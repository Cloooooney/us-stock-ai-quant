"""Mirror the frozen model's monthly signal in an Alpaca paper account.

Runs after the forward tracker in the monthly cycle. For the configured model
(``broker/config.json``) it:

1. reconciles earlier paper orders and, once every order is final, appends a
   FILLS event with the broker's fill prices;
2. when the model ledger has a new SIGNAL with its ENTRY, sizes equal-weight
   whole-share orders from the account equity, skips small adjustments to
   holdings that stay in the portfolio, submits sells before buys as market day
   orders (queued for the next open when sent after the close), and appends an
   ORDERS event.

Each order's client ID is derived from model, signal date, symbol, and side, so
a rerun can never submit the same order twice. Only the paper endpoint exists;
live trading is not implemented.

    python -m broker.paper_rebalance --check     # connection test, places no orders
    python -m broker.paper_rebalance --preview   # orders it would send for the latest month-end, places none
    python -m broker.paper_rebalance
"""
from __future__ import annotations

import argparse
import json
import math
from collections.abc import Callable
from datetime import date
from pathlib import Path

from broker.alpaca import AlpacaPaper, BrokerError, load_credentials
from paper_trading.ledger import append, read_events, validate

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "broker/config.json"
BROKER_LEDGER = ROOT / "paper_trading/alpaca_paper_ledger.jsonl"
MODEL_LEDGERS = {"v5": ROOT / "paper_trading/v5_ledger.jsonl", "v6": ROOT / "paper_trading/v6_ledger.jsonl"}
FINAL = {"filled", "canceled", "expired", "rejected"}
MAX_SIGNAL_AGE_DAYS = 10
MAX_PRICE_AGE_DAYS = 7


def load_config(path: Path = CONFIG) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("live_trading"):
        raise BrokerError("live trading is not implemented; the release gate in docs/ROADMAP.md comes first")
    if config["model"] not in MODEL_LEDGERS:
        raise BrokerError(f"unknown model {config['model']!r}")
    return config


def client_order_id(model: str, signal_date: str, symbol: str, side: str) -> str:
    return f"{model}-{signal_date}-{symbol}-{side}"


def plan_orders(targets: list[str], equity: float, prices: dict[str, float], positions: dict[str, float],
                cash_buffer: float, band: float, max_order_fraction: float) -> list[dict]:
    """Whole-share orders that move the account to equal weight across ``targets``.

    Names leaving the portfolio are sold in full. Continuing names are only
    traded when they are more than ``band`` of a target position away from it.
    """
    if not targets:
        raise BrokerError("no target holdings")
    missing = sorted(s for s in set(targets) | set(positions) if not prices.get(s, 0) > 0)
    if missing:
        raise BrokerError(f"no usable price for: {', '.join(missing)}")
    target_value = equity * (1 - cash_buffer) / len(targets)
    orders = []
    for symbol in sorted(set(targets) | set(positions)):
        price = prices[symbol]
        current = positions.get(symbol, 0.0)
        wanted = math.floor(target_value / price) if symbol in targets else 0
        diff = wanted - current
        if symbol in targets and current > 0 and abs(diff) * price < band * target_value:
            continue
        qty = int(math.floor(abs(diff)))
        if qty == 0:
            continue
        side = "buy" if diff > 0 else "sell"
        if side == "buy" and qty * price > max_order_fraction * equity:
            raise BrokerError(f"{symbol}: buy of {qty * price:,.0f} exceeds the per-order limit")
        orders.append({"symbol": symbol, "side": side, "qty": qty, "reference_price": round(price, 4)})
    return sorted(orders, key=lambda o: (o["side"] != "sell", o["symbol"]))


def latest_closes(root: Path, symbols: list[str], today: date) -> dict[str, float]:
    """Latest raw close per symbol from the local point-in-time price file."""
    import pandas as pd

    frame = pd.read_parquet(root / "data/pit/prices.parquet", columns=["ticker", "date", "close"],
                            filters=[("ticker", "in", list(symbols))])
    frame["date"] = pd.to_datetime(frame["date"])
    latest = frame.sort_values("date").groupby("ticker").last()
    stale = latest.index[(pd.Timestamp(today) - latest["date"]).dt.days > MAX_PRICE_AGE_DAYS]
    if len(stale):
        raise BrokerError(f"stale prices for: {', '.join(stale)}")
    return latest["close"].astype(float).to_dict()


def _by_type(events: list[dict], kind: str) -> dict[str, dict]:
    return {e["signal_date"]: e for e in events if e.get("event_type") == kind}


def reconcile(client, ledger: Path, model: str) -> list[str]:
    notes = []
    events = read_events(ledger)
    fills = _by_type(events, "FILLS")
    for signal_date, orders in sorted(_by_type(events, "ORDERS").items()):
        if signal_date in fills:
            continue
        states = []
        for sent in orders["submitted"]:
            order = client.order_by_client_id(sent["client_order_id"]) or {}
            states.append({"client_order_id": sent["client_order_id"], "symbol": sent["symbol"],
                           "side": sent["side"], "qty": sent["qty"], "status": order.get("status", "missing"),
                           "filled_qty": float(order.get("filled_qty") or 0),
                           "filled_avg_price": float(order["filled_avg_price"]) if order.get("filled_avg_price") else None,
                           "filled_at": order.get("filled_at")})
        if all(s["status"] in FINAL for s in states):
            append(ledger, {"event_type": "FILLS", "model": model, "signal_date": signal_date, "orders": states})
            notes.append(f"recorded paper fills for {signal_date}")
        else:
            notes.append(f"paper orders for {signal_date} are not final yet")
    return notes


def run(root: Path = ROOT, client=None, check: bool = False, today: date | None = None,
        prices_lookup: Callable[[list[str]], dict[str, float]] | None = None,
        ledger: Path | None = None, model_ledgers: dict[str, Path] | None = None) -> dict:
    today = today or date.today()
    config = load_config(root / "broker/config.json")
    ledger = ledger or root / "paper_trading/alpaca_paper_ledger.jsonl"
    model_ledgers = model_ledgers or {k: root / v.relative_to(ROOT) for k, v in MODEL_LEDGERS.items()}
    if client is None:
        credentials = load_credentials(root)
        if credentials is None:
            return {"status": "not_configured", "detail": "no Alpaca paper keys in .env; nothing was sent"}
        client = AlpacaPaper(*credentials)
    account = client.account()
    summary = {"status": "ok", "model": config["model"], "account_status": account.get("status"),
               "equity": float(account["equity"]), "cash": float(account["cash"])}
    if check:
        return {**summary, "positions": len(client.positions())}

    valid, detail = validate(ledger)
    if not valid:
        raise BrokerError(f"broker ledger failed validation: {detail}")
    notes = reconcile(client, ledger, config["model"])

    model_events = read_events(model_ledgers[config["model"]])
    signals, entries = _by_type(model_events, "SIGNAL"), _by_type(model_events, "ENTRY")
    broker_events = read_events(ledger)
    ordered, filled = _by_type(broker_events, "ORDERS"), _by_type(broker_events, "FILLS")
    if not signals:
        return {**summary, "notes": notes + ["no model signal yet"]}
    signal_date = max(signals)
    if signal_date in ordered:
        return {**summary, "notes": notes + [f"orders for {signal_date} already sent"]}
    if signal_date not in entries:
        return {**summary, "notes": notes + [f"waiting for the model ENTRY of {signal_date}"]}
    if set(ordered).difference(filled):
        return {**summary, "notes": notes + ["earlier paper orders are not final; not stacking new orders"]}
    if (today - date.fromisoformat(signal_date)).days > MAX_SIGNAL_AGE_DAYS:
        return {**summary, "notes": notes + [f"signal {signal_date} is too old to act on; skipped"]}

    targets = [h["ticker"] for h in signals[signal_date]["holdings"]]
    positions = client.positions()
    lookup = prices_lookup or (lambda symbols: latest_closes(root, symbols, today))
    prices = lookup(sorted(set(targets) | set(positions)))
    plan = plan_orders(targets, summary["equity"], prices, positions, config["cash_buffer"],
                       config["rebalance_band"], config["max_order_fraction"])
    submitted, errors = [], []
    for order in plan:
        cid = client_order_id(config["model"], signal_date, order["symbol"], order["side"])
        try:
            existing = client.order_by_client_id(cid)
            response = existing or client.submit_market_order(order["symbol"], order["qty"], order["side"], cid)
            submitted.append({**order, "client_order_id": cid, "order_id": response.get("id"),
                              "status": response.get("status")})
        except BrokerError as error:
            errors.append({**order, "client_order_id": cid, "error": str(error)})
    append(ledger, {"event_type": "ORDERS", "model": config["model"], "signal_date": signal_date,
                    "account_equity": summary["equity"], "positions_before": positions,
                    "planned": plan, "submitted": submitted, "errors": errors})
    return {**summary, "notes": notes + [f"sent {len(submitted)} paper orders for {signal_date}"],
            "errors": errors}


def latest_model_selection(root: Path, model: str):
    """Holdings the frozen model would pick for the latest completed month-end."""
    if model == "v6":
        from models.v6_factor import build_v6_signal
        selected, _, _ = build_v6_signal(root)
    elif model == "v7":
        from models.v7_factor import build_v7_signal
        frozen = json.loads((root / "reports/ai_v7_factor/frozen_config.json").read_text(encoding="utf-8"))
        selected, _, _ = build_v7_signal(root, frozen["score"])
    else:
        from models.v5 import build_v5_signal
        selected, _, _ = build_v5_signal(root)
    return selected


def preview(root: Path = ROOT, client=None, today: date | None = None,
            selection_builder: Callable[[Path, str], object] | None = None,
            prices_lookup: Callable[[list[str]], dict[str, float]] | None = None) -> dict:
    """Plan the orders for the latest completed month-end without sending any
    order or writing any ledger. A rehearsal, not a forward record."""
    today = today or date.today()
    config = load_config(root / "broker/config.json")
    if client is None:
        credentials = load_credentials(root)
        if credentials is None:
            return {"status": "not_configured", "detail": "no Alpaca paper keys in .env"}
        client = AlpacaPaper(*credentials)
    account = client.account()
    selected = (selection_builder or latest_model_selection)(root, config["model"])
    targets = [str(t) for t in selected.sort_values("portfolio_rank")["ticker"]]
    positions = client.positions()
    lookup = prices_lookup or (lambda symbols: latest_closes(root, symbols, today))
    prices = lookup(sorted(set(targets) | set(positions)))
    equity = float(account["equity"])
    plan = plan_orders(targets, equity, prices, positions, config["cash_buffer"],
                       config["rebalance_band"], config["max_order_fraction"])
    buys = sum(o["qty"] * o["reference_price"] for o in plan if o["side"] == "buy")
    return {"status": "preview_only_no_orders_sent", "model": config["model"],
            "signal_date": str(pd_date(selected["date"].max())), "equity": equity,
            "planned_orders": plan, "estimated_buy_value": round(buys, 2),
            "estimated_cash_left": round(equity - buys, 2)}


def pd_date(value) -> date:
    import pandas as pd

    return pd.Timestamp(value).date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mirror the frozen model in an Alpaca paper account.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="test the connection without placing orders")
    mode.add_argument("--preview", action="store_true", help="show the orders for the latest month-end; send none")
    args = parser.parse_args()
    print(json.dumps(preview() if args.preview else run(check=args.check), indent=2))


if __name__ == "__main__":
    main()
