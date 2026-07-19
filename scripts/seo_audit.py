#!/usr/bin/env python3
"""Production SEO/content integrity checks that do not invent validation results."""

import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

CONTENT = Path("content")
REGISTRY = Path("data/entities/registry.yaml")
PLACEHOLDERS = {"", "unknown", "none", "null", "tbd", "todo", "example"}


def split(path):
    parts = path.read_text("utf-8").split("---", 2)
    if len(parts) < 3:
        return {}, ""
    return yaml.safe_load(parts[1]) or {}, parts[2]


def as_datetime(value):
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, date):
        result = datetime.combine(value, datetime.min.time())
    elif isinstance(value, str):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("missing or invalid date")
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def valid_url(value):
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and "example." not in parsed.netloc.lower()


def normalise(text):
    return re.sub(r"\W+", " ", str(text).casefold()).strip()


def main():
    errors, warnings, titles = [], [], {}
    registry = yaml.safe_load(REGISTRY.read_text("utf-8")) if REGISTRY.exists() else {}
    now = datetime.now(timezone.utc)
    for path in sorted(CONTENT.rglob("*.md")):
        rel = path.relative_to(CONTENT)
        meta, body = split(path)
        if not meta:
            errors.append(f"{rel}: invalid front matter")
            continue
        if path.name == "_index.md":
            if meta.get("noindex") is False and len(body.split()) < 60:
                errors.append(f"{rel}: explicitly indexed hub has thin content")
            continue
        section = rel.parts[0]
        for field in ("title", "description", "date", "author"):
            if not meta.get(field):
                errors.append(f"{rel}: missing {field}")
        try:
            published = as_datetime(meta.get("date"))
            if published > now:
                scheduled = meta.get("scheduled") is True
                publish_date = as_datetime(meta.get("publishDate")) if meta.get("publishDate") else None
                if not (scheduled and publish_date and publish_date >= published):
                    errors.append(f"{rel}: future date without a valid schedule")
        except ValueError:
            errors.append(f"{rel}: invalid date")
        title_key = normalise(meta.get("title"))
        if title_key:
            if title_key in titles:
                errors.append(f"{rel}: duplicate search intent title also used by {titles[title_key]}")
            titles[title_key] = rel
        if section not in {"authors", "entities"}:
            sources = meta.get("sources")
            if not isinstance(sources, list) or not sources:
                errors.append(f"{rel}: published article needs at least one named source")
            else:
                for number, source in enumerate(sources, 1):
                    if not isinstance(source, dict) or str(source.get("name", "")).casefold() in PLACEHOLDERS or not valid_url(source.get("url")):
                        errors.append(f"{rel}: source {number} is missing a real name or URL")
            if not meta.get("verification_status"):
                errors.append(f"{rel}: missing verification_status")
        entity_ids = meta.get("entities", []) or []
        if not isinstance(entity_ids, list):
            errors.append(f"{rel}: entities must be a list")
        for entity_id in entity_ids:
            entry = registry.get(entity_id)
            if not entry or not entry.get("url") or not valid_url(entry.get("source_url")):
                errors.append(f"{rel}: entity '{entity_id}' is missing from the sourced registry")
        if section == "news":
            for field in ("title", "description", "author", "date"):
                if not meta.get(field):
                    errors.append(f"{rel}: NewsArticle requires {field}")
            if not (meta.get("cover") or {}).get("image"):
                errors.append(f"{rel}: NewsArticle requires a cover image")
            if not entity_ids:
                errors.append(f"{rel}: news item requires an entity link")
        if section == "entities":
            entity = meta.get("entity") or {}
            entity_id = entity.get("id")
            if not entity_id or entity_id not in registry:
                errors.append(f"{rel}: entity page has no matching registry item")
            elif registry[entity_id].get("url") != f"/entities/{meta.get('slug', path.stem)}/":
                errors.append(f"{rel}: registry URL does not match stable entity slug")
            if len(body.split()) < 120:
                errors.append(f"{rel}: entity profile is too thin")
        if len(body.split()) < 100 and section not in {"authors", "entities"}:
            warnings.append(f"{rel}: short body ({len(body.split())} words)")
    if errors:
        print("[SEO Audit] failed:")
        for error in errors:
            print(f"  - {error}")
    if warnings:
        print("[SEO Audit] warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    if not errors:
        print("[SEO Audit] passed.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
