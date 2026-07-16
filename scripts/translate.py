#!/usr/bin/env python3
"""KoreaWiki Translate — exports content for translation to JSON.

Before translating, consult the Translation Memory:

  python3 scripts/glossary.py consult
  python3 scripts/glossary.py lookup <term>

After translating (mm workflow), extract and upsert terms:

  python3 scripts/glossary.py upsert --file entries.json
  python3 scripts/glossary.py sync
"""

import sys, json, yaml
from pathlib import Path

CONTENT = Path("content")
SEP = "---"
GLOSSARY_JSON = Path("data/glossary/glossary.json")

def extract(fp):
    c = fp.read_text("utf-8")
    parts = c.split(SEP)
    if len(parts) < 3: return None
    try: meta = yaml.safe_load(parts[1])
    except: return None
    return {"source": str(fp.relative_to(CONTENT)), "title": meta.get("title",""), "description": meta.get("description",""), "keywords": meta.get("keywords",[]), "body": parts[2].strip()}

def load_tm_hint(limit=100):
    """Lightweight TM slice for inclusion in translation export."""
    if not GLOSSARY_JSON.exists():
        return []
    try:
        data = json.loads(GLOSSARY_JSON.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    entries = data.get("entries") or []
    out = []
    for e in entries[:limit]:
        out.append({
            "korean": e.get("korean", ""),
            "vietnamese": e.get("vietnamese", ""),
            "category": e.get("category", ""),
            "context": e.get("context", ""),
        })
    return out

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "export"
    units = [u for fp in CONTENT.rglob("*.md") if fp.name != "_index.md" and (u := extract(fp))]
    if action == "export":
        payload = {
            "units": units,
            "translation_memory": load_tm_hint(),
            "note": "Prefer translation_memory renderings for terminology consistency. Full TM: python3 scripts/glossary.py consult",
        }
        Path("translations.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
        print(f"Exported {len(units)} units + {len(payload['translation_memory'])} TM hints to translations.json")
    elif action == "validate":
        empty = [u for u in units if not u.get("body")]
        if empty: print(f"{len(empty)} files empty"); [print(f"  - {u['source']}") for u in empty]
        else: print(f"All {len(units)} files have content.")
    elif action == "consult":
        # Delegate to glossary manager
        import subprocess
        sys.exit(subprocess.call([sys.executable, str(Path("scripts/glossary.py")), "consult"] + sys.argv[2:]))
    sys.exit(0)

if __name__ == "__main__":
    main()
