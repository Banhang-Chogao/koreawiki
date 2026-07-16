#!/usr/bin/env python3
"""KoreaWiki Translate — exports content for translation to JSON."""

import sys, json, yaml
from pathlib import Path

CONTENT = Path("content")
SEP = "---"

def extract(fp):
    c = fp.read_text("utf-8")
    parts = c.split(SEP)
    if len(parts) < 3: return None
    try: meta = yaml.safe_load(parts[1])
    except: return None
    return {"source": str(fp.relative_to(CONTENT)), "title": meta.get("title",""), "description": meta.get("description",""), "keywords": meta.get("keywords",[]), "body": parts[2].strip()}

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "export"
    units = [u for fp in CONTENT.rglob("*.md") if fp.name != "_index.md" and (u := extract(fp))]
    if action == "export":
        Path("translations.json").write_text(json.dumps(units, ensure_ascii=False, indent=2), "utf-8")
        print(f"Exported {len(units)} units to translations.json")
    elif action == "validate":
        empty = [u for u in units if not u.get("body")]
        if empty: print(f"{len(empty)} files empty"); [print(f"  - {u['source']}") for u in empty]
        else: print(f"All {len(units)} files have content.")
    sys.exit(0)

if __name__ == "__main__":
    main()
