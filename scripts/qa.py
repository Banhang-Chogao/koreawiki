#!/usr/bin/env python3
"""KoreaWiki QA — validates front matter, markdown, and required article features.

Every article (any authoring path: mm, manual, AI, import) MUST include:
  - front matter `faq:` (list of {q,a}) → powers "Bài này trả lời" + FAQ anchors
  - shortcode `{{< article-footer >}}` … → source, links, copyright, FAQ UI

Auto-fix: python3 scripts/apply_article_footer.py --apply
"""

import sys, yaml, re
from pathlib import Path
from datetime import datetime

CONTENT = Path("content")
SEP = "---"
DATE_TYPES = (datetime, type(datetime.now().date()))
REQUIRED = {"title": str, "description": str, "date": DATE_TYPES, "draft": bool}
FOOTER_RE = re.compile(
    r"\{\{<\s*article-footer\s*>\}\}[\s\S]*?\{\{<\s*/article-footer\s*>\}\}",
    re.I,
)

def extract(content):
    """Parse YAML front matter only (first --- … --- block).

    Do NOT split the whole file on '---' — Markdown tables use |---|---| and
    would truncate body (footer false-negative).
    """
    if not content.startswith(SEP):
        return None, ""
    rest = content[len(SEP) :]
    if rest.startswith("\n"):
        rest = rest[1:]
    # Closing fence must be on its own line
    m = re.search(r"(?m)^---\s*$", rest)
    if not m:
        return None, ""
    fm = rest[: m.start()]
    body = rest[m.end() :]
    if body.startswith("\n"):
        body = body[1:]
    try:
        return yaml.safe_load(fm), body
    except yaml.YAMLError:
        return None, ""

def check_faq(meta):
    errors = []
    faq = meta.get("faq")
    if faq is None:
        errors.append(
            "Missing front matter 'faq:' (required for 'Bài này trả lời' + FAQ anchors). "
            "Run: python3 scripts/apply_article_footer.py --apply"
        )
        return errors
    if not isinstance(faq, list) or len(faq) < 2:
        errors.append("'faq:' must be a list with at least 2 items ({q, a})")
        return errors
    for i, item in enumerate(faq):
        if not isinstance(item, dict):
            errors.append(f"faq[{i}] must be a mapping with q/a")
            continue
        q = item.get("q") or item.get("question") or ""
        a = item.get("a") or item.get("answer") or ""
        if not str(q).strip():
            errors.append(f"faq[{i}] missing question (q)")
        if not str(a).strip():
            errors.append(f"faq[{i}] missing answer (a)")
    return errors

def check_article_footer(body):
    if not FOOTER_RE.search(body or ""):
        return [
            "Missing {{< article-footer >}} … {{< /article-footer >}} shortcode. "
            "Run: python3 scripts/apply_article_footer.py --apply"
        ]
    return []

def check(meta, body=""):
    errors = []
    for f, t in REQUIRED.items():
        if f not in meta: errors.append(f"Missing: '{f}'")
        elif not isinstance(meta[f], t) and meta[f] is not None: errors.append(f"'{f}' wrong type")
    if meta.get("date") and meta.get("lastmod") and meta["lastmod"] < meta["date"]:
        errors.append("lastmod before date")
    if not meta.get("title") or len(str(meta.get("title",""))) > 120:
        errors.append("Title missing or >120 chars")
    desc = meta.get("description","")
    if len(desc) < 50: errors.append("Description <50 chars")
    elif len(desc) > 320: errors.append("Description >320 chars")
    if not meta.get("tags"): errors.append("Missing tags")
    if not meta.get("categories"): errors.append("Missing categories")
    errors.extend(check_faq(meta))
    errors.extend(check_article_footer(body))
    return errors

def main():
    files = list(CONTENT.rglob("*.md"))
    issues = []
    for fp in files:
        if fp.name == "_index.md": continue
        meta, body = extract(fp.read_text("utf-8"))
        if meta:
            errs = check(meta, body)
            if errs: issues.append((fp.relative_to(CONTENT), errs))
        else:
            issues.append((fp.relative_to(CONTENT), ["No valid front matter"]))
    if issues:
        print(f"{len(issues)} files with issues:\n")
        for rel, errs in issues:
            print(f"  {rel}:"); [print(f"    - {e}") for e in errs]
        print(
            "\nTip: python3 scripts/apply_article_footer.py --apply"
        )
        sys.exit(1)
    print("QA passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
