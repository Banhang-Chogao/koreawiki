#!/usr/bin/env python3
"""Post-build checks for canonical URLs, feeds, sitemaps, noindex and Pagefind."""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PUBLIC = Path("public")
BASE = "https://banhang-chogao.github.io/koreawiki/"


def main():
    public = Path(sys.argv[sys.argv.index("--public") + 1]) if "--public" in sys.argv else PUBLIC
    errors = []
    for filename in ("sitemap.xml", "news.xml", "index.xml"):
        path = public / filename
        if not path.exists():
            errors.append(f"missing {filename}")
        else:
            try:
                ET.parse(path)
            except ET.ParseError as exc:
                errors.append(f"invalid {filename}: {exc}")
    for path in public.rglob("index.html"):
        rel = path.relative_to(public).parent.as_posix().strip("/")
        html = path.read_text("utf-8")
        # Hugo creates page/1 and language aliases as tiny canonical redirects. They
        # intentionally do not include the regular document head or robots policy.
        if 'http-equiv=refresh' in html:
            continue
        canonical = re.findall(r'<link\s+rel=canonical\s+href=(?:"([^"]+)"|([^\s>]+))', html)
        canonical = [(quoted or bare) for quoted, bare in canonical]
        if len(canonical) != 1 or not canonical[0].startswith(BASE):
            errors.append(f"{path.relative_to(public)}: invalid canonical")
        should_noindex = rel.startswith(("tags", "categories", "search")) or "/page/" in f"/{rel}/"
        if should_noindex and 'content="noindex, follow, max-image-preview:large"' not in html:
            errors.append(f"{path.relative_to(public)}: thin archive must be noindex")
        if "max-image-preview:large" not in html:
            errors.append(f"{path.relative_to(public)}: missing max-image-preview:large")
    if (public / "pagefind").exists() is False:
        errors.append("missing Pagefind search index")
    if errors:
        print("[Build SEO] failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("[Build SEO] passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
