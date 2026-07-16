#!/usr/bin/env python3
"""KoreaWiki Link Checker — validates internal links in content."""

import sys, re
from pathlib import Path
from urllib.parse import urlparse

CONTENT = Path("content")

def extract(c):
    return re.findall(r'\[([^\]]+)\]\(([^)]+)\)', c)

def valid(link):
    p = urlparse(link)
    if p.scheme or p.netloc: return False
    if link.startswith("#") or link.startswith("mailto:") or link.startswith("tel:"): return False
    return True

def resolve(link, src):
    if link.startswith("/"): return CONTENT / link.lstrip("/").rstrip("/") / "_index.md"
    return src.parent / link

def main():
    broken = []
    for fp in CONTENT.rglob("*.md"):
        c = fp.read_text("utf-8")
        for text, url in extract(c):
            if not valid(url): continue
            if "#" in url:
                anchor = url.split("#")[1]
                if not url.split("#")[0] and f'id="{anchor}"' not in c and f'name="{anchor}"' not in c:
                    broken.append((fp.relative_to(CONTENT), f"Broken anchor #{anchor}"))
                continue
            t = resolve(url, fp)
            if not t.exists() and not any(x.exists() for x in [t.with_suffix(".md"), t.parent / "index.md", CONTENT / url.lstrip("/")]):
                broken.append((fp.relative_to(CONTENT), f"Broken: {url}"))
    if broken:
        print(f"{len(broken)} broken links:"); [print(f"  {r}: {e}") for r,e in broken]
        sys.exit(1)
    print("All internal links valid.")
    sys.exit(0)

if __name__ == "__main__":
    main()
