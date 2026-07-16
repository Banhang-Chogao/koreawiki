#!/usr/bin/env python3
"""KoreaWiki Markdown Lint — checks basic markdown formatting rules."""

import sys, re
from pathlib import Path

CONTENT = Path("content")
WARNINGS = [
    (r'\b(?:Click here|Read more|Learn more|Click this)\b', "Vague link text"),
    (r'https?://(?:www\.)?(?:bit\.ly|tinyurl|goo\.gl)', "URL shortener used"),
    (r' {2,}\n', "Trailing whitespace"),
]

def main():
    issues = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md": continue
        text = fp.read_text("utf-8")
        rel = fp.relative_to(CONTENT)
        for pat, msg in WARNINGS:
            if re.search(pat, text): issues.append((rel, msg))
        lines = text.split("\n")
        for i, line in enumerate(lines, 1):
            if len(line) > 200 and not line.startswith("|"): issues.append((rel, f"Line {i} >200 chars"))
    if issues:
        print(f"Found {len(issues)} markdown issues:\n"); [print(f"  {r}: {m}") for r,m in issues]
        sys.exit(1)
    print("Markdown lint passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
