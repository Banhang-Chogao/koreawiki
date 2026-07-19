#!/usr/bin/env python3
"""Validate the Google News sitemap without requiring every news article to be new."""

import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

CONTENT = Path("content/news")
PUBLIC = Path("public")
WINDOW = timedelta(hours=48)
NEWS_NS = {"n": "http://www.google.com/schemas/sitemap-news/0.9", "s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def load_meta(path):
    parts = path.read_text("utf-8").split("---", 2)
    return yaml.safe_load(parts[1]) or {} if len(parts) >= 3 else {}


def as_datetime(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, datetime.min.time())
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError(f"unsupported date value {value!r}")
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def eligible_pages(now):
    pages = []
    for path in CONTENT.glob("*.md"):
        if path.name == "_index.md":
            continue
        meta = load_meta(path)
        try:
            published = as_datetime(meta.get("date"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{path}: invalid date: {exc}") from exc
        if not meta.get("draft") and now - WINDOW <= published <= now:
            pages.append((path, meta, published))
    return pages


def check_built_sitemap(expected, now, public):
    errors = []
    sitemap = public / "news.xml"
    if not sitemap.exists():
        return [f"missing built News sitemap: {sitemap}"]
    try:
        root = ET.parse(sitemap).getroot()
    except ET.ParseError as exc:
        return [f"invalid XML in {sitemap}: {exc}"]
    locs = set()
    for node in root.findall("s:url", NEWS_NS):
        loc = node.findtext("s:loc", namespaces=NEWS_NS)
        published = node.findtext("n:news/n:publication_date", namespaces=NEWS_NS)
        title = node.findtext("n:news/n:title", namespaces=NEWS_NS)
        if not loc or not published or not title:
            errors.append("news sitemap entry misses loc, publication_date, or title")
            continue
        locs.add(loc)
        try:
            timestamp = as_datetime(published)
        except ValueError as exc:
            errors.append(f"{loc}: invalid publication_date: {exc}")
            continue
        if timestamp > now or now - timestamp > WINDOW:
            errors.append(f"{loc}: outside 48-hour News sitemap window")
    expected_urls = {meta.get("canonical", "") for _, meta, _ in expected if meta.get("canonical")}
    # Canonical is optional in front matter, so only use it when supplied. All emitted URLs
    # are independently checked above; Hugo determines the final permalink.
    if expected_urls and not expected_urls.issubset(locs):
        errors.append("a canonical URL eligible for News sitemap was not emitted")
    return errors


def main():
    now = datetime.now(timezone.utc)
    try:
        expected = eligible_pages(now)
    except ValueError as exc:
        print(f"[News Sitemap] {exc}")
        return 1
    errors = []
    if "--postbuild" in sys.argv:
        public = Path(sys.argv[sys.argv.index("--public") + 1]) if "--public" in sys.argv else PUBLIC
        errors.extend(check_built_sitemap(expected, now, public))
    if errors:
        print("[News Sitemap] failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"[News Sitemap] {len(expected)} eligible article(s) in the rolling 48-hour window.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
