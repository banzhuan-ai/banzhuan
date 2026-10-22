from __future__ import annotations

import argparse
from getpass import getpass
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import (
    BanzhuanClient,
    build_perps_risk_config,
    clear_stored_api_key,
    load_stored_api_key,
    save_stored_api_key,
)


def _die(message: str, code: int = 1) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_graph(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    graph_path = Path(path)
    if not graph_path.exists():
        _die(f"Graph file not found: {graph_path}")
    data = _read_json(graph_path)
    if not isinstance(data, dict):
        _die(f"Graph file must contain a JSON object: {graph_path}")
    return data


def _load_messages(path: Optional[str]) -> List[Dict[str, Any]]:
    if not path:
        return []
    messages_path = Path(path)
    if not messages_path.exists():
        _die(f"Messages file not found: {messages_path}")
    data = _read_json(messages_path)
    if not isinstance(data, list):
        _die(f"Messages file must contain a JSON array: {messages_path}")
    return list(data)


def _resolve_client(args: argparse.Namespace) -> BanzhuanClient:
    try:
        return BanzhuanClient(
            api_key=getattr(args, "api_key", None),
            exchange=getattr(args, "exchange", None),
            base_url=getattr(args, "base_url", None),
        )
    except Exception as exc:
        _die(str(exc))


def cmd_auth_set(_args: argparse.Namespace) -> None:
    path = save_stored_api_key(getpass("Yototec API key: "))
    print(f"API key saved to {path}")


def cmd_auth_show(_args: argparse.Namespace) -> None:
    print("API key configured." if load_stored_api_key() else "No stored API key.")


def cmd_auth_clear(_args: argparse.Namespace) -> None:
    clear_stored_api_key()
    print("Stored API key cleared.")


def cmd_builder_chat(args: argparse.Namespace) -> None:
    client = _resolve_client(args)
    current_graph = _load_graph(args.graph_in)
    messages = _load_messages(args.messages_in)

    builder_run_config: Dict[str, Any] = {
        "market": args.market or (current_graph or {}).get("market") or "HYPE-USD",
        "lookbackDays": int(args.lookback_days),
        "initialCapital": float(args.initial_capital),
    }

    response = client.builder_chat(
        args.message,
        current_graph=current_graph,
        conversation_history=messages,
        model=args.model,
        async_mode=not args.sync,
        builder_run_config=builder_run_config,
    )

    raw_output = response
    result = response
    if response.get("async") and response.get("jobId"):
        print(f"Builder job started: {response['jobId']}")
        raw_output = client.wait_for_builder_job(response["jobId"])
        result = raw_output.get("result") or {}

    updated_graph = client.apply_builder_result(current_graph, result)
    graph_out = args.graph_out or args.graph_in
    messages_out = args.messages_out or args.messages_in

    if graph_out:
        _write_json(Path(graph_out), updated_graph)
        print(f"Updated graph written to {graph_out}")

    if messages_out:
        updated_messages = list(messages)
        updated_messages.append({"role": "user", "content": args.message})
        updated_messages.append({"role": "assistant", "content": result.get("message", "")})
        _write_json(Path(messages_out), updated_messages)
        print(f"Updated messages written to {messages_out}")

    if args.result_out:
        _write_json(Path(args.result_out), raw_output)
        print(f"Builder result written to {args.result_out}")

    print()
    print(result.get("message") or "Builder request completed.")


def cmd_backtest(args: argparse.Namespace) -> None:
    client = _resolve_client(args)
    graph = _load_graph(args.graph)
    if not graph:
        _die("--graph is required")

    market = args.market or graph.get("market") or "HYPE-USD"
    end_ms = int(args.end_ms) if args.end_ms is not None else client.now_ms()
    start_ms = int(args.start_ms) if args.start_ms is not None else end_ms - int(args.days) * 24 * 60 * 60 * 1000
    initial_capital = float(args.capital)

    response = client.create_backtest(
        strategy_graph=graph,
        start_ms=start_ms,
        end_ms=end_ms,
        initial_capital=initial_capital,
        risk_config=build_perps_risk_config(
            initial_capital,
            market,
            max_leverage_x100=int(args.max_leverage_x100),
            max_drawdown_bps=int(args.max_drawdown_bps),
            daily_loss_limit_bps=int(args.daily_loss_limit_bps),
            take_profit_bps=int(args.take_profit_bps),
        ),
        spread_bps=float(args.spread_bps),
        taker_fee_bps=float(args.taker_fee_bps),
        maker_fee_bps=float(args.maker_fee_bps),
        include_equity_curve=True,
        include_trades=True,
        include_logs=False,
    )

    job_id = response.get("jobId") or response.get("id")
    if not job_id:
        _die("Backtest response did not include a job ID")

    print(f"Backtest started: {job_id}")
    result = client.wait_for_backtest(job_id, include="result")

    if args.out:
        _write_json(Path(args.out), result)
        print(f"Backtest result written to {args.out}")

    summary = ((result.get("result") or {}).get("summary") or {})
    print()
    print("Backtest summary")
    print(f"  finalCapital: {summary.get('finalCapital')}")
    print(f"  totalReturnPct: {summary.get('totalReturnPct')}")
    print(f"  maxDrawdownPct: {summary.get('maxDrawdownPct')}")
    print(f"  totalTrades: {summary.get('totalTrades')}")


def cmd_publish(args: argparse.Namespace) -> None:
    client = _resolve_client(args)
    graph = _load_graph(args.graph)
    if not graph:
        _die("--graph is required")

    market = args.market or graph.get("market") or "HYPE-USD"

    if args.strategy_id:
        response = client.publish_strategy_version(
            args.strategy_id,
            strategy_graph=graph,
            changelog=args.changelog or "Update",
        )
    else:
        if not args.name:
            _die("--name is required when creating a new strategy")
        response = client.create_strategy(
            name=args.name,
            description=args.description or "Strategy created with the banzhuan Python SDK",
            risk_tier=args.risk_tier,
            supported_markets=[market],
            visibility=args.visibility,
            changelog=args.changelog or "Initial publish",
            strategy_graph=graph,
        )

    if args.out:
        _write_json(Path(args.out), response)
        print(f"Publish result written to {args.out}")

    print("Publish complete")
    if response.get("strategyId"):
        print(f"  strategyId: {response['strategyId']}")
    if response.get("version"):
        version = response["version"]
        if isinstance(version, dict):
            print(f"  version: {version.get('major')}.{version.get('minor')}.{version.get('patch')}")
    if response.get("codeHash"):
        print(f"  codeHash: {response['codeHash']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="banzhuan")
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="Manage the stored API key")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)

    auth_set = auth_sub.add_parser("set", help="Store a Yototec API key with hidden input")
    auth_set.set_defaults(func=cmd_auth_set)

    auth_show = auth_sub.add_parser("show", help="Show the stored API key")
    auth_show.set_defaults(func=cmd_auth_show)

    auth_clear = auth_sub.add_parser("clear", help="Delete the stored API key")
    auth_clear.set_defaults(func=cmd_auth_clear)

    builder = sub.add_parser("builder-chat", help="Send a Builder AI prompt and update a local graph file")
    builder.add_argument("--exchange", choices=("hype", "poly"), default="hype")
    builder.add_argument("--base-url", help="Override the executor base URL")
    builder.add_argument("--message", required=True, help="Builder prompt")
    builder.add_argument("--graph-in", help="Existing graph JSON file")
    builder.add_argument("--graph-out", help="Output graph JSON file")
    builder.add_argument("--messages-in", help="Existing conversation history JSON file")
    builder.add_argument("--messages-out", help="Output conversation history JSON file")
    builder.add_argument("--result-out", help="Output raw Builder response JSON file")
    builder.add_argument("--model", default="nano", help="Builder model name, usually nano or mini")
    builder.add_argument("--market", help="Builder market override")
    builder.add_argument("--lookback-days", type=int, default=14)
    builder.add_argument("--initial-capital", type=float, default=10000)
    builder.add_argument("--sync", action="store_true", help="Use synchronous Builder mode")
    builder.set_defaults(func=cmd_builder_chat)

    backtest = sub.add_parser("backtest", help="Run a backtest against a Builder graph")
    backtest.add_argument("--exchange", choices=("hype", "poly"), default="hype")
    backtest.add_argument("--base-url", help="Override the executor base URL")
    backtest.add_argument("--graph", required=True, help="Builder graph JSON file")
    backtest.add_argument("--market", help="Backtest market override")
    backtest.add_argument("--days", type=int, default=14)
    backtest.add_argument("--capital", type=float, default=10000)
    backtest.add_argument("--start-ms", type=int)
    backtest.add_argument("--end-ms", type=int)
    backtest.add_argument("--max-leverage-x100", type=int, default=300)
    backtest.add_argument("--max-drawdown-bps", type=int, default=2000)
    backtest.add_argument("--daily-loss-limit-bps", type=int, default=0)
    backtest.add_argument("--take-profit-bps", type=int, default=0)
    backtest.add_argument("--spread-bps", type=float, default=0.0)
    backtest.add_argument("--taker-fee-bps", type=float, default=0.0)
    backtest.add_argument("--maker-fee-bps", type=float, default=0.0)
    backtest.add_argument("--out", help="Output backtest JSON file")
    backtest.set_defaults(func=cmd_backtest)

    publish = sub.add_parser("publish", help="Create or update a strategy from a Builder graph")
    publish.add_argument("--exchange", choices=("hype", "poly"), default="hype")
    publish.add_argument("--base-url", help="Override the executor base URL")
    publish.add_argument("--graph", required=True, help="Builder graph JSON file")
    publish.add_argument("--strategy-id", help="Existing strategy ID to publish a new version")
    publish.add_argument("--name", help="Strategy name when creating a new strategy")
    publish.add_argument("--description", help="Strategy description")
    publish.add_argument("--market", help="Market override")
    publish.add_argument("--risk-tier", default="moderate")
    publish.add_argument("--visibility", choices=("public", "private"), default="private")
    publish.add_argument("--changelog", help="Publish changelog")
    publish.add_argument("--out", help="Output publish JSON file")
    publish.set_defaults(func=cmd_publish)

    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
