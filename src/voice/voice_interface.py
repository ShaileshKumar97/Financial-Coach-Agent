import asyncio
import json
import logging
import os
import uuid

from livekit import agents
from livekit import rtc
from livekit.agents import Agent
from livekit.agents import AgentSession
from livekit.agents import RoomInputOptions
from livekit.agents.llm import ChatChunk
from livekit.agents.llm import ChoiceDelta
from livekit.plugins import cartesia
from livekit.plugins import deepgram
from livekit.plugins import noise_cancellation
from livekit.plugins import openai

from src.agent.financial_coach_agent import FinancialCoachAgent

logger = logging.getLogger(__name__)

_DATA_TRIGGER_KEYWORDS = (
    "plan",
    "budget",
    "breakdown",
    "payoff",
    "debt",
    "schedule",
    "recommend",
    "summary",
    "details",
    "what should",
)


class FinancialCoachVoiceAgent(Agent):
    def __init__(self, financial_agent: FinancialCoachAgent, room: rtc.Room):
        super().__init__(instructions=financial_agent.get_system_prompt())
        self.financial_agent = financial_agent
        self.room = room
        self.last_handled_user_msg_id: str | None = None
        self.session_id = (
            f"call_{uuid.uuid4().hex[:8]}"  # Unique session ID for this call
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions=(
                "Say a very brief, warm hello to the user to start the call. "
                "For example: 'Hi! I'm your financial coach. How can I help you today?' "
                "Do not read out their financial data yet. Keep it under 2 sentences."
            )
        )

    async def stt_node(self, audio, model_settings=None):
        async for event in super().stt_node(audio, model_settings):
            yield event

    async def llm_node(self, chat_ctx, tools, model_settings=None):
        messages = (
            getattr(chat_ctx, "messages", getattr(chat_ctx, "items", []))
            if chat_ctx
            else []
        )

        user_text = ""
        if messages:
            for msg in reversed(messages):
                if hasattr(msg, "role") and "user" in str(msg.role).lower():
                    content = msg.content
                    if isinstance(content, str):
                        texts = [content]
                    elif isinstance(content, list):
                        texts = []
                        for part in content:
                            if isinstance(part, str):
                                texts.append(part)
                            elif hasattr(part, "text"):
                                texts.append(part.text)
                    elif hasattr(content, "text"):
                        texts = [content.text]
                    else:
                        texts = [str(content)]

                    user_text = " ".join(texts).strip()
                    if user_text:
                        break

        # if not user_text and self.financial_agent.user_id:
        #     try:
        #         state = self.financial_agent.graph.get_state({"configurable": {"thread_id": self.session_id}})
        #         if state and state.values and "messages" in state.values:
        #             msgs = state.values["messages"]
        #             for m in reversed(msgs):
        #                 if m.__class__.__name__ == "HumanMessage":
        #                     user_text = m.content.strip()
        #                     if user_text:
        #                         break
        #     except Exception:
        #         pass

        if not user_text:
            async for chunk in super().llm_node(chat_ctx, tools, model_settings):
                yield chunk
            return

        loop = asyncio.get_event_loop()
        agent_response = await loop.run_in_executor(
            None, self.financial_agent.chat, user_text, None, self.session_id
        )

        voice_text = agent_response.get("voice", "I've analyzed your data.")
        detailed_content = agent_response.get("detail", voice_text)

        user_msg_id = (
            messages[-1].id if messages and hasattr(messages[-1], "id") else user_text
        )
        if user_msg_id != self.last_handled_user_msg_id:
            if any(kw in user_text.lower() for kw in _DATA_TRIGGER_KEYWORDS):
                self.last_handled_user_msg_id = user_msg_id
                asyncio.create_task(
                    self._publish_data_card(
                        user_text, detailed_content, self.session_id
                    )
                )

        yield ChatChunk(
            id=uuid.uuid4().hex, delta=ChoiceDelta(role="assistant", content=voice_text)
        )

    async def _publish_data_card(
        self, question: str, content: str, session_id: str
    ) -> None:
        """Push a structured payload to the frontend via the LiveKit data channel."""
        try:
            payload = json.dumps(
                {
                    "type": "financial_data_card",
                    "question": question,
                    "content": content,
                    "session_id": session_id,
                }
            ).encode("utf-8")
            await self.room.local_participant.publish_data(
                payload,
                reliable=True,
                topic="financial_card",
            )
        except Exception as e:
            logger.warning(f"Data card publish failed: {e}")


def create_entrypoint(financial_agent: FinancialCoachAgent):
    async def entrypoint(ctx: agents.JobContext):
        await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)

        stt = deepgram.STT(model="nova-2")
        llm = openai.LLM(
            model="gpt-oss-120b",
            api_key=os.getenv("CEREBRAS_API_KEY"),
            base_url=os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
            max_completion_tokens=450,
        )
        tts = cartesia.TTS(
            model="sonic-2",
            voice=os.getenv(
                "CARTESIA_VOICE_ID", "79a125e8-cd45-4c13-8a67-188112f4dd22"
            ),
            api_key=os.getenv("CARTESIA_API_KEY"),
        )

        session = AgentSession(
            llm=llm,
            stt=stt,
            tts=tts,
            resume_false_interruption=True,
            false_interruption_timeout=1.0,
        )

        agent = FinancialCoachVoiceAgent(financial_agent, ctx.room)
        await session.start(
            room=ctx.room,
            agent=agent,
            room_input_options=RoomInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
        )

    return entrypoint
