"""Write ``automation/status.json`` after a scheduled run.

The status file is pushed to GitHub with the forward ledgers so a remote
reviewer can tell whether the local automation ran, whether it succeeded, and
what each forward record currently contains, without access to the computer.

    python -m automation.status --result success --step monthly_cycle --log automation/logs/x.log
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from paper_trading.ledger import read_events, validate

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "automation/status.json"
LEDGERS = {"v5": ROOT / "paper_trading/v5_ledger.jsonl", "v6": ROOT / "paper_trading/v6_ledger.jsonl"}
LOG_TAIL_LINES = 40


def ledger_status(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    valid, detail = validate(path)
    events = read_events(path) if valid else []
    counts = Counter(e.get("event_type") for e in events)
    signals = sorted(e["signal_date"] for e in events if e.get("event_type") == "SIGNAL")
    entries = sorted(e["signal_date"] for e in events if e.get("event_type") == "ENTRY")
    periods = [e for e in events if e.get("event_type") == "PERIOD"]
    return {"exists": True, "valid": valid, "detail": None if valid else detail,
            "tail_hash": detail if valid else None, "events": dict(counts),
            "latest_signal": signals[-1] if signals else None,
            "signals_without_entry": sorted(set(signals).difference(entries)),
            "periods": len(periods),
            "latest_period": periods[-1]["signal_date"] if periods else None}


def log_tail(path: Path | None, lines: int = LOG_TAIL_LINES) -> list[str]:
    if path is None or not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]


def build(result: str, step: str, log: Path | None, now: datetime | None = None,
          ledgers: dict[str, Path] = LEDGERS) -> dict:
    now = now or datetime.now(timezone.utc)
    status = {"last_attempt_utc": now.isoformat(), "result": result, "step": step,
              "ledgers": {key: ledger_status(path) for key, path in ledgers.items()}}
    if result != "success":
        status["log_tail"] = log_tail(log)
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--result", choices=["success", "failed"], required=True)
    parser.add_argument("--step", required=True)
    parser.add_argument("--log", type=Path)
    args = parser.parse_args()
    status = build(args.result, args.step, args.log)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
