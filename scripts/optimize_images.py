#!/usr/bin/env python3
"""KoreaWiki Image Check — validates image references in content.

Checks:
  - Markdown images ![alt](path)
  - HTML <img src="...">
  - Front matter cover.image (mm workflow hosts under static/)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

CONTENT = Path("content")
STATIC = Path("static")
SEP = "---"


def extract_md_refs(body: str) -> list[str]:
    refs: list[str] = []
    for p in (
        re.compile(r"!\[.*?\]\((.+?)\)"),
        re.compile(r'<img[^>]+src=["\'](.+?)["\']', re.I),
    ):
        refs.extend(p.findall(body))
    return refs


def extract_cover(meta: dict | None) -> str | None:
    if not isinstance(meta, dict):
        return None
    cover = meta.get("cover")
    if isinstance(cover, dict):
        img = cover.get("image")
        if img:
            return str(img).strip()
    elif isinstance(cover, str) and cover.strip():
        return cover.strip()
    return None


def resolve_static(ref: str) -> Path:
    ref = ref.lstrip("/")
    if ref.startswith("images/"):
        return STATIC / ref
    return STATIC / ref


def main() -> int:
    issues: list[tuple[str, str]] = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md":
            continue
        text = fp.read_text("utf-8")
        rel = str(fp.relative_to(CONTENT))
        refs = extract_md_refs(text)
        # front matter cover.image
        if text.startswith(SEP):
            parts = text.split(SEP, 2)
            if len(parts) >= 3:
                try:
                    meta = yaml.safe_load(parts[1]) or {}
                except Exception:
                    meta = {}
                cov = extract_cover(meta)
                if cov:
                    if cov.startswith("http://") or cov.startswith("https://"):
                        # mm must host under static/; legacy remote covers only warn
                        print(
                            f"  WARN {rel}: remote cover.image "
                            f"(mm should host under static/): {cov}"
                        )
                    else:
                        refs.append(cov)
        for ref in refs:
            if ref.startswith("http://") or ref.startswith("https://"):
                continue
            if ref.startswith("data:"):
                continue
            p = resolve_static(ref)
            if not p.exists():
                issues.append((rel, f"Missing: {ref}"))
    if issues:
        print(f"Image issues ({len(issues)}):")
        for r, e in issues:
            print(f"  {r}: {e}")
        return 1
    print("Image check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
