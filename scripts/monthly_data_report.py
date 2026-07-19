#!/usr/bin/env python3
"""Create a source-backed monthly data summary; never manufacture missing metrics."""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports/seo"


def valid_url(value):
    parsed = urlparse(str(value or ""))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main():
    events = []
    for path in (ROOT / "data/calendar").glob("*.json"):
        events.extend(json.loads(path.read_text("utf-8")).get("events", []))
    locations = json.loads((ROOT / "data/locations.json").read_text("utf-8"))
    places = [item for group in locations.values() for item in group]
    registry = yaml.safe_load((ROOT / "data/entities/registry.yaml").read_text("utf-8")) or {}
    eligible_events = [event for event in events if valid_url((event.get("source") or {}).get("url"))]
    eligible_places = [place for place in places if valid_url((place.get("source") or {}).get("url"))]
    eligible_entities = [entity for entity in registry.values() if valid_url(entity.get("source_url"))]
    REPORTS.mkdir(parents=True, exist_ok=True)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    report = REPORTS / f"monthly-data-{month}.md"
    report.write_text("\n".join([f"# KoreaWiki data report — {month}", "", "## Method", "Only records with a valid source URL are counted. Missing data is reported as missing, never estimated.", "", "## Published structured records", f"- Calendar events with sources: {len(eligible_events)}", f"- Places with sources: {len(eligible_places)}", f"- Entity profiles with sources: {len(eligible_entities)}", "", "## Source collections", "- `data/calendar/*.json`", "- `data/locations.json`", "- `data/entities/registry.yaml`", "" ]), "utf-8")
    print(f"[Monthly data] wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
