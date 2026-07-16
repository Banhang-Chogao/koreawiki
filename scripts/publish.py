#!/usr/bin/env python3
"""KoreaWiki Publish — sets draft=false and updates lastmod."""

import sys, yaml
from pathlib import Path
from datetime import datetime

CONTENT = Path("content")
SEP = "---"

def publish(fp):
    c = fp.read_text("utf-8")
    parts = c.split(SEP)
    if len(parts) < 3: return False
    try: meta = yaml.safe_load(parts[1])
    except: return False
    if not meta: return False
    changed = False
    if meta.get("draft", True):
        meta["draft"] = False; changed = True
    meta["lastmod"] = datetime.now()
    new_y = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)
    fp.write_text(f"{SEP}\n{new_y}{SEP}\n{parts[2].lstrip()}", "utf-8")
    return changed

def main():
    paths = [Path(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else list(CONTENT.rglob("*.md"))
    pub = []
    for fp in paths:
        if fp.name == "_index.md": continue
        if publish(fp): pub.append(fp.relative_to(CONTENT))
    if pub:
        print(f"Published {len(pub)} files:"); [print(f"  - {p}") for p in pub]
    else: print("No changes.")
    sys.exit(0)

if __name__ == "__main__":
    main()
