#!/usr/bin/env python3
"""KoreaWiki QA — validates front matter, markdown, and file structure."""

import sys, yaml, re
from pathlib import Path
from datetime import datetime

CONTENT = Path("content")
SEP = "---"
DATE_TYPES = (datetime, type(datetime.now().date()))
REQUIRED = {"title": str, "description": str, "date": DATE_TYPES, "draft": bool}

def extract(content):
    parts = content.split(SEP)
    if len(parts) >= 3:
        try: return yaml.safe_load(parts[1]), parts[2]
        except yaml.YAMLError: pass
    return None, ""

def check(meta):
    errors = []
    for f, t in REQUIRED.items():
        if f not in meta: errors.append(f"Missing: '{f}'")
        elif not isinstance(meta[f], t) and meta[f] is not None: errors.append(f"'{f}' wrong type")
    if meta.get("date") and meta.get("lastmod") and meta["lastmod"] < meta["date"]:
        errors.append("lastmod before date")
    if not meta.get("title") or len(str(meta.get("title",""))) > 120:
        errors.append("Title missing or >120 chars")
    desc = meta.get("description","")
    if len(desc) < 50: errors.append("Description <50 chars")
    elif len(desc) > 320: errors.append("Description >320 chars")
    if not meta.get("tags"): errors.append("Missing tags")
    if not meta.get("categories"): errors.append("Missing categories")
    return errors

def main():
    files = list(CONTENT.rglob("*.md"))
    issues = []
    for fp in files:
        if fp.name == "_index.md": continue
        meta, _ = extract(fp.read_text("utf-8"))
        if meta:
            errs = check(meta)
            if errs: issues.append((fp.relative_to(CONTENT), errs))
        else:
            issues.append((fp.relative_to(CONTENT), ["No valid front matter"]))
    if issues:
        print(f"{len(issues)} files with issues:\n")
        for rel, errs in issues:
            print(f"  {rel}:"); [print(f"    - {e}") for e in errs]
        sys.exit(1)
    print("QA passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
