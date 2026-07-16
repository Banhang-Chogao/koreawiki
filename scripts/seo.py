#!/usr/bin/env python3
"""KoreaWiki SEO — validates SEO metadata in front matter."""

import sys, yaml, re
from pathlib import Path

CONTENT = Path("content")
SEP = "---"

def extract_meta(content):
    parts = content.split(SEP)
    if len(parts) >= 3:
        try: return yaml.safe_load(parts[1])
        except: pass
    return {}

def main():
    files = list(CONTENT.rglob("*.md"))
    issues = []
    for fp in files:
        if fp.name == "_index.md": continue
        meta = extract_meta(fp.read_text("utf-8"))
        rel = fp.relative_to(CONTENT)
        errs = []
        t = meta.get("title","")
        if not t: errs.append("Missing title")
        elif len(t) > 120: errs.append(f"Title >120 ({len(t)})")
        elif len(t) < 10: errs.append(f"Title <10 chars")
        d = meta.get("description","")
        if not d: errs.append("Missing description")
        elif len(d) < 50: errs.append(f"Description <50 ({len(d)})")
        elif len(d) > 320: errs.append(f"Description >320 ({len(d)})")
        kw = meta.get("keywords",[])
        if not kw: errs.append("Missing keywords")
        elif len(kw) < 3: errs.append(f"Keywords <3 ({len(kw)})")
        if meta.get("slug","") and not re.match(r'^[a-z0-9\-]+$', meta["slug"]):
            errs.append(f"Invalid slug: {meta['slug']}")
        if not meta.get("date"): errs.append("Missing date")
        if not meta.get("author"): errs.append("Missing author")
        if errs: issues.append((rel, errs))
    if issues:
        print(f"SEO issues in {len(issues)} files:\n")
        for r, e in issues: print(f"  {r}:"); [print(f"    - {x}") for x in e]
        sys.exit(1)
    print("SEO checks passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
