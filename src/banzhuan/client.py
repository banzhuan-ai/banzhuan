from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Union

import requests

from .graph import BuilderGraph, apply_builder_commands


DEFAULT_BASE_URLS: Dict[str, str] = {
    "hype": "https://hype.banzhuan.ai/api/executor",
    "poly": "https://poly.banzhuan.ai/api/executor",
}

CREDENTIALS_DIR = Path.home() / ".banzhuan"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"


def resolve_base_url(
    exchange: Optional[str] = None,
    base_url: Optional[str] = None,
) -> str:
    if base_url:
        return str(base_url).rstrip("/")

    normalized = (exchange or "hype").strip().lower()
    if normalized not in DEFAULT_BASE_URLS:
        supported = ", ".join(sorted(DEFAULT_BASE_URLS))
        raise ValueError(f"Unsupported exchange '{exchange}'. Expected one of: {supported}")
    return DEFAULT_BASE_URLS[normalized]


def _load_credentials() -> Dict[str, Any]:
    try:
        if CREDENTIALS_FILE.exists():
            return json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def load_stored_session_token() -> str:
    creds = _load_credentials()
    return str(creds.get("session_token") or "")


def save_stored_session_token(token: str) -> Path:
    clean = str(token or "").strip()
    if not clean:
        raise ValueError("Session token cannot be empty")
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(
        json.dumps({"session_token": clean}, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        CREDENTIALS_FILE.chmod(0o600)
    except Exception:
        pass
    return CREDENTIALS_FILE


def clear_stored_session_token() -> None:
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()


def build_perps_risk_config(
    max_budget_usd: float,
    market: str,
    *,
    max_leverage_x100: int = 300,
    max_drawdown_bps: int = 2000,
    daily_loss_limit_bps: int = 0,
    take_profit_bps: int = 0,
) -> Dict[str, Any]:
    return {
        "maxBudgetUsd": float(max_budget_usd),
        "maxLeverageX100": int(max_leverage_x100),
        "maxDrawdownBps": int(max_drawdown_bps),
        "dailyLossLimitBps": int(daily_loss_limit_bps),
        "takeProfitBps": int(take_profit_bps),
        "allowedMarkets": [str(market)],
    }


class BanzhuanAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        payload: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class AuthenticationError(BanzhuanAPIError):
    pass


class CreditsRequiredError(BanzhuanAPIError):
    pass


class RateLimitError(BanzhuanAPIError):
    pass


class BanzhuanClient:
    def __init__(
        self,
        *,
        session_token: Optional[str] = None,
        exchange: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        resolved_token = (
            str(session_token or "").strip()
            or str(os.environ.get("BANZHUAN_SESSION_TOKEN") or "").strip()
            or load_stored_session_token()
        )
        if not resolved_token:
            raise ValueError(
                "Session token required. Authenticate at https://banzhuan.ai/credits and pass "
                "session_token=..., set BANZHUAN_SESSION_TOKEN, or run `banzhuan auth set ...`."
            )

        self.base_url = resolve_base_url(exchange=exchange, base_url=base_url)
        self.session_token = resolved_token
        self.timeout = float(timeout)
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "banzhuan-python-sdk/0.2.0",
            }
        )

    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def days_ago_ms(days: int) -> int:
        return BanzhuanClient.now_ms() - int(days) * 24 * 60 * 60 * 1000

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        url = path if path.startswith("http://") or path.startswith("https://") else f"{self.base_url}/{path.lstrip('/')}"
        response = self.session.request(
            method=method.upper(),
            url=url,
            params=dict(params or {}),
            json=dict(json_body or {}) if json_body is not None else None,
            headers={"x-banzhuan-session": self.session_token},
            timeout=timeout or self.timeout,
        )

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                payload: Any = response.json()
            except Exception:
                payload = {"error": f"Invalid JSON response from {url}"}
        else:
            payload = {"raw": response.text}

        if response.status_code >= 400:
            message = f"Request failed with HTTP {response.status_code}"
            if isinstance(payload, dict):
                message = str(payload.get("error") or payload.get("hint") or message)
            if response.status_code == 401:
                raise AuthenticationError(message, status_code=response.status_code, payload=payload)
            if response.status_code == 402:
                raise CreditsRequiredError(message, status_code=response.status_code, payload=payload)
            if response.status_code == 429:
                raise RateLimitError(message, status_code=response.status_code, payload=payload)
            raise BanzhuanAPIError(message, status_code=response.status_code, payload=payload)

        return payload

    def apply_builder_result(
        self,
        current_graph: Optional[BuilderGraph],
        result: Mapping[str, Any],
    ) -> BuilderGraph:
        return apply_builder_commands(
            current_graph,
            result.get("commands") or [],
        )

    def list_available_api_keys(self) -> Any:
        return self._request("GET", "/api-keys/available")

    def claim_api_key(self, key: str) -> Any:
        return self._request("POST", "/api-keys/claim", json_body={"key": key})

    def get_my_api_key(self) -> Any:
        return self._request("GET", "/api-keys/mine")

    def builder_chat(
        self,
        message: str,
        *,
        current_graph: Optional[BuilderGraph] = None,
        conversation_history: Optional[Sequence[Mapping[str, Any]]] = None,
        model: str = "nano",
        async_mode: bool = True,
        builder_run_config: Optional[Mapping[str, Any]] = None,
        validation_result: Optional[Mapping[str, Any]] = None,
        last_backtest_summary: Optional[Mapping[str, Any]] = None,
        knowledge: bool = False,
        backtest_results: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        payload: Dict[str, Any] = {
            "message": message,
            "model": model,
            "async": bool(async_mode),
        }
        if current_graph is not None:
            payload["currentGraph"] = current_graph
        if conversation_history is not None:
            payload["conversationHistory"] = list(conversation_history)
        if builder_run_config is not None:
            payload["builderRunConfig"] = dict(builder_run_config)
        if validation_result is not None:
            payload["validationResult"] = dict(validation_result)
        if last_backtest_summary is not None:
            payload["lastBacktestSummary"] = dict(last_backtest_summary)
        if knowledge:
            payload["knowledge"] = True
        if backtest_results is not None:
            payload["backtestResults"] = dict(backtest_results)
        return self._request("POST", "/builder-chat", json_body=payload, timeout=max(self.timeout, 180.0))

    def get_builder_job(self, job_id: str) -> Any:
        return self._request("GET", f"/builder-chat/jobs/{job_id}")

    def wait_for_builder_job(
        self,
        job_id: str,
        *,
        poll_interval_s: float = 2.0,
        timeout_s: float = 600.0,
    ) -> Any:
        deadline = time.time() + timeout_s
        while True:
            job = self.get_builder_job(job_id)
            if job.get("done"):
                if job.get("error"):
                    raise BanzhuanAPIError(str(job["error"]), payload=job)
                return job
            if time.time() >= deadline:
                raise TimeoutError(f"Timed out waiting for builder job {job_id}")
            time.sleep(poll_interval_s)

    def save_chat_session(
        self,
        *,
        name: str,
        messages: Sequence[Mapping[str, Any]],
        canvas_snapshot: Optional[Mapping[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Any:
        payload: Dict[str, Any] = {
            "name": name,
            "messages": list(messages),
            "canvasSnapshot": canvas_snapshot,
        }
        if session_id:
            payload["sessionId"] = session_id
        return self._request("POST", "/builder-chat/sessions", json_body=payload)

    def list_chat_sessions(self) -> Any:
        return self._request("GET", "/builder-chat/sessions")

    def get_chat_session(self, session_id: str) -> Any:
        return self._request("GET", f"/builder-chat/sessions/{session_id}")

    def delete_chat_session(self, session_id: str) -> Any:
        return self._request("DELETE", f"/builder-chat/sessions/{session_id}")

    def clear_chat_sessions(self) -> Any:
        return self._request("DELETE", "/builder-chat/sessions")

    def save_draft(
        self,
        *,
        name: str,
        strategy_graph: BuilderGraph,
        description: str = "",
        risk_tier: str = "moderate",
        supported_markets: Optional[Sequence[str]] = None,
        visibility: str = "private",
        draft_id: Optional[str] = None,
    ) -> Any:
        payload: Dict[str, Any] = {
            "name": name,
            "description": description,
            "riskTier": risk_tier,
            "supportedMarkets": list(supported_markets or []),
            "strategyGraph": strategy_graph,
            "visibility": visibility,
        }
        if draft_id:
            payload["draftId"] = draft_id
        return self._request("POST", "/strategies/drafts", json_body=payload)

    def list_drafts(self) -> Any:
        return self._request("GET", "/strategies/drafts")

    def get_draft(self, draft_id: str) -> Any:
        return self._request("GET", f"/strategies/drafts/{draft_id}")

    def delete_draft(self, draft_id: str) -> Any:
        return self._request("DELETE", f"/strategies/drafts/{draft_id}")

    def clear_drafts(self) -> Any:
        return self._request("DELETE", "/strategies/drafts")

    def create_strategy(
        self,
        *,
        name: str,
        description: str,
        risk_tier: str,
        supported_markets: Sequence[str],
        visibility: str = "private",
        changelog: str = "Initial publish",
        python_code: Optional[str] = None,
        strategy_graph: Optional[BuilderGraph] = None,
    ) -> Any:
        if not python_code and not strategy_graph:
            raise ValueError("Either python_code or strategy_graph is required")
        payload: Dict[str, Any] = {
            "name": name,
            "description": description,
            "riskTier": risk_tier,
            "supportedMarkets": list(supported_markets),
            "visibility": visibility,
            "changelog": changelog,
        }
        if python_code:
            payload["pythonCode"] = python_code
        if strategy_graph is not None:
            payload["strategyGraph"] = strategy_graph
        return self._request("POST", "/strategies", json_body=payload, timeout=max(self.timeout, 180.0))

    def publish_strategy_version(
        self,
        strategy_id: str,
        *,
        changelog: str = "Update",
        python_code: Optional[str] = None,
        strategy_graph: Optional[BuilderGraph] = None,
        version: Optional[Mapping[str, int]] = None,
    ) -> Any:
        if not python_code and not strategy_graph:
            raise ValueError("Either python_code or strategy_graph is required")
        payload: Dict[str, Any] = {"changelog": changelog}
        if python_code:
            payload["pythonCode"] = python_code
        if strategy_graph is not None:
            payload["strategyGraph"] = strategy_graph
        if version is not None:
            payload["version"] = dict(version)
        return self._request(
            "POST",
            f"/strategies/{strategy_id}/versions",
            json_body=payload,
            timeout=max(self.timeout, 180.0),
        )

    def list_my_strategies(self) -> Any:
        return self._request("GET", "/strategies/mine")

    def get_strategy(self, strategy_id: str) -> Any:
        return self._request("GET", f"/strategies/{strategy_id}")

    def get_strategy_graph(self, strategy_id: str) -> Any:
        return self._request("GET", f"/strategies/{strategy_id}/graph")

    def set_strategy_visibility(self, strategy_id: str, visibility: str) -> Any:
        return self._request(
            "PUT",
            f"/strategies/{strategy_id}/visibility",
            json_body={"visibility": visibility},
        )

    def activate_strategy(self, strategy_id: str) -> Any:
        return self._request("POST", f"/strategies/{strategy_id}/activate")

    def delete_strategy(self, strategy_id: str) -> Any:
        return self._request("DELETE", f"/strategies/{strategy_id}")

    def create_backtest(
        self,
        *,
        start_ms: int,
        end_ms: int,
        initial_capital: float,
        risk_config: Mapping[str, Any],
        python_code: Optional[str] = None,
        strategy_id: Optional[str] = None,
        strategy_version: Optional[Mapping[str, Any]] = None,
        strategy_graph: Optional[BuilderGraph] = None,
        symbols: Optional[Sequence[str]] = None,
        slippage_bps: Optional[float] = None,
        spread_bps: Optional[float] = None,
        taker_fee_bps: Optional[float] = None,
        maker_fee_bps: Optional[float] = None,
        include_equity_curve: bool = True,
        include_trades: bool = True,
        include_logs: bool = False,
        max_logs: Optional[int] = None,
    ) -> Any:
        option_count = sum(
            bool(option)
            for option in (
                python_code,
                strategy_graph,
                strategy_id and strategy_version,
            )
        )
        if option_count != 1:
            raise ValueError(
                "Provide exactly one of python_code, strategy_graph, or (strategy_id + strategy_version)"
            )

        payload: Dict[str, Any] = {
            "startMs": int(start_ms),
            "endMs": int(end_ms),
            "initialCapital": float(initial_capital),
            "riskConfig": dict(risk_config),
            "includeEquityCurve": bool(include_equity_curve),
            "includeTrades": bool(include_trades),
            "includeLogs": bool(include_logs),
        }
        if python_code:
            payload["pythonCode"] = python_code
        if strategy_graph is not None:
            payload["strategyGraph"] = strategy_graph
        if strategy_id and strategy_version:
            payload["strategyId"] = strategy_id
            payload["strategyVersion"] = dict(strategy_version)
        if symbols is not None:
            payload["symbols"] = list(symbols)
        if slippage_bps is not None:
            payload["slippageBps"] = float(slippage_bps)
        if spread_bps is not None:
            payload["spreadBps"] = float(spread_bps)
        if taker_fee_bps is not None:
            payload["takerFeeBps"] = float(taker_fee_bps)
        if maker_fee_bps is not None:
            payload["makerFeeBps"] = float(maker_fee_bps)
        if max_logs is not None:
            payload["maxLogs"] = int(max_logs)
        return self._request("POST", "/backtests", json_body=payload, timeout=max(self.timeout, 180.0))

    def get_backtest(self, job_id: str, *, include: Optional[str] = None) -> Any:
        params: Dict[str, Any] = {}
        if include:
            params["include"] = include
        return self._request("GET", f"/backtests/{job_id}", params=params)

    def list_backtests(self, *, limit: int = 20) -> Any:
        return self._request("GET", "/backtests", params={"limit": int(limit)})

    def cancel_backtest(self, job_id: str) -> Any:
        return self._request("DELETE", f"/backtests/{job_id}")

    def purge_backtest(self, job_id: str) -> Any:
        return self._request("DELETE", f"/backtests/{job_id}/purge")

    def clear_backtests(self) -> Any:
        return self._request("DELETE", "/backtests/clear-all")

    def wait_for_backtest(
        self,
        job_id: str,
        *,
        include: str = "result",
        poll_interval_s: float = 2.0,
        timeout_s: float = 1800.0,
    ) -> Any:
        deadline = time.time() + timeout_s
        while True:
            job = self.get_backtest(job_id)
            status = str(job.get("status") or "")
            if status == "completed":
                return self.get_backtest(job_id, include=include)
            if status in {"failed", "cancelled"}:
                raise BanzhuanAPIError(
                    str(job.get("error") or f"Backtest {status}"),
                    payload=job,
                )
            if time.time() >= deadline:
                raise TimeoutError(f"Timed out waiting for backtest {job_id}")
            time.sleep(poll_interval_s)

    def list_research_jobs(self, *, limit: int = 20) -> Any:
        return self._request("GET", "/research/jobs", params={"limit": int(limit)})

    def get_research_job(self, job_id: str) -> Any:
        return self._request("GET", f"/research/jobs/{job_id}")

    def wait_for_research_job(
        self,
        job_id: str,
        *,
        poll_interval_s: float = 2.0,
        timeout_s: float = 1800.0,
    ) -> Any:
        deadline = time.time() + timeout_s
        while True:
            job = self.get_research_job(job_id)
            if job.get("done"):
                if job.get("error") or str(job.get("status") or "") == "failed":
                    raise BanzhuanAPIError(str(job.get("error") or "Research job failed"), payload=job)
                return job
            if time.time() >= deadline:
                raise TimeoutError(f"Timed out waiting for research job {job_id}")
            time.sleep(poll_interval_s)

    def list_research_runs(self, *, limit: int = 50, offset: int = 0) -> Any:
        return self._request(
            "GET",
            "/research",
            params={"limit": int(limit), "offset": int(offset)},
        )

    def get_research_run(self, research_run_id: str) -> Any:
        return self._request("GET", f"/research/{research_run_id}")

    def generate_factor_preview(self, prompt: str) -> Any:
        return self._request(
            "POST",
            "/research/factors/generate-preview",
            json_body={"prompt": prompt},
            timeout=max(self.timeout, 180.0),
        )

    def create_factor(
        self,
        *,
        name: str,
        description: str,
        category: str,
        required_inputs: Sequence[str],
        graph_json: Union[Mapping[str, Any], str],
    ) -> Any:
        graph_payload = graph_json if isinstance(graph_json, str) else json.dumps(graph_json)
        return self._request(
            "POST",
            "/research/factors",
            json_body={
                "name": name,
                "description": description,
                "category": category,
                "requiredInputs": list(required_inputs),
                "graphJson": graph_payload,
            },
        )

    def list_factors(
        self,
        *,
        market: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Any:
        params: Dict[str, Any] = {}
        if market:
            params["market"] = market
        if category:
            params["category"] = category
        return self._request("GET", "/research/factors", params=params)

    def get_factor(self, factor_id: str) -> Any:
        return self._request("GET", f"/research/factors/{factor_id}")

    def delete_factor(self, factor_id: str) -> Any:
        return self._request("DELETE", f"/research/factors/{factor_id}")

    def evaluate_factor(
        self,
        *,
        factor_id: str,
        market: str,
        lookback_days: int = 30,
    ) -> Any:
        return self._request(
            "POST",
            "/research/factors/evaluate",
            json_body={
                "factorId": factor_id,
                "market": market,
                "lookbackDays": int(lookback_days),
            },
            timeout=max(self.timeout, 180.0),
        )

    def evaluate_all_factors(
        self,
        *,
        market: str,
        lookback_days: int = 30,
    ) -> Any:
        return self._request(
            "POST",
            "/research/factors/evaluate-all",
            json_body={
                "market": market,
                "lookbackDays": int(lookback_days),
            },
            timeout=max(self.timeout, 180.0),
        )

    def get_market_insights(
        self,
        *,
        symbol: str,
        start_ms: Optional[int] = None,
        end_ms: Optional[int] = None,
    ) -> Any:
        params: Dict[str, Any] = {"symbol": symbol}
        if start_ms is not None:
            params["start"] = int(start_ms)
        if end_ms is not None:
            params["end"] = int(end_ms)
        return self._request("GET", "/market-insights", params=params)

    def generate_market_insight(self, symbol: str) -> Any:
        return self._request(
            "POST",
            "/market-insights/generate",
            json_body={"symbol": symbol},
            timeout=max(self.timeout, 180.0),
        )
