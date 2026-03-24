# banzhuan

Python SDK for BanZhuan.AI Builder, AI Chat, backtests, research, drafts, and strategy publishing on:

- `https://hype.banzhuan.ai`
- `https://edge.banzhuan.ai`

This package is designed for automation and agent workflows. It uses the same production session token model as the website.

## Installation

```bash
pip install banzhuan
```

## Authentication

1. Open [https://banzhuan.ai/credits](https://banzhuan.ai/credits)
2. Connect your wallet and sign in
3. Copy your session token from the "Session Token (CLI)" card
4. Pass that token to the SDK or store it with the CLI

The package does not perform wallet signing. It assumes you already have a valid session token.

```bash
banzhuan auth set <your-session-token>
```

Or use an environment variable:

```bash
export BANZHUAN_SESSION_TOKEN=<your-session-token>
```

## Quick Start

```python
from banzhuan import BanzhuanClient, build_perps_risk_config

client = BanzhuanClient(exchange="hype", session_token="your-session-token")

reply = client.builder_chat(
    "Build a trend-following strategy for ETH-USD with a stop loss and cooldown",
    current_graph=None,
    conversation_history=[],
    async_mode=True,
    builder_run_config={
        "market": "ETH-USD",
        "lookbackDays": 14,
        "initialCapital": 10_000,
    },
)

job = client.wait_for_builder_job(reply["jobId"])
result = job["result"]
graph = client.apply_builder_result(None, result)

backtest = client.create_backtest(
    strategy_graph=graph,
    start_ms=client.days_ago_ms(14),
    end_ms=client.now_ms(),
    initial_capital=10_000,
    risk_config=build_perps_risk_config(10_000, "ETH-USD"),
)

final_backtest = client.wait_for_backtest(backtest["jobId"], include="result")
print(final_backtest["result"]["summary"])
```

## What The SDK Covers

- Builder AI chat: `POST /builder-chat`
- Builder async job polling: `GET /builder-chat/jobs/:jobId`
- Chat session persistence: `POST/GET/DELETE /builder-chat/sessions`
- Strategy drafts: `POST/GET/DELETE /strategies/drafts`
- Strategy publishing and versioning: `POST /strategies`, `POST /strategies/:id/versions`
- Backtests: `POST /backtests`, `GET /backtests/:id`, `GET /backtests`
- Factor-ledger research:
  - `POST /research/factors/generate-preview`
  - `POST /research/factors`
  - `POST /research/factors/evaluate`
  - `POST /research/factors/evaluate-all`
  - `GET /research/jobs/:jobId`
  - `GET /research/:id`
- Market insights: `GET /market-insights`, `POST /market-insights/generate`

## Builder Graphs

Builder AI chat returns command deltas, not a fully materialized graph. This package includes a Python port of the production graph mutation logic so you can:

- send a prompt
- receive Builder commands
- apply them locally
- save the graph
- backtest or publish the graph later

## CLI

The CLI is intentionally small and focused on session-token workflows.

### Save a session token

```bash
banzhuan auth set <your-session-token>
```

### Run a Builder prompt against a graph file

```bash
banzhuan builder-chat \
  --exchange hype \
  --message "Create a funding mean-reversion strategy for HYPE-USD" \
  --graph-out graph.json
```

### Backtest a graph file

```bash
banzhuan backtest \
  --exchange hype \
  --graph graph.json \
  --market HYPE-USD \
  --days 14 \
  --capital 10000 \
  --out backtest.json
```

### Publish a Builder graph

```bash
banzhuan publish \
  --exchange hype \
  --graph graph.json \
  --name "ETH Trend" \
  --market ETH-USD \
  --visibility private
```

## Notes

- A valid session token authenticates you as the wallet that created it.
- Credits and invite-key checks still apply on production endpoints.
- Research uses the current factor-ledger workflow. The legacy sweep-style `/research/run` path is not used.
- This package focuses on Builder, research, backtests, drafts, and strategy management. Live session deployment can still be completed in the web app.

## License

MIT
