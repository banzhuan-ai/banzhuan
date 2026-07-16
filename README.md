# banzhuan

Python SDK for BanZhuan.AI backtests, factor research, market insights, strategy drafts, and strategy publishing on:

- `https://hype.banzhuan.ai` (Hyperliquid perps)
- `https://edge.banzhuan.ai` (EdgeX perps) - deactivated July 5, 2026
- `https://poly.banzhuan.ai` (Polymarket prediction markets)
- `https://afp.banzhuan.ai` (Autonity AFP) - deactivated July 5, 2026

This package is designed for automation and agent workflows. It uses the same production session token model as the website.

> Note (July 10, 2026): the one-to-one Builder AI chat API was retired and now returns HTTP 410. This affects `builder_chat()` and `save_chat_session()`. Its replacement is the Agent Society group chat on the website. Saved legacy chat sessions remain readable as an archive via `list_chat_sessions()` and `get_chat_session()`.

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
import json

from banzhuan import BanzhuanClient, build_perps_risk_config

# exchange can be "hype" or "poly"; "edge" and "afp" target platforms
# that were deactivated on July 5, 2026
client = BanzhuanClient(exchange="hype", session_token="your-session-token")

# Load a Builder graph JSON file, for example one written by an earlier
# `banzhuan builder-chat` run or fetched with client.get_strategy_graph(...)
with open("graph.json", encoding="utf-8") as fh:
    graph = json.load(fh)

backtest = client.create_backtest(
    strategy_graph=graph,
    start_ms=client.days_ago_ms(14),
    end_ms=client.now_ms(),
    initial_capital=10_000,
    risk_config=build_perps_risk_config(10_000, "ETH-USD"),
)

final_backtest = client.wait_for_backtest(backtest["jobId"], include="result")
print(final_backtest["result"]["summary"])

# Publish the graph as a private strategy once the backtest looks good
published = client.create_strategy(
    name="ETH Trend",
    description="Trend-following strategy for ETH-USD",
    risk_tier="moderate",
    supported_markets=["ETH-USD"],
    visibility="private",
    strategy_graph=graph,
)
print(published.get("strategyId"))
```

## What The SDK Covers

- Builder AI chat: `POST /builder-chat` (retired July 10, 2026, now returns HTTP 410)
- Builder async job polling: `GET /builder-chat/jobs/:jobId` (only used by the retired chat flow)
- Chat sessions: `GET /builder-chat/sessions` reads saved legacy chats as an archive; the save endpoint (`POST /builder-chat/sessions`) returns HTTP 410
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

The retired Builder AI chat returned command deltas, not a fully materialized graph. This package still includes a Python port of the production graph mutation logic (`apply_builder_commands()`), so you can:

- replay archived Builder command deltas against a graph
- save the resulting graph
- backtest or publish the graph later

You can also fetch an existing graph with `get_strategy_graph()` or through a saved draft (`get_draft()`), then backtest or republish it with `create_backtest()`, `create_strategy()`, or `publish_strategy_version()`.

## CLI

The CLI is intentionally small and focused on session-token workflows.

### Save a session token

```bash
banzhuan auth set <your-session-token>
```

### Run a Builder prompt against a graph file (retired)

The `builder-chat` command depends on the retired Builder AI chat API and now fails with HTTP 410 (retired July 10, 2026). It is kept here for reference only.

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
- Builder AI Chat was retired on July 10, 2026: `builder_chat()` and `save_chat_session()` now receive HTTP 410. The replacement is the Agent Society group chat on the website. `apply_builder_result()` and `apply_builder_commands()` remain available for replaying archived Builder command deltas.
- Backtest and strategy publishing methods use perps-specific formats on HYPE. For POLY, use the Python API with exchange-specific payloads or the web UI.
- The `edge` and `afp` exchange values point at platforms that were deactivated on July 5, 2026. The SDK still accepts them for compatibility, but their APIs no longer serve SDK requests (EDGE returns a static 503).
- Live session deployment can still be completed in the web app.

## License

MIT
