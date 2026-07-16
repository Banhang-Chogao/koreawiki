#!/usr/bin/env python3
"""KoreaWiki Image Check — validates image references in content."""

import sys, re
from pathlib import Path

CONTENT = Path("content")
STATIC = Path("static")

def extract_refs(c):
    refs = []
    for p in [re.compile(r'!\[.*?\]\((.+?)\)'), re.compile(r'<img[^>]+src=["\'](.+?)["\']')]:
        refs.extend(p.findall(c))
    return refs

def main():
    issues = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md": continue
        for ref in extract_refs(fp.read_text("utf-8")):
            if ref.startswith("http"): continue
            p = STATIC / ref.lstrip("/") if ref.startswith("/") else STATIC / ref
            if not p.exists(): issues.append((fp.relative_to(CONTENT), f"Missing: {ref}"))
    if issues:
        print(f"Image issues in {len(issues)} files:"); [print(f"  {r}: {e}") for r,e in issues]
        sys.exit(1)
    print("Image check passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
