"""Minimal Alpaca Trading API client, restricted to the paper-trading endpoint.

Live trading is deliberately not supported: the base URL is fixed to the paper
endpoint and any other URL is refused. Keys are read from environment variables
or a local ``.env`` file (ignored by Git) and are never logged.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

PAPER_URL = "https://paper-api.alpaca.markets"
KEY_ID = "ALPACA_API_KEY_ID"
SECRET = "ALPACA_API_SECRET_KEY"
TIMEOUT = 30


class BrokerError(RuntimeError):
    pass


def to_alpaca(ticker: str) -> str:
    """Project tickers use a hyphen for share classes (BRK-B); Alpaca uses a dot (BRK.B)."""
    return ticker.replace("-", ".")


def from_alpaca(symbol: str) -> str:
    return symbol.replace(".", "-")


def load_credentials(root: Path) -> tuple[str, str] | None:
    """Keys from the environment, falling back to ``root/.env``; None if absent."""
    values = {KEY_ID: os.environ.get(KEY_ID, ""), SECRET: os.environ.get(SECRET, "")}
    env_file = root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            name, sep, value = line.partition("=")
            name = name.strip()
            if sep and name in values and not values[name]:
                values[name] = value.strip().strip('"').strip("'")
    if not values[KEY_ID] or not values[SECRET]:
        return None
    return values[KEY_ID], values[SECRET]


class AlpacaPaper:
    def __init__(self, key_id: str, secret: str, session: requests.Session | None = None,
                 base_url: str = PAPER_URL):
        if base_url.rstrip("/") != PAPER_URL:
            raise BrokerError("only the Alpaca paper-trading endpoint is supported")
        self.base = PAPER_URL
        self.session = session or requests.Session()
        self.session.headers.update({"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret})

    def _request(self, method: str, path: str, **kwargs):
        response = self.session.request(method, f"{self.base}{path}", timeout=TIMEOUT, **kwargs)
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise BrokerError(f"{method} {path} failed with {response.status_code}: {response.text[:300]}")
        return response.json()

    def account(self) -> dict:
        return self._request("GET", "/v2/account")

    def clock(self) -> dict:
        return self._request("GET", "/v2/clock")

    def positions(self) -> dict[str, float]:
        return {from_alpaca(p["symbol"]): float(p["qty"]) for p in self._request("GET", "/v2/positions") or []}

    def order_by_client_id(self, client_order_id: str) -> dict | None:
        return self._request("GET", "/v2/orders:by_client_order_id",
                             params={"client_order_id": client_order_id})

    def submit_market_order(self, symbol: str, qty: int, side: str, client_order_id: str) -> dict:
        """Market day order. Submitted after the close, it queues for the next session's open."""
        if side not in {"buy", "sell"} or qty <= 0:
            raise BrokerError(f"invalid order: {side} {qty} {symbol}")
        return self._request("POST", "/v2/orders", json={
            "symbol": to_alpaca(symbol), "qty": str(int(qty)), "side": side, "type": "market",
            "time_in_force": "day", "client_order_id": client_order_id})
