#!/usr/bin/env python3
"""KoreaWiki Link Checker — validates internal links in content."""

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

CONTENT = Path("content")
STATIC = Path("static")
ROOT = Path(".")

# Site-root static prefixes (mm embeds body photos as /images/...)
STATIC_PREFIXES = ("/images/", "/fonts/", "/scss/", "/js/", "/pagefind/")


def extract(c):
    return re.findall(r"\[([^\]]+)\]\(([^)]+)\)", c)


def valid(link):
    p = urlparse(link)
    if p.scheme or p.netloc:
        return False
    if link.startswith("#") or link.startswith("mailto:") or link.startswith("tel:"):
        return False
    return True


def is_static_asset(link: str) -> bool:
    path = link.split("#")[0].split("?")[0]
    return any(path.startswith(p) for p in STATIC_PREFIXES) or path.startswith("images/")


def static_exists(link: str) -> bool:
    path = link.split("#")[0].split("?")[0].lstrip("/")
    return (STATIC / path).exists() or (ROOT / path).exists()


def resolve(link, src):
    if link.startswith("/"):
        return CONTENT / link.lstrip("/").rstrip("/") / "_index.md"
    return src.parent / link


def main():
    broken = []
    for fp in CONTENT.rglob("*.md"):
        c = fp.read_text("utf-8")
        for text, url in extract(c):
            if not valid(url):
                continue
            pure = url.split("#")[0]
            if "#" in url and not pure:
                anchor = url.split("#")[1]
                if f'id="{anchor}"' not in c and f'name="{anchor}"' not in c:
                    broken.append((fp.relative_to(CONTENT), f"Broken anchor #{anchor}"))
                continue
            # Markdown images / assets under static/
            if is_static_asset(pure):
                if not static_exists(pure):
                    broken.append((fp.relative_to(CONTENT), f"Broken static: {url}"))
                continue
            t = resolve(pure, fp)
            if not t.exists() and not any(
                x.exists()
                for x in [
                    t.with_suffix(".md"),
                    t.parent / "index.md",
                    CONTENT / pure.lstrip("/"),
                ]
            ):
                broken.append((fp.relative_to(CONTENT), f"Broken: {url}"))
    if broken:
        print(f"{len(broken)} broken links:")
        for r, e in broken:
            print(f"  {r}: {e}")
        sys.exit(1)
    print("All internal links valid.")
    sys.exit(0)


if __name__ == "__main__":
    main()
