#!/usr/bin/env python3
"""Validate JSON-LD that Hugo emitted, including full NewsArticle requirements."""

import json
import re
import sys
from pathlib import Path

PUBLIC = Path("public")
SCRIPT_RE = re.compile(r'<script\s+type=(?:"application/ld\+json"|application/ld\+json)>\s*(.*?)\s*</script>', re.DOTALL)


def non_empty(value):
    return bool(value) and (not isinstance(value, str) or value not in {"null", "None"})


def validate_item(item, rel):
    errors = []
    if not isinstance(item, dict):
        return [f"{rel}: JSON-LD item is not an object"]
    if item.get("@context") != "https://schema.org" or not non_empty(item.get("@type")):
        errors.append(f"{rel}: JSON-LD misses @context or @type")
    if item.get("@type") == "NewsArticle":
        required = ("headline", "description", "image", "datePublished", "dateModified", "author", "publisher", "mainEntityOfPage")
        for field in required:
            if not non_empty(item.get(field)):
                errors.append(f"{rel}: NewsArticle missing {field}")
        if not isinstance(item.get("author"), dict) or not non_empty(item["author"].get("name")):
            errors.append(f"{rel}: NewsArticle author needs a real name")
        if not isinstance(item.get("publisher"), dict) or not non_empty(item["publisher"].get("name")):
            errors.append(f"{rel}: NewsArticle publisher needs a name")
        if not isinstance(item.get("mainEntityOfPage"), dict) or not non_empty(item["mainEntityOfPage"].get("@id")):
            errors.append(f"{rel}: NewsArticle mainEntityOfPage needs @id")
    if item.get("@type") == "BreadcrumbList" and not item.get("itemListElement"):
        errors.append(f"{rel}: BreadcrumbList is empty")
    return errors


def main():
    public = Path(sys.argv[sys.argv.index("--public") + 1]) if "--public" in sys.argv else PUBLIC
    if not public.exists():
        print(f"Build the site first ({public}/ missing).")
        return 1
    errors = []
    for path in public.rglob("*.html"):
        rel = path.relative_to(public)
        if rel.name == "404.html":
            continue
        rel_text = rel.as_posix()
        is_language_home = len(rel.parts) == 2 and rel.name == "index.html" and rel.parts[0] in {"en", "ko", "vi"}
        is_noncanonical_archive = "/page/" in f"/{rel_text}" or rel.parts[0] in {"tags", "categories"}
        items = []
        for match in SCRIPT_RE.finditer(path.read_text("utf-8")):
            try:
                payload = json.loads(match.group(1))
            except json.JSONDecodeError as exc:
                errors.append(f"{rel}: invalid JSON-LD: {exc.msg}")
                continue
            items.extend(payload if isinstance(payload, list) else [payload])
        if not items and (is_noncanonical_archive or is_language_home):
            continue
        if not items:
            errors.append(f"{rel}: no JSON-LD emitted")
            continue
        for item in items:
            errors.extend(validate_item(item, rel))
        if rel.parts and rel.parts[0] == "news" and len(rel.parts) > 2 and not any(item.get("@type") == "NewsArticle" for item in items if isinstance(item, dict)):
            errors.append(f"{rel}: news page did not emit NewsArticle")
        if rel != Path("index.html") and not is_language_home and not any(item.get("@type") == "BreadcrumbList" for item in items if isinstance(item, dict)):
            errors.append(f"{rel}: missing BreadcrumbList")
    if errors:
        print(f"Schema errors in {len(errors)} item(s):")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Schema validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
