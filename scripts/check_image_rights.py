#!/usr/bin/env python3
"""Reject fake image attribution and report images that still need a rights record."""

import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml
from PIL import Image

CONTENT = Path("content")
STATIC = Path("static")
PLACEHOLDERS = {"", "unknown", "none", "null", "anonymous", "internet", "google", "pinterest", "tbd"}


def meta_for(path):
    parts = path.read_text("utf-8").split("---", 2)
    return yaml.safe_load(parts[1]) or {} if len(parts) >= 3 else {}


def valid_url(value):
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and "example." not in parsed.netloc.lower()


def main():
    errors, warnings = [], []
    for path in sorted(CONTENT.rglob("*.md")):
        if path.name == "_index.md":
            continue
        meta = meta_for(path)
        rel = path.relative_to(CONTENT)
        cover = meta.get("cover") or {}
        image = cover.get("image")
        credits = meta.get("image_credits") or []
        if credits and not isinstance(credits, list):
            errors.append(f"{rel}: image_credits must be a list")
            continue
        for number, credit in enumerate(credits, 1):
            if not isinstance(credit, dict):
                errors.append(f"{rel}: image_credits[{number}] must be an object")
                continue
            holder = str(credit.get("holder", credit.get("photographer", credit.get("creator", "")))).strip()
            license_name = str(credit.get("license", "")).strip()
            source = credit.get("source_url", credit.get("author_url", ""))
            if holder.casefold() in PLACEHOLDERS or license_name.casefold() in PLACEHOLDERS:
                errors.append(f"{rel}: image_credits[{number}] has a placeholder holder or license")
            if not valid_url(source):
                errors.append(f"{rel}: image_credits[{number}] has no valid source_url")
        if image and not credits:
            warnings.append(f"{rel}: image rights are not recorded; do not reuse or automate this asset")
        if image and meta.get("image_rights") == "verified" and not credits:
            errors.append(f"{rel}: image_rights is verified but no verifiable credit exists")
        if image and path.parts[1] == "news":
            asset = STATIC / image.lstrip("/")
            try:
                width, _ = Image.open(asset).size
                if width < 1200:
                    warnings.append(f"{rel}: News hero is {width}px wide; prefer a licensed 1200px+ original")
            except (FileNotFoundError, OSError):
                errors.append(f"{rel}: missing/unreadable cover asset {image}")
    if warnings:
        print("[Image Rights] warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    if errors:
        print("[Image Rights] failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("[Image Rights] no fake attribution detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
