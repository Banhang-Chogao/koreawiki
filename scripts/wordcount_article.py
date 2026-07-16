#!/usr/bin/env python3
"""Count Vietnamese body words in a Hugo markdown article (for mm/nn length bar).

Usage:
  python3 scripts/wordcount_article.py path/to/post.md
  python3 scripts/wordcount_article.py path/to/post.md --min 2000
  python3 scripts/wordcount_article.py --check-latest   # newest content file under content/en

Excludes YAML front matter and {{< article-footer >}} … block from the count.
Word = whitespace-separated token (works for Vietnamese with spaces).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SEP = "---"
FOOTER_RE = re.compile(
    r"\{\{<\s*article-footer\s*>\}\}[\s\S]*?\{\{<\s*/article-footer\s*>\}\}",
    re.I,
)


def extract_body(text: str) -> str:
    if not text.startswith(SEP):
        return text
    rest = text[len(SEP) :]
    if rest.startswith("\n"):
        rest = rest[1:]
    m = re.search(r"(?m)^---\s*$", rest)
    if not m:
        return text
    body = rest[m.end() :]
    if body.startswith("\n"):
        body = body[1:]
    body = FOOTER_RE.sub("", body)
    # strip image-only lines and pure markdown chrome lightly
    return body


def word_count(body: str) -> int:
    # remove markdown image syntax keep alt as words
    body = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    body = re.sub(r"[#>*`|_\\-]+", " ", body)
    tokens = [t for t in re.split(r"\s+", body.strip()) if t]
    return len(tokens)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="Markdown file")
    ap.add_argument("--min", type=int, default=0, help="Fail if below this word count")
    ap.add_argument(
        "--check-latest",
        action="store_true",
        help="Use newest *.md under content/en (excl. _index)",
    )
    args = ap.parse_args()

    if args.check_latest:
        root = Path("content/en")
        files = [p for p in root.rglob("*.md") if p.name != "_index.md"]
        if not files:
            print("error: no content files", file=sys.stderr)
            return 2
        path = max(files, key=lambda p: p.stat().st_mtime)
    elif args.path:
        path = Path(args.path)
    else:
        ap.print_help()
        return 2

    if not path.exists():
        print(f"error: not found {path}", file=sys.stderr)
        return 2

    body = extract_body(path.read_text(encoding="utf-8"))
    n = word_count(body)
    print(f"{path}: {n} words (body, excl. front matter + article-footer)")
    if args.min and n < args.min:
        print(f"FAIL: need ≥ {args.min} words (short by {args.min - n})", file=sys.stderr)
        return 1
    if args.min:
        print(f"OK: ≥ {args.min}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
