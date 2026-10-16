"""Thin Alpaca paper-trading HTTP client.

We need exactly four endpoints (account, positions, submit_order, get_order),
so we wrap `requests` directly rather than depending on `alpaca-py`. Mocking
in tests is straightforward with the `responses` library.
"""
from __future__ import annotations

import time
from typing import Any

import requests

from packages.shared.config import get_settings

from packages.shared.logging import get_logger

log = get_logger(__name__)

DEFAULT_TIMEOUT = 15
DEFAULT_MAX_RETRIES = 3


class AlpacaError(RuntimeError):
    """Raised on non-2xx response after retries are exhausted."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        is_ambiguous: bool = False,
        is_duplicate: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.is_ambiguous = is_ambiguous
        self.is_duplicate = is_duplicate


class AlpacaClient:
    """Minimal client over Alpaca's paper REST API."""

    def __init__(
        self,
        key_id: str | None = None,
        secret_key: str | None = None,
        base_url: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        session: requests.Session | None = None,
    ) -> None:
        settings = get_settings()
        self.key_id = key_id if key_id is not None else settings.alpaca_key_id
        self.secret_key = secret_key if secret_key is not None else settings.alpaca_secret_key
        self.base_url = (base_url if base_url is not None else settings.alpaca_base_url).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._http = session or requests.Session()

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._http.request(
                    method,
                    url,
                    headers=self._headers,
                    timeout=self.timeout,
                    **kwargs,
                )
            except requests.RequestException as exc:
                last_exc = exc
                log.warning("Alpaca %s %s attempt %d failed: %s", method, path, attempt, exc)
            else:
                if 200 <= resp.status_code < 300:
                    return resp.json() if resp.content else None
                if resp.status_code >= 500 and attempt < self.max_retries:
                    log.warning(
                        "Alpaca %s %s attempt %d got %d, retrying",
                        method, path, attempt, resp.status_code,
                    )
                elif resp.status_code >= 500:
                    raise AlpacaError(
                        f"Alpaca {method} {path} returned {resp.status_code}: {resp.text[:300]}",
                        status_code=resp.status_code,
                        is_ambiguous=True,
                    )
                else:
                    is_dup = (
                        resp.status_code == 422
                        and "client_order_id" in resp.text.lower()
                    )
                    raise AlpacaError(
                        f"Alpaca {method} {path} returned {resp.status_code}: {resp.text[:300]}",
                        status_code=resp.status_code,
                        is_ambiguous=is_dup,
                        is_duplicate=is_dup,
                    )
            time.sleep(2 ** (attempt - 1) * 0.1)
        raise AlpacaError(
            f"Alpaca {method} {path} failed after {self.max_retries} attempts: {last_exc}",
            status_code=None,
            is_ambiguous=True,
        )

    def get_account(self) -> dict[str, Any]:
        return self._request("GET", "/v2/account")

    def list_positions(self) -> list[dict[str, Any]]:
        return self._request("GET", "/v2/positions") or []

    def get_order(self, broker_order_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v2/orders/{broker_order_id}")

    def get_order_by_client_id(self, client_order_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v2/orders:by_client_order_id?client_order_id={client_order_id}")

    def submit_bracket_order(
        self,
        *,
        symbol: str,
        qty: float,
        side: str,
        take_profit: float,
        stop_loss: float,
        time_in_force: str = "day",
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": "market",
            "time_in_force": time_in_force,
            "order_class": "bracket",
            "take_profit": {"limit_price": round(take_profit, 2)},
            "stop_loss": {"stop_price": round(stop_loss, 2)},
        }
        if client_order_id is not None:
            payload["client_order_id"] = client_order_id
        return self._request("POST", "/v2/orders", json=payload)

    def submit_market_order(
        self,
        *,
        symbol: str,
        qty: float,
        side: str,
        time_in_force: str = "day",
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": "market",
            "time_in_force": time_in_force,
        }
        if client_order_id is not None:
            payload["client_order_id"] = client_order_id
        return self._request("POST", "/v2/orders", json=payload)
