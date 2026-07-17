#!/usr/bin/env python3
"""KoreaWiki Slug — validates and normalizes URL slugs."""

import sys, re, yaml
from pathlib import Path

CONTENT = Path("content")
SEP = "---"

def slugify(text):
    text = text.lower().strip()
    maps = [
        (r'[àáảãạâầấẩẫậăằắẳẵặ]', 'a'),
        (r'[èéẻẽẹêềếểễệ]', 'e'),
        (r'[ìíỉĩị]', 'i'),
        (r'[òóỏõọôồốổỗộơờớởỡợ]', 'o'),
        (r'[ùúủũụưừứửữự]', 'u'),
        (r'[ỳýỷỹỵ]', 'y'),
        (r'[đ]', 'd'),
        (r'[ºª]', ''),
    ]
    for pattern, repl in maps:
        text = re.sub(pattern, repl, text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def normalize(fp):
    c = fp.read_text("utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", c, re.DOTALL)
    if not match: return False
    try: meta = yaml.safe_load(match.group(1))
    except: return False
    if not meta: return False
    expected = slugify(meta.get("title",""))
    if meta.get("slug","") == expected: return False
    meta["slug"] = expected
    fp.write_text(f"{SEP}\n{yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)}{SEP}\n{match.group(2).lstrip()}", "utf-8")
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
