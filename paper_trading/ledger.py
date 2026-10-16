from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def read_events(path: Path) -> list[dict]:
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(path: Path) -> tuple[bool, str]:
    previous = GENESIS
    for number, event in enumerate(read_events(path), 1):
        claimed = event.get("event_hash"); body = {k: v for k, v in event.items() if k != "event_hash"}
        if body.get("previous_hash") != previous:
            return False, f"line {number}: previous hash mismatch"
        actual = hashlib.sha256((previous + canonical(body)).encode("utf-8")).hexdigest()
        if claimed != actual:
            return False, f"line {number}: event hash mismatch"
        previous = claimed
    return True, previous


def append(path: Path, payload: dict, timestamp: str | None = None) -> dict:
    valid, previous = validate(path)
    if not valid: raise ValueError(f"refusing to append to invalid ledger: {previous}")
    event = {**payload, "recorded_at_utc": timestamp or datetime.now(timezone.utc).isoformat(),
             "previous_hash": previous}
    event["event_hash"] = hashlib.sha256((previous + canonical(event)).encode("utf-8")).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:  # LF on every OS, matching .gitattributes
        handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush(); os.fsync(handle.fileno())
    return event


def contains(path: Path, event_type: str, signal_date: str) -> bool:
    return any(e.get("event_type") == event_type and e.get("signal_date") == signal_date for e in read_events(path))
