#!/usr/bin/env python3
"""
glossary.py — KoreaWiki Translation Memory & Glossary System

Usage:
  python3 scripts/glossary.py add <korean> <vietnamese> [--context ...]
  python3 scripts/glossary.py search <query>
  python3 scripts/glossary.py merge
  python3 scripts/glossary.py validate
  python3 scripts/glossary.py export [--format json|csv|md|sqlite]
  python3 scripts/glossary.py import <file>
  python3 scripts/glossary.py list [--category ...] [--tag ...]
  python3 scripts/glossary.py stats
  python3 scripts/glossary.py extract <source_json>  # extract from mm output
"""

import sys, json, csv, os, re, sqlite3, textwrap
from datetime import date, datetime
from pathlib import Path
from collections import defaultdict
from shutil import which

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_DIR = ROOT / "data" / "glossary"
EXPORT_DIR = ROOT / "scripts" / "glossary_export"
JSON_PATH = GLOSSARY_DIR / "glossary.json"
PUBLIC_JSON = GLOSSARY_DIR / "public.json"
MD_PATH = EXPORT_DIR / "glossary.md"
CSV_PATH = EXPORT_DIR / "glossary.csv"
DB_PATH = EXPORT_DIR / "glossary.sqlite"
PUBLIC_JSON = GLOSSARY_DIR / "public.json"  # sanitized for Hugo

FIELDS = [
    "id", "korean", "vietnamese", "romanization", "pos", "meaning",
    "context", "example_kr", "example_vi", "source", "category",
    "first_seen", "last_seen", "frequency", "tags"
]

REQUIRED = ["korean", "vietnamese"]
PUBLIC_FIELDS = ["korean", "vietnamese", "romanization", "pos", "meaning",
                 "context", "example_kr", "example_vi", "category", "tags"]

CATEGORIES = [
    "noun", "verb", "adjective", "adverb", "particle", "suffix",
    "grammar", "expression", "idiom", "slang", "proverb",
    "name", "person", "organization", "place", "title",
    "food", "clothing", "technology", "other"
]

CONTEXTS = [
    "entertainment", "kdrama", "kpop", "news", "culture",
    "history", "society", "travel", "food", "daily",
    "business", "technology", "academic", "formal", "informal"
]

# ---------- Core DB ----------

def load():
    if not JSON_PATH.exists():
        return []
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))

def save(entries):
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

def next_id(entries):
    return max((e.get("id", 0) for e in entries), default=0) + 1

def find(entries, korean=None, vietnamese=None, entry_id=None):
    for e in entries:
        if entry_id and e.get("id") == entry_id:
            return e
        if korean and e.get("korean", "").strip() == korean.strip():
            return e
        if vietnamese and e.get("vietnamese", "").strip() == vietnamese.strip():
            # match vietnamese only if korean also matches
            if korean and e.get("korean", "").strip() == korean.strip():
                return e
    return None

def add_entry(korean, vietnamese, **kwargs):
    entries = load()
    existing = find(entries, korean=korean, vietnamese=vietnamese)
    today = date.today().isoformat()

    if existing:
        existing["frequency"] = existing.get("frequency", 1) + 1
        existing["last_seen"] = today
        for k, v in kwargs.items():
            if v and k in FIELDS:
                existing[k] = v
        save(entries)
        return existing, "updated"

    entry = {
        "id": next_id(entries),
        "korean": korean.strip(),
        "vietnamese": vietnamese.strip(),
        "romanization": kwargs.get("romanization", ""),
        "pos": kwargs.get("pos", ""),
        "meaning": kwargs.get("meaning", ""),
        "context": kwargs.get("context", ""),
        "example_kr": kwargs.get("example_kr", ""),
        "example_vi": kwargs.get("example_vi", ""),
        "source": kwargs.get("source", ""),
        "category": kwargs.get("category", ""),
        "first_seen": today,
        "last_seen": today,
        "frequency": 1,
        "tags": kwargs.get("tags", []),
    }
    entries.append(entry)
    save(entries)
    return entry, "created"

def delete_entry(entry_id):
    entries = load()
    entries = [e for e in entries if e.get("id") != int(entry_id)]
    save(entries)

def update_entry(entry_id, **kwargs):
    entries = load()
    for e in entries:
        if e.get("id") == int(entry_id):
            for k, v in kwargs.items():
                if v is not None and k in FIELDS:
                    e[k] = v
            save(entries)
            return e
    return None

# ---------- Search ----------

def search_entries(query, entries=None):
    if entries is None:
        entries = load()
    q = query.lower().strip()
    if not q:
        return entries
    results = []
    for e in entries:
        searchable = " ".join(str(e.get(f, "")) for f in FIELDS if f != "id").lower()
        if q in searchable:
            results.append(e)
    return results

# ---------- Merge ----------

def merge_duplicates():
    entries = load()
    groups = defaultdict(list)
    for e in entries:
        key = (e.get("korean", "").strip(), e.get("vietnamese", "").strip())
        groups[key].append(e)

    merged = []
    dups_found = 0
    for key, group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
            continue
        # merge: keep first, accumulate stats
        base = dict(group[0])
        for dup in group[1:]:
            base["frequency"] = base.get("frequency", 1) + dup.get("frequency", 1)
            base["last_seen"] = max(base.get("last_seen", ""), dup.get("last_seen", ""))
            base["first_seen"] = min(base.get("first_seen", ""), dup.get("first_seen", ""))
            if dup.get("source") and dup["source"] not in base.get("source", ""):
                base["source"] = (base.get("source", "") + "; " + dup["source"]).strip("; ")
            base_tags = set(base.get("tags", []))
            base_tags.update(dup.get("tags", []))
            base["tags"] = sorted(base_tags)
            dups_found += 1
        merged.append(base)

    save(merged)
    return len(merged), dups_found

# ---------- Validate ----------

def validate():
    entries = load()
    issues = []
    for e in entries:
        for field in REQUIRED:
            if not e.get(field, "").strip():
                issues.append(f"#{e.get('id')}: missing required field '{field}'")
        if e.get("category") and e["category"] not in CATEGORIES:
            issues.append(f"#{e.get('id')}: invalid category '{e['category']}'")
        if e.get("context") and e["context"] not in CONTEXTS:
            issues.append(f"#{e.get('id')}: invalid context '{e['context']}'")
        if len(e.get("korean", "")) > 200:
            issues.append(f"#{e.get('id')}: korean field too long ({len(e['korean'])} chars)")
    # check duplicates
    seen = set()
    for e in entries:
        key = (e.get("korean", "").strip(), e.get("vietnamese", "").strip())
        if key in seen:
            issues.append(f"#{e.get('id')}: duplicate ({key[0]} → {key[1]})")
        seen.add(key)
    return issues

# ---------- Export ----------

def export_md(entries=None):
    if entries is None:
        entries = load()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# KoreaWiki Glossary",
        "",
        f"Total entries: {len(entries)}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| Korean | Vietnamese | Romanization | POS | Context | Category | Source | Updated |",
        "|--------|-----------|-------------|-----|---------|----------|--------|---------|",
    ]
    for e in sorted(entries, key=lambda x: x.get("korean", "")):
        lines.append(
            f"| {e.get('korean', '')} "
            f"| {e.get('vietnamese', '')} "
            f"| {e.get('romanization', '')} "
            f"| {e.get('pos', '')} "
            f"| {e.get('context', '')} "
            f"| {e.get('category', '')} "
            f"| {e.get('source', '')} "
            f"| {e.get('last_seen', '')} |"
        )
    return "\n".join(lines) + "\n"

def export_csv(entries=None):
    if entries is None:
        entries = load()
    output = []
    header = FIELDS
    output.append(",".join(f'"{h}"' for h in header))
    for e in entries:
        row = [str(e.get(f, "")).replace('"', '""') for f in header]
        output.append(",".join(f'"{v}"' for v in row))
    return "\n".join(output) + "\n"

def export_json(entries=None):
    if entries is None:
        entries = load()
    return json.dumps(entries, ensure_ascii=False, indent=2)

def export_sqlite():
    entries = load()
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    cols = ", ".join(f'"{f}" TEXT' for f in FIELDS if f != "id")
    c.execute(f'CREATE TABLE glossary (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})')
    for e in entries:
        vals = [json.dumps(e.get("tags", [])) if f == "tags" else e.get(f, "") for f in FIELDS if f != "id"]
        placeholders = ", ".join("?" for _ in vals)
        c.execute(f'INSERT INTO glossary ({", ".join(f for f in FIELDS if f != "id")}) VALUES ({placeholders})', vals)
    conn.commit()
    conn.close()

# ---------- Public data for Hugo ----------

def generate_public():
    entries = load()
    public = []
    for e in entries:
        pub = {f: e.get(f, "") for f in PUBLIC_FIELDS}
        pub["tags"] = e.get("tags", [])
        public.append(pub)
    PUBLIC_JSON.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(public)

# ---------- Statistics ----------

def stats():
    entries = load()
    if not entries:
        return "No entries in glossary."
    lines = [f"Total entries: {len(entries)}"]
    by_cat = defaultdict(int)
    by_ctx = defaultdict(int)
    for e in entries:
        by_cat[e.get("category", "uncategorized")] += 1
        by_ctx[e.get("context", "unknown")] += 1
    lines.append(f"Categories: {dict(by_cat)}")
    lines.append(f"Contexts: {dict(by_ctx)}")
    top = sorted(entries, key=lambda x: -x.get("frequency", 1))[:5]
    lines.append("Top entries:")
    for e in top:
        lines.append(f"  {e.get('korean')} → {e.get('vietnamese')} (freq: {e.get('frequency')})")
    return "\n".join(lines)

# ---------- Import ----------

def import_file(path):
    path = Path(path)
    if not path.exists():
        return 0, f"File not found: {path}"
    ext = path.suffix.lower()
    count = 0
    if ext == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data:
            kr = item.get("korean", item.get("Korean", "")).strip()
            vn = item.get("vietnamese", item.get("Vietnamese", "")).strip()
            if kr and vn:
                add_entry(kr, vn, **{k.lower(): v for k, v in item.items() if k.lower() in FIELDS})
                count += 1
    elif ext == ".csv":
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kr = row.get("korean", row.get("Korean", "")).strip()
                vn = row.get("vietnamese", row.get("Vietnamese", "")).strip()
                if kr and vn:
                    add_entry(kr, vn, **row)
                    count += 1
    elif ext == ".md":
        text = path.read_text(encoding="utf-8")
        rows = re.findall(r"^\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", text, re.MULTILINE)
        for kr, vn in rows:
            kr = kr.strip()
            vn = vn.strip()
            if kr and vn and not kr.startswith("-") and kr.lower() not in ("korean", "---"):
                add_entry(kr, vn)
                count += 1
    return count, "ok"

# ---------- MM Integration ----------

def extract_from_article(source_json_path):
    """
    Parse mm's generated article JSON (or the article markdown frontmatter)
    and extract Korean→Vietnamese glossary entries.
    """
    path = Path(source_json_path)
    if not path.exists():
        return 0, f"not found: {path}"

    text = path.read_text(encoding="utf-8")
    # Try to parse as JSON first
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Treat as raw text
        data = {"text": text}

    content = data.get("text", data.get("content", text))
    if not content:
        content = text

    # Detect Hangul (Korean) content
    hangul = re.findall(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]+', content)
    if not hangul:
        return 0, "no Korean text found"

    # Extract unique Korean words/phrases
    korean_words = set(hangul)
    count = 0
    source_url = data.get("source", data.get("url", ""))

    for kw in sorted(korean_words, key=len, reverse=True)[:50]:
        kw = kw.strip()
        if len(kw) < 2:
            continue
        existing = find(load(), korean=kw)
        if existing:
            existing["frequency"] = existing.get("frequency", 1) + 1
            existing["last_seen"] = date.today().isoformat()
            count += 1
        else:
            add_entry(
                korean=kw,
                vietnamese=f"[{kw}]",
                source=source_url,
                category="auto",
                context="entertainment",
                tags=["auto-extracted"],
            )
            count += 1

    save(load())  # persist updates
    generate_public()
    return count, f"{count} entries {'updated' if count else 'extracted'}"

# ---------- CLI ----------

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "add":
        if len(args) < 3:
            print("Usage: glossary.py add <korean> <vietnamese> [--context ...]")
            return
        korean = args[1]
        vietnamese = args[2]
        kwargs = {}
        i = 3
        while i < len(args):
            if args[i].startswith("--") and i + 1 < len(args):
                kwargs[args[i][2:]] = args[i + 1]
                i += 2
            else:
                i += 1
        entry, action = add_entry(
            korean, vietnamese,
            context=kwargs.get("context", ""),
            category=kwargs.get("category", ""),
            source=kwargs.get("source", ""),
            meaning=kwargs.get("meaning", ""),
        )
        generate_public()
        print(f"{action}: #{entry['id']} {korean} → {vietnamese}")

    elif cmd == "search":
        query = " ".join(args[1:]) if len(args) > 1 else ""
        results = search_entries(query)
        print(f"Found {len(results)} results for '{query}':")
        for r in results[:20]:
            print(f"  #{r.get('id')} {r.get('korean')} → {r.get('vietnamese')} [{r.get('category')}]")

    elif cmd == "merge":
        total, dups = merge_duplicates()
        generate_public()
        print(f"Merged: {dups} duplicates removed, {total} entries remaining.")

    elif cmd == "validate":
        issues = validate()
        if issues:
            print(f"Found {len(issues)} issues:")
            for iss in issues:
                print(f"  ⚠️  {iss}")
        else:
            print("✅ All entries valid.")

    elif cmd == "export":
        fmt = "json"
        if "--format" in args:
            fmt = args[args.index("--format") + 1]
        if fmt == "json":
            JSON_PATH.write_text(export_json(), encoding="utf-8")
        elif fmt == "csv":
            CSV_PATH.write_text(export_csv(), encoding="utf-8")
        elif fmt == "md":
            MD_PATH.write_text(export_md(), encoding="utf-8")
        elif fmt == "sqlite":
            export_sqlite()
        else:
            print(f"Unknown format: {fmt}")
            return
        print(f"Exported to {fmt.upper()}.")

    elif cmd == "import":
        if len(args) < 2:
            print("Usage: glossary.py import <file>")
            return
        count, msg = import_file(args[1])
        generate_public()
        print(f"Imported {count} entries. {msg}")

    elif cmd == "list":
        entries = load()
        cat_filter = None
        tag_filter = None
        if "--category" in args:
            cat_filter = args[args.index("--category") + 1]
        if "--tag" in args:
            tag_filter = args[args.index("--tag") + 1]
        if cat_filter:
            entries = [e for e in entries if e.get("category") == cat_filter]
        if tag_filter:
            entries = [e for e in entries if tag_filter in e.get("tags", [])]
        for e in sorted(entries, key=lambda x: x.get("korean", "")):
            print(f"  #{e.get('id')} {e.get('korean')} → {e.get('vietnamese')} [{e.get('category')}]")

    elif cmd == "stats":
        print(stats())

    elif cmd == "extract":
        if len(args) < 2:
            print("Usage: glossary.py extract <file>")
            return
        count, msg = extract_from_article(args[1])
        print(f"Extracted {msg}.")

    elif cmd == "public":
        count = generate_public()
        print(f"Generated public.json with {count} entries.")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()
