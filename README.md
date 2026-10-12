# banzhuan Python SDK

SDK and CLI source for BanZhuan.AI. The supported production integration here is
owner observation of autonomous work on Hyperliquid and Polymarket. Only `hype`
and `poly` are exchange targets. Agent Society is the central headless service;
Alpha, EDGE and AFP are not current SDK targets.

This README describes source `bd01901b44d61c950c188ad2a84f09b17ad9b2c8`, package
version `0.2.0`. It does not assert that a package index or every deployment already
contains this revision. Install a reviewed source release at its exact pin; do not
infer source identity from the package version alone. Python 3.9 or newer is required.

## Authentication and read example

`BanzhuanClient` accepts an existing central Credits session through its
`session_token` argument, `BANZHUAN_SESSION_TOKEN`, or the CLI credential store.
The SDK performs no wallet signing or passkey ceremony. Obtain authentication
through the approved central Credits procedure; owner setup/signing uses reviewed
terminal procedures. Never put a token in a committed example, shell history or log.

With `BANZHUAN_SESSION_TOKEN` already supplied privately:

```python
from banzhuan import BanzhuanClient

client = BanzhuanClient(exchange="poly")
page = client.list_backtests()
```

## Production read contract

| Methods | Hyperliquid | Polymarket |
|---|---|---|
| `list_backtests`, `get_backtest` | `/backtests`, `/backtests/:id` | `/observations/backtests`, `/observations/backtests/:id` |
| `list_research_jobs`, `get_research_job` | Shared `/research/jobs` routes | Shared owner read routes |
| `list_research_runs`, `get_research_run` | Shared `/research` routes | Shared owner read routes |
| `get_factor` | Stored factor details | Shared factor-detail route |
| `list_factors` | `/research/:id` is registered first and shadows the list path | The shared table preserves that route order; do not rely on this list call |
| `list_drafts`, `get_draft` | Stored drafts are observations; mutations retired | Draft list is empty; no shared draft-detail route is mounted |
| Strategy/graph reads | Owner-visible stored publications/graphs | Shared reads over prediction-market publications/graphs |
| `get_market_insights` | Stored market insights | Shared read contract with prediction-market data |

The table describes the inspected client/server source contract, not a new live
API certification. Responses remain venue-native. Polymarket observation backtest lists return a
`success/domain/data` envelope and fixed limit 50; the supplied SDK `limit` does not
turn that into Hyperliquid pagination. Its detail is an observation envelope, and
`include` does not select Hyperliquid result views. `wait_for_backtest` expects a
top-level `status`, so it must not be used with Polymarket's envelope. Use the
observation methods and inspect their native state. The client has no dedicated
method for Polymarket's paged backtest artifacts, account capital operations or
signed Society invocation transport.

Private stored reads require a valid session and ownership; public strategy
metadata follows its server visibility rules. Read-only passkey sessions are
restricted to their server-approved observations; a method's presence does not
promise passkey access to every historical route. Missing/unauthorized resources
remain errors. The SDK sends `x-banzhuan-session` and raises typed authentication,
Credits and rate-limit errors or `BanzhuanAPIError` for HTTP failures.

## Manual mutations are disabled

The package still contains methods for Builder chat, draft writes, strategy
publication/activation/deletion, backtest creation/cancellation/purge, factor
creation/evaluation and insight generation. These do not authorize a wallet
session to operate the production Auto-only platform. The executors refuse those
discretionary mutations; signed Society tools perform autonomous work. Operator
routes and owner constraint/funding capabilities have separate authority that
this SDK does not provide. There is no supported legacy mutation workflow.

The CLI exposes `auth`, `builder-chat`, `backtest` and `publish`; the three work
commands are not current production wallet workflows. `auth set/show/clear` manage
local credentials; `auth show` prints the stored token and must not be captured in
shared logs. No read-only CLI family is supplied in this revision.

`BuilderGraph`, `apply_builder_commands()` and `build_perps_risk_config()` are local
payload helpers. The perps helper does not make leverage/funding applicable to
Polymarket and creates no remote authority. Local graph replay is not live execution.

## Source and verification

`src/banzhuan/client.py` contains HTTP methods and polling helpers; `graph.py`
contains graph types/replay; `cli.py` contains the CLI; `__init__.py` exports the
public surface. `pyproject.toml` defines the package and `tests/` the focused checks.
Application builds/tests run only in Docker on the authorized EC2 host. Reuse the
accepted observation-read evidence at its pinned scope; a docs release does not
certify new live orders, strategy returns or package publication.

See the [platform operations](https://github.com/banzhuan-ai/plans/blob/main/README.md),
[Hyperliquid](https://github.com/banzhuan-ai/plans/blob/main/DEPLOY_HYPE.md) and
[Polymarket](https://github.com/banzhuan-ai/plans/blob/main/DEPLOY_POLY.md) runbooks
for the actual served component pins and contracts.

MIT.
