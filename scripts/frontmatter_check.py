#!/usr/bin/env python3
"""KoreaWiki Frontmatter Check — validates YAML front matter completeness and correctness."""

import sys, yaml
from pathlib import Path
from datetime import datetime

CONTENT = Path("content")
SEP = "---"
DATE_TYPES = (datetime, type(datetime.now().date()))
FIELDS = {
    "title": (str, True), "description": (str, True), "keywords": (list, False),
    "date": (DATE_TYPES, True), "lastmod": (DATE_TYPES, False), "draft": (bool, False),
    "author": (str, False), "tags": (list, False), "categories": (list, False),
    "slug": (str, False), "showToc": (bool, False), "readingTime": (bool, False),
}

def main():
    issues = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md": continue
        parts = fp.read_text("utf-8").split(SEP)
        if len(parts) < 3: issues.append((fp.relative_to(CONTENT), "No front matter")); continue
        try: meta = yaml.safe_load(parts[1])
        except yaml.YAMLError as e: issues.append((fp.relative_to(CONTENT), f"YAML error: {e}")); continue
        if not isinstance(meta, dict): issues.append((fp.relative_to(CONTENT), "Front matter not a dict")); continue
        errs = []
        for field, (ftype, required) in FIELDS.items():
            if field in meta:
                if not isinstance(meta[field], ftype) and meta[field] is not None:
                    errs.append(f"'{field}' wrong type (expected {ftype.__name__})")
            elif required:
                errs.append(f"Missing required '{field}'")
        if errs: issues.append((fp.relative_to(CONTENT), errs))
    if issues:
        print(f"Issues in {len(issues)} files:\n")
        for r, e in issues:
            print(f"  {r}:")
            if isinstance(e, list): [print(f"    - {x}") for x in e]
            else: print(f"    - {e}")
        sys.exit(1)
    print("Front matter check passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
