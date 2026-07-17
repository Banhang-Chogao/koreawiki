#!/usr/bin/env python3
"""Post-build QA: validate generated HTML for broken relative paths.

Checks that all src/href attributes pointing to site assets use
absolute paths (starting with /koreawiki/) instead of relative paths
that would break on subdirectory pages.
"""
import re, sys
from pathlib import Path

PUBLIC = Path("public")
BASE_PATH = "/koreawiki/"

SRC_PATTERN = re.compile(
    r'(src|href)\s*=\s*"(?!https?://|/|#|data:|mailto:)([^"]+)"'
)

def check_file(fp):
    content = fp.read_text("utf-8", errors="replace")
    issues = []
    for m in SRC_PATTERN.finditer(content):
        attr, val = m.group(1), m.group(2)
        if val and not val.startswith(("%7B%7B", "{{")):
            issues.append((m.start(), attr, val))
    return issues

def main():
    if not PUBLIC.is_dir():
        print("SKIP: public/ not found. Run 'hugo' first.")
        sys.exit(0)

    html_files = list(PUBLIC.rglob("*.html"))
    all_issues = []
    for fp in sorted(html_files):
        issues = check_file(fp)
        for offset, attr, val in issues:
            rel = fp.relative_to(PUBLIC)
            all_issues.append(f"  {rel}  {attr}=\"{val}\"")

    if all_issues:
        print(f"ERROR: {len(all_issues)} relative path(s) found:\n")
        for e in all_issues:
            print(e)
        print(f"\nFix: add | relURL filter in Hugo templates for these paths.")
        sys.exit(1)

    print(f"OK: {len(html_files)} files checked — no relative asset paths.")
    sys.exit(0)

if __name__ == "__main__":
    main()
