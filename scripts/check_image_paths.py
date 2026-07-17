#!/usr/bin/env python3
"""Check Hugo templates for image paths missing relURL filter.

Searches .html template files for src="{{ .Params.cover.image }}" or similar
patterns where image paths are used without | relURL or | absURL.
"""
import re, sys
from pathlib import Path

TEMPLATES_DIR = Path("themes/koreawiki/layouts")
IMG_PARAM_PATTERN = re.compile(
    r'\{\{\s*\.Params\.\w+\.(?:image|src|thumbnail|cover)\s*\}\}'
)
RELURL_PATTERN = re.compile(r'\|\s*(relURL|absURL)')

def check_file(fp):
    lines = fp.read_text("utf-8").splitlines()
    issues = []
    for i, line in enumerate(lines, 1):
        for m in IMG_PARAM_PATTERN.finditer(line):
            rest = line[m.end():]
            if not RELURL_PATTERN.search(rest):
                issues.append((i, m.group()))
    return issues

def main():
    files = list(TEMPLATES_DIR.rglob("*.html"))
    all_issues = []
    for fp in sorted(files):
        issues = check_file(fp)
        for lineno, match in issues:
            rel = fp.relative_to(TEMPLATES_DIR)
            all_issues.append(f"  {rel}:{lineno}  {match}  (missing | relURL)")
    if all_issues:
        print("ERROR: Image paths without relURL found:\n")
        for e in all_issues:
            print(e)
        sys.exit(1)
    print("OK: All image paths use relURL.")

if __name__ == "__main__":
    main()
