import json
from datetime import datetime, timezone

from automation.status import build
from paper_trading.ledger import append


def test_status_reports_ledger_contents_and_failures(tmp_path):
    v5 = tmp_path / "v5.jsonl"
    append(v5, {"event_type": "SIGNAL", "signal_date": "2026-10-30"}, timestamp="2026-11-02T22:00:00Z")
    log = tmp_path / "run.log"
    log.write_text("\n".join(f"line {i}" for i in range(100)), encoding="utf-8")
    now = datetime(2026, 11, 2, 22, 30, tzinfo=timezone.utc)

    ok = build("success", "monthly_cycle", log, now, {"v5": v5, "v6": tmp_path / "missing.jsonl"})
    assert ok["result"] == "success" and "log_tail" not in ok
    assert ok["ledgers"]["v5"]["valid"] is True
    assert ok["ledgers"]["v5"]["latest_signal"] == "2026-10-30"
    assert ok["ledgers"]["v5"]["signals_without_entry"] == ["2026-10-30"]
    assert ok["ledgers"]["v6"] == {"exists": False}

    failed = build("failed", "monthly_cycle", log, now, {"v5": v5})
    assert failed["log_tail"][-1] == "line 99" and len(failed["log_tail"]) == 40
    json.dumps(failed)


def test_status_flags_a_tampered_ledger(tmp_path):
    v5 = tmp_path / "v5.jsonl"
    append(v5, {"event_type": "SIGNAL", "signal_date": "2026-10-30"}, timestamp="2026-11-02T22:00:00Z")
    v5.write_text(v5.read_text(encoding="utf-8").replace("2026-10-30", "2026-09-30"), encoding="utf-8")
    status = build("success", "monthly_cycle", None, ledgers={"v5": v5})
    assert status["ledgers"]["v5"]["valid"] is False


def test_ledger_lines_end_with_lf(tmp_path):
    path = tmp_path / "ledger.jsonl"
    append(path, {"event_type": "SIGNAL", "signal_date": "2026-10-30"}, timestamp="2026-11-02T22:00:00Z")
    assert b"\r\n" not in path.read_bytes()
