import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from broker.alpaca import AlpacaPaper, BrokerError, load_credentials
from broker.paper_rebalance import client_order_id, plan_orders, run
from paper_trading.ledger import append, read_events, validate

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [f"S{i:02d}" for i in range(20)]


class FakeClient:
    def __init__(self, equity=100_000.0, positions=None):
        self.equity, self.held, self.orders, self.submitted = equity, dict(positions or {}), {}, []

    def account(self):
        return {"status": "ACTIVE", "equity": str(self.equity), "cash": str(self.equity)}

    def positions(self):
        return dict(self.held)

    def order_by_client_id(self, cid):
        return self.orders.get(cid)

    def submit_market_order(self, symbol, qty, side, cid):
        if cid in self.orders:
            raise BrokerError("duplicate client_order_id")
        order = {"id": f"id-{len(self.orders)}", "status": "accepted", "symbol": symbol, "qty": qty, "side": side}
        self.orders[cid] = order
        self.submitted.append(order)
        return order

    def fill_all(self, price=50.0):
        for order in self.orders.values():
            order.update(status="filled", filled_qty=str(order["qty"]), filled_avg_price=str(price),
                         filled_at="2026-11-03T14:30:00Z")


def workspace(tmp_path):
    (tmp_path / "broker").mkdir()
    shutil.copy(ROOT / "broker/config.json", tmp_path / "broker/config.json")
    model = tmp_path / "v6.jsonl"
    append(model, {"event_type": "SIGNAL", "signal_date": "2026-10-30",
                   "holdings": [{"ticker": t} for t in TARGETS]}, timestamp="2026-11-02T22:00:00Z")
    return model


def test_paper_client_refuses_live_endpoint():
    with pytest.raises(BrokerError, match="paper"):
        AlpacaPaper("k", "s", base_url="https://api.alpaca.markets")


def test_credentials_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY_ID", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET_KEY", raising=False)
    assert load_credentials(tmp_path) is None
    (tmp_path / ".env").write_text('﻿ALPACA_API_KEY_ID = "PKTEST"\nALPACA_API_SECRET_KEY=secret\n', encoding="utf-8")
    assert load_credentials(tmp_path) == ("PKTEST", "secret")


def test_plan_sells_exits_buys_entrants_and_skips_small_adjustments():
    prices = {"A": 100.0, "B": 50.0, "C": 10.0, "OLD": 20.0}
    positions = {"A": 320.0, "B": 300.0, "OLD": 100.0}
    plan = plan_orders(["A", "B", "C"], 100_000, prices, positions, cash_buffer=0.02, band=0.10,
                       max_order_fraction=0.5)
    target = 100_000 * 0.98 / 3
    assert plan[0] == {"symbol": "OLD", "side": "sell", "qty": 100, "reference_price": 20.0}
    assert {"symbol": "C", "side": "buy", "qty": int(target // 10), "reference_price": 10.0} in plan
    assert not any(o["symbol"] == "A" for o in plan)  # 326 wanted vs 320 held: inside the band
    assert {"symbol": "B", "side": "buy", "qty": int(target // 50) - 300, "reference_price": 50.0} in plan
    assert [o["side"] for o in plan] == sorted(o["side"] for o in plan)[::-1]  # sells first


def test_plan_rejects_bad_prices_and_oversized_buys():
    with pytest.raises(BrokerError, match="no usable price"):
        plan_orders(["A"], 1000, {"A": 0.0}, {}, 0.02, 0.1, 1.0)
    with pytest.raises(BrokerError, match="per-order limit"):
        plan_orders(["A"], 100_000, {"A": 10.0}, {}, 0.0, 0.1, 0.05)


def test_live_trading_flag_is_refused(tmp_path):
    workspace(tmp_path)
    (tmp_path / "broker/config.json").write_text(json.dumps({"model": "v6", "live_trading": True}))
    with pytest.raises(BrokerError, match="live trading"):
        run(tmp_path, client=FakeClient())


def test_not_configured_without_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY_ID", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET_KEY", raising=False)
    workspace(tmp_path)
    assert run(tmp_path)["status"] == "not_configured"


def test_orders_wait_for_entry_then_send_once_then_reconcile(tmp_path):
    model = workspace(tmp_path)
    ledger = tmp_path / "broker.jsonl"
    client = FakeClient()
    kwargs = dict(client=client, today=date(2026, 11, 2), ledger=ledger, model_ledgers={"v6": model},
                  prices_lookup=lambda symbols: {s: 50.0 for s in symbols})

    waiting = run(tmp_path, **kwargs)
    assert "waiting for the model ENTRY" in waiting["notes"][-1] and not client.submitted

    append(model, {"event_type": "ENTRY", "signal_date": "2026-10-30"}, timestamp="2026-11-02T22:01:00Z")
    sent = run(tmp_path, **kwargs)
    assert len(client.submitted) == 20 and sent["errors"] == []
    assert client_order_id("v6", "2026-10-30", "S00", "buy") in client.orders
    assert all(o["qty"] == int(100_000 * 0.98 / 20 // 50) for o in client.submitted)

    again = run(tmp_path, **kwargs)
    assert len(client.submitted) == 20 and "already sent" in again["notes"][-1]
    assert "not final" in again["notes"][0]

    client.fill_all(price=50.25)
    run(tmp_path, **kwargs)
    [orders] = [e for e in read_events(ledger) if e["event_type"] == "ORDERS"]
    [fills] = [e for e in read_events(ledger) if e["event_type"] == "FILLS"]
    assert len(orders["submitted"]) == 20
    assert all(o["status"] == "filled" and o["filled_avg_price"] == 50.25 for o in fills["orders"])
    assert validate(ledger)[0]


def test_stale_signal_is_not_traded(tmp_path):
    model = workspace(tmp_path)
    append(model, {"event_type": "ENTRY", "signal_date": "2026-10-30"}, timestamp="2026-11-02T22:01:00Z")
    client = FakeClient()
    result = run(tmp_path, client=client, today=date(2026, 11, 20), ledger=tmp_path / "b.jsonl",
                 model_ledgers={"v6": model}, prices_lookup=lambda s: {x: 50.0 for x in s})
    assert "too old" in result["notes"][-1] and not client.submitted


def test_check_mode_places_no_orders(tmp_path):
    workspace(tmp_path)
    client = FakeClient(positions={"S00": 5})
    result = run(tmp_path, client=client, check=True)
    assert result["positions"] == 1 and result["equity"] == 100_000.0 and not client.submitted


def test_share_class_symbols_are_translated_for_alpaca():
    from broker.alpaca import from_alpaca, to_alpaca

    class Session:
        def __init__(self):
            self.headers, self.sent = {}, []

        def request(self, method, url, timeout, **kwargs):
            self.sent.append((method, url, kwargs))

            class Response:
                status_code = 200

                @staticmethod
                def json():
                    return [{"symbol": "BRK.B", "qty": "3"}] if url.endswith("/v2/positions") else {"id": "x"}
            return Response()

    assert to_alpaca("BRK-B") == "BRK.B" and from_alpaca("BF.B") == "BF-B" and to_alpaca("AAPL") == "AAPL"
    session = Session()
    client = AlpacaPaper("k", "s", session=session)
    client.submit_market_order("BRK-B", 2, "buy", "v6-2026-10-30-BRK-B-buy")
    assert session.sent[-1][2]["json"]["symbol"] == "BRK.B"
    assert client.positions() == {"BRK-B": 3.0}


def test_preview_plans_without_sending_or_writing(tmp_path):
    import pandas as pd

    workspace(tmp_path)
    client = FakeClient()
    selected = pd.DataFrame({"ticker": TARGETS, "portfolio_rank": range(1, 21), "date": pd.Timestamp("2026-09-30")})
    from broker.paper_rebalance import preview

    result = preview(tmp_path, client=client, selection_builder=lambda root, model: selected,
                     prices_lookup=lambda symbols: {s: 50.0 for s in symbols})
    assert result["status"] == "preview_only_no_orders_sent" and result["signal_date"] == "2026-09-30"
    assert len(result["planned_orders"]) == 20 and not client.submitted
    assert result["estimated_buy_value"] <= 100_000 * 0.98
    assert not (tmp_path / "paper_trading").exists()


def test_rehearsal_sends_labelled_orders_once_and_closes_after_formal_trading(tmp_path):
    import pandas as pd

    from broker.paper_rebalance import rehearse

    workspace(tmp_path)
    client = FakeClient()
    selected = pd.DataFrame({"ticker": TARGETS, "portfolio_rank": range(1, 21), "date": pd.Timestamp("2026-09-30")})
    kwargs = dict(client=client, selection_builder=lambda root, model: selected,
                  prices_lookup=lambda symbols: {s: 50.0 for s in symbols},
                  ledger=tmp_path / "rehearsal.jsonl", broker_ledger=tmp_path / "broker.jsonl")
    first = rehearse(tmp_path, **kwargs)
    assert first["status"] == "rehearsal_orders_sent" and first["orders"] == 20 and len(client.submitted) == 20
    assert all(cid.startswith("rehearsal-v6-2026-09-30-") for cid in client.orders)
    [event] = read_events(tmp_path / "rehearsal.jsonl")
    assert event["rehearsal_only"] is True and event["official_forward_result"] is False

    assert rehearse(tmp_path, **kwargs)["status"] == "already_rehearsed" and len(client.submitted) == 20

    append(tmp_path / "broker.jsonl", {"event_type": "ORDERS", "signal_date": "2026-10-30", "submitted": []},
           timestamp="2026-11-02T22:00:00Z")
    with pytest.raises(BrokerError, match="formal paper trading has started"):
        rehearse(tmp_path, **kwargs)


def test_formal_rebalance_trades_from_rehearsal_positions():
    held = {t: 96.0 for t in TARGETS[:15]} | {"OLD1": 39.0}  # 98 wanted: inside the band
    targets = TARGETS[:15] + ["NEW1", "NEW2", "NEW3", "NEW4", "NEW5"]
    prices = {s: 50.0 for s in set(targets) | set(held)}
    plan = plan_orders(targets, 100_000, prices, held, cash_buffer=0.02, band=0.10, max_order_fraction=0.10)
    assert {o["symbol"] for o in plan} == {"OLD1", "NEW1", "NEW2", "NEW3", "NEW4", "NEW5"}
    assert plan[0] == {"symbol": "OLD1", "side": "sell", "qty": 39, "reference_price": 50.0}
