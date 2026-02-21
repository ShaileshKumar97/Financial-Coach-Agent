import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from livekit.agents import cli
from livekit.agents import WorkerOptions

from src.agent.financial_coach_agent import FinancialCoachAgent
from src.data.transaction_loader import TransactionLoader
from src.voice.voice_interface import create_entrypoint


load_dotenv()


def setup_user_data(data_source: str = ""):
    if data_source and os.path.exists(data_source):
        return TransactionLoader.load_from_csv(data_source)
    else:
        return TransactionLoader.create_sample_data()


async def run_text_mode(agent: FinancialCoachAgent):
    print("\nFinancial Coach Agent - Text Mode")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                break

            if not user_input:
                continue

            response = agent.chat(user_input)
            print(f"\nFinancial Coach: {response}\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")


def run_voice_mode(agent: FinancialCoachAgent):
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "CEREBRAS_API_KEY",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        return

    entrypoint_fn = create_entrypoint(agent)

    sys.argv = [sys.argv[0], "start"]

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint_fn))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Financial Coach Voice AI Agent")
    parser.add_argument(
        "--user-id", type=str, default="default_user", help="User identifier"
    )
    parser.add_argument("--data", type=str, default=None, help="Path to CSV file")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["text", "voice"],
        default="text",
        help="Interaction mode",
    )

    args = parser.parse_args()

    try:
        transactions = setup_user_data(args.data)
        agent = FinancialCoachAgent(args.user_id, transactions)

        if args.mode == "text":
            asyncio.run(run_text_mode(agent))
        elif args.mode == "voice":
            run_voice_mode(agent)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
