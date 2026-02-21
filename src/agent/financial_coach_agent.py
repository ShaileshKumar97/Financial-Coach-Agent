import os
from typing import Annotated

from langchain_core.messages import AIMessage
from langchain_core.messages import BaseMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from src.analysis.financial_analyzer import FinancialAnalyzer
from src.models.transaction import Transaction


def create_financial_tools(analyzer: FinancialAnalyzer):
    @tool
    def get_spending_summary() -> str:
        """Get a summary of spending by category over the last 6 months."""
        spending = analyzer.get_spending_by_category()
        if not spending:
            return "No spending data available."

        summary = "Spending Summary:\n"
        total = sum(spending.values())
        for category, amount in sorted(
            spending.items(), key=lambda x: x[1], reverse=True
        ):
            pct = (amount / total * 100) if total > 0 else 0
            summary += f"  {category}: ${amount:,.2f} ({pct:.1f}%)\n"
        summary += f"\nTotal Spending: ${total:,.2f}"
        return summary

    @tool
    def get_income_analysis() -> str:
        """Get income analysis including savings rate."""
        income = analyzer.get_income_summary()
        if income["total"] == 0:
            return "No income data available."

        result = (
            f"Income Analysis:\n"
            f"  Total Income: ${income['total']:,.2f}\n"
            f"  Average Monthly Income: ${income['average_monthly']:,.2f}\n"
            f"  Average Monthly Spending: ${income['average_monthly_spending']:,.2f}\n"
            f"  Monthly Savings: ${income['monthly_savings']:,.2f}\n"
            f"  Savings Rate: {income['savings_rate']:.1f}%"
        )
        if income["savings_rate"] < 0:
            result += "\n\nWarning: You're spending more than you earn."
        elif income["savings_rate"] < 10:
            result += "\n\nRecommendation: Aim for at least 10-20% savings rate."
        return result

    @tool
    def get_debt_analysis() -> str:
        """Get analysis of debt payments and payoff strategies."""
        debt = analyzer.get_debt_analysis()
        if debt["total_debt_payments"] == 0:
            return "No debt payments found in transactions."

        result = (
            f"Debt Analysis:\n"
            f"  Total Debt Payments: ${debt['total_debt_payments']:,.2f}\n"
            f"  Average Monthly Debt Payment: ${debt['average_monthly_debt']:,.2f}\n"
            f"  Available for Additional Debt Payment: ${debt['available_for_debt']:,.2f}"
        )
        if debt["strategies"]:
            result += "\n\nRecommended Strategies:"
            for strat in debt["strategies"]:
                result += f"\n  {strat['strategy'].replace('_', ' ').title()}: {strat['description']}"
                result += (
                    f"\n    Monthly Allocation: ${strat['monthly_allocation']:,.2f}"
                )
        return result

    @tool
    def identify_spending_issues() -> str:
        """Identify problematic spending patterns."""
        patterns = analyzer.identify_spending_patterns()
        if not patterns:
            return "No significant spending issues identified."
        result = "Spending Patterns Identified:\n"
        for pattern in patterns:
            result += f"  {pattern['insight']}\n"
        return result.strip()

    @tool
    def get_budget_recommendations() -> str:
        """Get personalized budget recommendations based on income and actual spending."""
        budget = analyzer.get_budget_recommendations()
        result = (
            f"Budget Recommendations:\n"
            f"  Average Monthly Income: ${budget['average_monthly_income']:,.2f}\n"
            f"  Average Monthly Spending: ${budget['average_monthly_spending']:,.2f}\n"
            f"  Recommended Total Budget: ${budget['total_recommended_budget']:,.2f}"
        )
        if budget["recommendations"]:
            result += "\n\nAreas for Improvement:"
            for rec in budget["recommendations"]:
                result += f"\n  {rec['category']}: {rec['suggestion']}"
        else:
            result += "\n\nNo major budget adjustments needed."
        return result

    return [
        get_spending_summary,
        get_income_analysis,
        get_debt_analysis,
        identify_spending_issues,
        get_budget_recommendations,
    ]


class FinancialCoachState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class FinancialCoachAgent:
    def __init__(
        self,
        user_id: str,
        transactions: list[Transaction],
    ):
        self.user_id = user_id
        self.analyzer = FinancialAnalyzer(transactions)

        if not os.getenv("CEREBRAS_API_KEY"):
            raise ValueError("CEREBRAS_API_KEY not set.")

        self.llm = ChatOpenAI(
            model="gpt-oss-120b",
            temperature=0.2,
            max_tokens=450,
            api_key=os.getenv("CEREBRAS_API_KEY"),
            base_url=os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
        )
        self.tools = create_financial_tools(self.analyzer)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.memory = MemorySaver()
        self._voice_context = self._build_voice_context()
        self.graph = self._build_graph()

    def _build_graph(self):
        def should_continue(state: FinancialCoachState) -> str:
            messages = state["messages"]
            if not messages:
                return END
            last_message = messages[-1]
            if isinstance(last_message, AIMessage) and getattr(
                last_message, "tool_calls", None
            ):
                return "tools"
            return END

        def call_model(state: FinancialCoachState) -> FinancialCoachState:
            response = self.llm_with_tools.invoke(state["messages"])
            return {"messages": [response]}

        workflow = StateGraph(FinancialCoachState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent", should_continue, {"tools": "tools", END: END}
        )
        workflow.add_edge("tools", "agent")
        return workflow.compile(checkpointer=self.memory)

    def _build_voice_context(self) -> str:
        lines: list[str] = []
        try:
            spending = self.analyzer.get_spending_by_category()
            if spending:
                total = sum(spending.values())
                top3 = sorted(spending.items(), key=lambda x: x[1], reverse=True)[:3]
                top_str = ", ".join(
                    f"{cat} ({amt / total * 100:.0f}%)" for cat, amt in top3
                )
                lines.append(f"Top spending categories: {top_str}.")
                lines.append(f"Total 6-month spending: ${total:,.0f}.")
        except Exception:
            pass
        try:
            income = self.analyzer.get_income_summary()
            if income["total"] > 0:
                lines.append(
                    f"Avg monthly income: ${income['average_monthly']:,.0f}. "
                    f"Avg monthly spending: ${income['average_monthly_spending']:,.0f}. "
                    f"Savings rate: {income['savings_rate']:.1f}%."
                )
        except Exception:
            pass
        try:
            debt = self.analyzer.get_debt_analysis()
            if debt["total_debt_payments"] > 0:
                lines.append(
                    f"Monthly debt payments: ${debt['average_monthly_debt']:,.0f}. "
                    f"Available for extra payoff: ${debt['available_for_debt']:,.0f}."
                )
        except Exception:
            pass
        return "\n".join(lines) if lines else "No transaction data available."

    def get_voice_context(self) -> str:
        return self._voice_context

    def get_system_prompt(self) -> str:
        return f"""You are a friendly financial coach speaking in a live voice call. \
You have already reviewed the user's last 6 months of transactions. \
Here is a quick snapshot of their finances:

{self._voice_context}

Voice Rules (follow strictly):
1. Respond in 1-3 short, natural spoken sentences. Never more.
2. No markdown, no bullet points, no headers, no emoji.
3. Spell out numbers conversationally — say "about twelve hundred dollars" not "$1,200.00".
4. Never repeat back all the data; just answer the user's specific question.
5. Be warm, encouraging, and to the point — like a real coach on a call.

Data & Tool Rules:
- The snapshot above only contains high-level summaries.
- You HAVE tools available for deep-dive questions (e.g., specific budget recommendations, detailed debt strategies, or spending category breakdowns).
- If the user asks for details not in the snapshot, YOU MUST CALL THE RELEVANT TOOL to get the data before answering.
- Only if the tool returns no data should you say you don't have the information. Never invent numbers."""

    def chat(
        self,
        user_message: str,
        conversation_history: list[BaseMessage] | None = None,
        thread_id: str | None = None,
    ) -> dict:
        messages: list[BaseMessage] = []

        if not conversation_history or not any(
            isinstance(m, SystemMessage) for m in conversation_history
        ):
            messages.append(SystemMessage(content=self.get_system_prompt()))

        if conversation_history:
            messages.extend(conversation_history)

        messages.append(HumanMessage(content=user_message))

        config = {
            "configurable": {"thread_id": thread_id or self.user_id},
            "recursion_limit": 10,
        }
        result = self.graph.invoke({"messages": messages}, config=config)

        spoken_response = "I've analyzed your data. How can I help?"
        detailed_data = ""

        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content and not detailed_data:
                spoken_response = msg.content
            if isinstance(msg, ToolMessage) and not detailed_data:
                detailed_data = msg.content

        if not detailed_data:
            detailed_data = spoken_response

        return {"voice": spoken_response, "detail": detailed_data}
