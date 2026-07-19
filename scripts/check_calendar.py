#!/usr/bin/env python3
"""Validate the structured, fixed-URL calendar data."""

import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

DATA = Path("data/calendar")
ALLOWED_TYPES = {"comeback", "concert", "fanmeeting", "award", "drama", "achievement", "photoshoot"}
ALLOWED_STATUS = {"announced", "confirmed", "reported", "cancelled"}


def valid_url(value):
    parsed = urlparse(str(value or ""))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main():
    errors, ids = [], set()
    for path in sorted(DATA.glob("*.json")):
        try:
            payload = json.loads(path.read_text("utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON: {exc}")
            continue
        for number, event in enumerate(payload.get("events", []), 1):
            prefix = f"{path.name} event {number}"
            event_id = event.get("id")
            if not event_id or event_id in ids:
                errors.append(f"{prefix}: missing or duplicate id")
            ids.add(event_id)
            try:
                date.fromisoformat(event.get("date", ""))
            except ValueError:
                errors.append(f"{prefix}: invalid date")
            if event.get("type") not in ALLOWED_TYPES:
                errors.append(f"{prefix}: unsupported type")
            if event.get("status") not in ALLOWED_STATUS:
                errors.append(f"{prefix}: unsupported status")
            source = event.get("source") or {}
            if not source.get("name") or not valid_url(source.get("url")):
                errors.append(f"{prefix}: source name and valid URL are required")
            if not str(event.get("url", "")).startswith("/"):
                errors.append(f"{prefix}: internal stable URL is required")
    if errors:
        print("[Calendar] failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"[Calendar] valid ({len(ids)} events).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
