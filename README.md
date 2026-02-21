---
title: Financial Coach Agent
emoji: 👀
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Financial Coach Voice Agent

A voice-first financial coaching assistant. It loads a user's transaction history from a CSV/generate sample data, runs analysis on it, and lets the user have a spoken conversation with an AI coach with actual numbers.

## Stack

| Layer | Library |
|---|---|
| Agent / memory | LangGraph + LangChain |
| LLM (agent) | Cerebras `gpt-oss-120b` |
| STT | Deepgram `nova-2` |
| TTS | Cartesia `sonic-2` |
| Voice infra | LiveKit |
| Data | pandas, pydantic |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

**Required env vars:**
```
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
DEEPGRAM_API_KEY=
CARTESIA_API_KEY=
CARTESIA_VOICE_ID=
CEREBRAS_API_KEY=

```

## Usage

```bash
# Text mode
python main.py --mode text --data sample_transactions.csv

# Voice mode
python main.py --mode voice
```

Pass `--user-id` to namespace conversation memory per user.

## CSV format

Columns: `date`, `amount`, `category`, `description`, `type`, `account_type`

- `amount` is signed: positive = income, negative = expense.  
- `category` must match a value in `TransactionCategory` (check `src/models/transaction.py`).
- At least 30 days of data is required.

The repo includes `sample_transactions.csv` with 6 months of sample generated data.

## Assumptions

- Transaction history covers at least 30 days (enforced at startup).
- Income is inferred from positive-amount transactions, no explicit "type=income" filter is used.
- Budget targets follow rough 50/30/20 guidelines capped per category.
- Voice responses are capped at 450 tokens to keep TTS latency low.
- The LangGraph agent uses in-memory checkpointing. Restart clears conversation history.

## Project structure

```
src/
  agent/        FinancialCoachAgent (LangGraph agent + tools)
  analysis/     FinancialAnalyzer (pure computation, no LLM)
  data/         TransactionLoader (CSV / sample data)
  models/       Transaction / TransactionCategory pydantic models
  voice/        FinancialCoachVoiceAgent (LiveKit integration)
main.py         CLI entry point
```
