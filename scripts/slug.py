#!/usr/bin/env python3
"""KoreaWiki Slug — validates and normalizes URL slugs."""

import sys, re, yaml, unicodedata
from pathlib import Path

CONTENT = Path("content")
SEP = "---"

VIET_MAP = str.maketrans({
    'đ': 'd', 'Đ': 'd',
})

def slugify(text):
    text = text.lower().strip()
    text = text.translate(VIET_MAP)
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'-+', '-', re.sub(r'[\s_]+', '-', text)).strip('-')

def normalize(fp):
    c = fp.read_text("utf-8")
    parts = c.split(SEP)
    if len(parts) < 3: return False
    try: meta = yaml.safe_load(parts[1])
    except: return False
    if not meta: return False
    expected = slugify(meta.get("title",""))
    if meta.get("slug","") == expected: return False
    meta["slug"] = expected
    fp.write_text(
        f"{SEP}\n{yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)}{SEP}\n{parts[2].lstrip()}",
        "utf-8",
    )
    return True

def main():
    check = "--check" in sys.argv
    changed = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md": continue
        if normalize(fp): changed.append(fp.relative_to(CONTENT))
    if changed:
        if check:
            print(f"Slugs need updating for {len(changed)} files:"); [print(f"  - {c}") for c in changed]
            sys.exit(1)
        else:
            print(f"Normalized {len(changed)} slugs:"); [print(f"  - {c}") for c in changed]
    else: print("All slugs valid.")
    sys.exit(0)

if __name__ == "__main__":
    main()
