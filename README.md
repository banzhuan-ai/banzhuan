# banzhuan

Python SDK and CLI for current BanZhuan.AI backtest, research, strategy, and
market-insight APIs. The package is designed for production automation and
agent workflows.

## Production Target Matrix

| Target | Production state | SDK status |
|--------|------------------|------------|
| HYPE | Active | Primary target for drafts, strategy management, backtests, factor-ledger research, and market insights |
| POLY | Active | Partial common-client support: backtests and most factor-ledger operations are available; Builder and strategy behavior is exchange-specific |
| Alpha | Active | Not an SDK exchange target; Agent Society is operated through the product UI |
| EDGE | Retired | Identifier removed September 4, 2026 when the host was terminated |
| AFP | Retired | Identifier removed September 4, 2026 when the host was terminated |

An accepted exchange name does not guarantee feature parity. Use the
capability matrix below before building an integration.

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

After configuring the production session token as described above:

```python
from banzhuan import BanzhuanClient

client = BanzhuanClient(exchange="hype")
result = client.list_backtests(limit=5)
print(result)
```

## Capability Matrix

| Capability | HYPE | POLY |
|------------|------|------|
| Local Builder graph types and command replay | Supported | Supported |
| One-to-one Builder chat | Retired; use Agent Society in the product UI | Compatibility route exists, with POLY-specific behavior |
| Drafts and common strategy-management paths | Supported | Not exposed on the HYPE-compatible paths used by this client |
| Backtests and job polling | Supported | Supported with exchange-specific payload requirements |
| Factor-ledger research | Supported | Partial route parity |
| Market insights | Supported | No HYPE-compatible route |

The local graph helpers do not call a remote service. `apply_builder_commands()`
can materialize command deltas, and graph JSON can then be used with a
supported backtest or strategy workflow.

## Current Python Surface

- `BanzhuanClient` for supported drafts, strategies, backtests, research, and
  market insights
- `BuilderGraph` types and `apply_builder_commands()` for local graph handling
- `build_perps_risk_config()` for perps-oriented HYPE payloads
- polling helpers for asynchronous backtest and research jobs

## CLI

The CLI provides `auth`, `backtest`, and `publish` command families. Its
backtest and publish payloads are perps-oriented and should be treated as
HYPE-first. The `builder-chat` command remains in the package for
compatibility, but the HYPE one-to-one flow is retired and it is not the
current onboarding path.

## Compatibility Notes

- Agent Society group chat in the product UI replaces the retired HYPE
  one-to-one Builder workflow.
- Legacy HYPE chat-session reads remain archival; saving new legacy sessions
  is not a current workflow.
- POLY exposes a compatibility Builder route and selected common API paths,
  but it does not mirror every HYPE strategy or market-insight endpoint.
- Alpha has no `BanzhuanClient` exchange mapping.
- `edge` and `afp` were removed on September 4, 2026 when their hosts were terminated; only `hype` and `poly` are accepted.

## Package Structure

```text
src/banzhuan/
  client.py       HTTP client and polling helpers
  graph.py        Builder graph types and local command replay
  cli.py          Command-line interface
  __init__.py     Public exports and package version
pyproject.toml    Package metadata
```

## License

MIT
