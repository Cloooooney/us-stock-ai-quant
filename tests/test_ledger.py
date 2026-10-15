import json
from paper_trading.ledger import append, contains, read_events, validate


def test_ledger_hash_chain_and_duplicate_lookup(tmp_path):
    path = tmp_path / "ledger.jsonl"
    append(path, {"event_type": "SIGNAL", "signal_date": "2026-10-30", "holdings": []}, timestamp="2026-11-02T00:00:00Z")
    append(path, {"event_type": "ENTRY", "signal_date": "2026-10-30", "fills": []}, timestamp="2026-11-02T00:01:00Z")
    valid, tail = validate(path)
    assert valid and len(tail) == 64
    assert contains(path, "SIGNAL", "2026-10-30")
    assert len(read_events(path)) == 2


def test_ledger_detects_tampering(tmp_path):
    path = tmp_path / "ledger.jsonl"
    append(path, {"event_type": "SIGNAL", "signal_date": "2026-10-30"}, timestamp="2026-11-02T00:00:00Z")
    event = json.loads(path.read_text(encoding="utf-8")); event["signal_date"] = "2026-09-30"
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    valid, _ = validate(path)
    assert not valid
