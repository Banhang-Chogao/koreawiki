#!/usr/bin/env python3
"""KoreaWiki Markdown Lint — checks and auto-fixes markdown formatting rules."""

import sys, re, textwrap
from pathlib import Path

CONTENT = Path("content")
WARNINGS = [
    (r'\b(?:Click here|Read more|Learn more|Click this)\b', "Vague link text"),
    (r'https?://(?:www\.)?(?:bit\.ly|tinyurl|goo\.gl)', "URL shortener used"),
    (r' {2,}\n', "Trailing whitespace"),
]
MAX_LINE = 200

def wrap_long_lines(text):
    """Wrap lines >MAX_LINE chars, skipping front matter YAML and tables."""
    lines = text.split("\n")
    in_fm = False
    new = []
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            in_fm = not in_fm
            new.append(line)
            continue
        if in_fm or stripped.startswith("|"):
            new.append(line)
            continue
        if len(line) > MAX_LINE:
            indent = len(line) - len(line.lstrip())
            prefix = " " * indent
            wrapped = textwrap.fill(line, width=MAX_LINE, subsequent_indent=prefix)
            new.append(wrapped)
        else:
            new.append(line)
    return "\n".join(new)

def main():
    fix = "--fix" in sys.argv
    issues = []
    fixed_files = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md": continue
        text = fp.read_text("utf-8")
        rel = fp.relative_to(CONTENT)
        for pat, msg in WARNINGS:
            if re.search(pat, text): issues.append((rel, msg))
        lines = text.split("\n")
        has_long = False
        for i, line in enumerate(lines, 1):
            if len(line) > MAX_LINE and not line.startswith("|"):
                issues.append((rel, f"Line {i} >{MAX_LINE} chars"))
                has_long = True
        if fix and has_long:
            new_text = wrap_long_lines(text)
            if new_text != text:
                fp.write_text(new_text, "utf-8")
                fixed_files.append(rel)
    if fix and fixed_files:
        print(f"Auto-wrapped {len(fixed_files)} files:")
        for f in fixed_files: print(f"  - {f}")
    if issues and not fix:
        print(f"Found {len(issues)} markdown issues:\n"); [print(f"  {r}: {m}") for r,m in issues]
        sys.exit(1)
    if not fix:
        print("Markdown lint passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
