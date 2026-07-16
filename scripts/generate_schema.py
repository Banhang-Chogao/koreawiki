#!/usr/bin/env python3
"""KoreaWiki Schema — validates JSON-LD in built output."""

import sys, json, re
from pathlib import Path

PUBLIC = Path("public")

def main():
    if not PUBLIC.exists(): print("Build the site first (public/ missing)."); sys.exit(1)
    errors = []
    for fp in PUBLIC.rglob("*.html"):
        html = fp.read_text("utf-8")
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
            try:
                s = json.loads(m.group(1))
                if "@context" not in s: errors.append((fp.relative_to(PUBLIC), "Missing @context"))
                if "@type" not in s: errors.append((fp.relative_to(PUBLIC), "Missing @type"))
                if s.get("@type") == "Article":
                    for k in ["headline","datePublished","author"]:
                        if k not in s: errors.append((fp.relative_to(PUBLIC), f"Article missing {k}"))
            except json.JSONDecodeError:
                errors.append((fp.relative_to(PUBLIC), "Invalid JSON-LD"))
    if errors:
        print(f"Schema errors in {len(errors)}:"); [print(f"  {r}: {e}") for r,e in errors]
        sys.exit(1)
    print("Schema validation passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
