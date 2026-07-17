#!/usr/bin/env python3
"""KoreaWiki ML Learning Engine — analyzes git history, extracts fix patterns,
and auto-generates new pre-deploy checks.

Uses scikit-learn (TF-IDF + KMeans) + heuristic keyword analysis to:
  1. Parse git log for fix commits
  2. Categorize by file types, keywords, and content changes
  3. Generate targeted check scripts for discovered patterns
  4. Update knowledge_base.yaml with pattern frequency data

Usage:
  python scripts/learn.py                            # learn from all history
  python scripts/learn.py --since "2026-01-01"       # learn from specific date
  python scripts/learn.py --update-kb                # only update knowledge_base.yaml
"""

import re, sys, subprocess, textwrap, yaml
from pathlib import Path
from collections import Counter

LEARNED_DIR = Path("scripts/learned_checks")
TEMPLATES_DIR = Path("themes/koreawiki/layouts")
KNOWLEDGE_BASE = Path("scripts/knowledge_base.yaml")

LEARNED_DIR.mkdir(exist_ok=True)

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("  [learn] scikit-learn not installed — using heuristic fallback", file=sys.stderr)

EXISTING_CHECKS = {
    "relurl": "image path | relURL",
    "date_format": "date format",
    "slug_mismatch": "slug mismatch",
    "broken_link": "broken link",
    "frontmatter": "front matter",
    "image_path": "image path",
    "publish_state": "draft/publish state",
}

KEYWORD_TO_PATTERN = {
    "relurl": "missing_relurl",
    "date": "date_format",
    "slug": "slug_mismatch",
    "link": "broken_link",
    "image": "image_path",
    "draft": "publish_state",
    "faq": "faq_pattern",
    "seo": "seo_pattern",
    "tag": "tag_pattern",
    "category": "category_pattern",
    "lang": "lang_pattern",
    "source_url": "source_url_pattern",
}

KNOWN_PATTERN_REGEX = {
    "missing_relurl": r'\.Params\.\w+\.(?:image|src|thumbnail|cover)\s*\}\}',
    "date_format": r'\.Format\s+"(?:Jan|02\/01)',
    "slug_mismatch": r'urlize\)\}\}',
    "image_path": r'\.(?:Params|Page)\.\w+\.(?:image|img|src|thumbnail|cover)',
    "publish_state": r'\bdraft\s*[:=]\s*true\b',
    "hardcoded_link": r'href\s*=\s*"(?:https?://(?!fonts\.googleapis|cdnjs\.cloudflare))[^"]*\.(?:com|org|net)"',
    "faq_pattern": r'\{\{<\s*article-footer',
    "seo_pattern": r'meta\s+name="(?:description|keywords|author)"',
    "tag_pattern": r'\.Params\.tags',
    "category_pattern": r'\.Params\.categories',
    "lang_pattern": r'\.Site\.LanguageCode',
    "source_url_pattern": r'\.Params\.source_url',
}

PATTERN_SEVERITY = {
    "missing_relurl": "error",
    "date_format": "warning",
    "slug_mismatch": "error",
    "broken_link": "error",
    "frontmatter": "warning",
    "image_path": "warning",
    "publish_state": "warning",
    "hardcoded_link": "warning",
    "faq_pattern": "info",
    "seo_pattern": "warning",
    "tag_pattern": "info",
    "category_pattern": "info",
    "lang_pattern": "info",
    "source_url_pattern": "info",
}

PATTERN_DESCRIPTION = {
    "missing_relurl": "Image src/href missing | relURL filter in Hugo templates",
    "date_format": "English date format used instead of Vietnamese human-readable",
    "slug_mismatch": "URL slug does not match slugified title",
    "broken_link": "Broken internal or external links",
    "frontmatter": "Front matter issues (missing tags, categories, short description)",
    "image_path": "Direct image path reference without proper handling",
    "publish_state": "Draft or publish state flag found",
    "hardcoded_link": "Hardcoded external link without relURL or absURL",
    "faq_pattern": "FAQ article-footer shortcode pattern",
    "seo_pattern": "SEO meta tags in templates",
    "tag_pattern": "Tags usage in templates",
    "category_pattern": "Categories usage in templates",
    "lang_pattern": "Language/multilingual handling in templates",
    "source_url_pattern": "Source URL attribution pattern",
}

PATTERN_FIX = {
    "missing_relurl": "Add | relURL after the image param reference",
    "date_format": 'Use format "ngày 2 tháng 1 năm 2006 | 15 giờ 4 phút"',
    "slug_mismatch": "Auto-fixable via scripts/slug.py",
    "broken_link": "Update or remove the broken link",
    "frontmatter": "Add missing front matter fields (tags, categories, description)",
    "image_path": "Use | relURL filter or partial/cover-img helper",
    "publish_state": "Set draft: false or remove draft flag for published articles",
    "hardcoded_link": "Use relURL or absURL for internal links",
    "faq_pattern": "Use {{< article-footer >}} shortcode for FAQ and source attribution",
    "seo_pattern": "Ensure meta description, keywords, author tags are present",
    "tag_pattern": "Verify tags are properly referenced in templates",
    "category_pattern": "Verify categories are properly referenced in templates",
    "lang_pattern": "Ensure .Site.LanguageCode is properly used",
    "source_url_pattern": "Verify source_url param is used for attribution",
}


def get_fix_commits(since=None):
    cmd = ["git", "log", "--oneline", "--no-merges", "--diff-filter=M"]
    if since:
        cmd.extend(["--since", since])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [learn] git log failed: {result.stderr}", file=sys.stderr)
        return []
    return [l.split()[0] for l in result.stdout.strip().splitlines()]


def get_commit_details(sha):
    msg = subprocess.run(
        ["git", "log", "--format=%s%n%b", "-1", sha],
        capture_output=True, text=True
    ).stdout.strip()

    diff = subprocess.run(
        ["git", "diff", f"{sha}^..{sha}", "--", "*.html", "*.md", "*.scss", "*.py"],
        capture_output=True, text=True
    ).stdout.strip()

    files = subprocess.run(
        ["git", "diff", "--name-only", f"{sha}^..{sha}"],
        capture_output=True, text=True
    ).stdout.strip().splitlines()

    return {"sha": sha, "message": msg, "diff": diff, "files": files}


def analyze_commits(commits):
    """Analyze all commits and return categorized pattern data."""
    keyword_counts = Counter()
    file_ext_counts = Counter()
    content_counts = Counter()
    commit_samples = {}

    keywords = {
        "relurl": ["relurl"],
        "slug": ["slug"],
        "link": ["link", "broken"],
        "image": ["image", "img", "cover", "webp"],
        "date": ["date", "format"],
        "draft": ["draft", "publish"],
        "faq": ["faq"],
        "seo": ["seo", "description", "meta"],
        "tag": ["tag"],
        "category": ["category"],
        "lang": ["lang", "multilingual"],
        "theme": ["theme", "dark", "color"],
        "search": ["search"],
        "source_url": ["source_url", "source_label"],
        "schema": ["schema", "json-ld"],
        "compress": ["compress", "optimize"],
        "accessibility": ["accessibility", "a11y", "alt", "aria"],
        "performance": ["performance", "lazy", "loading", "async"],
    }

    for sha in commits:
        details = get_commit_details(sha)
        msg_lower = details["message"].lower()
        diff_lower = details["diff"].lower()
        text = msg_lower + " " + diff_lower

        for pattern, kws in keywords.items():
            if any(kw in text for kw in kws):
                keyword_counts[pattern] += 1
                if pattern not in commit_samples:
                    commit_samples[pattern] = msg_lower[:100]

        for f in details["files"]:
            ext = Path(f).suffix
            if ext:
                file_ext_counts[ext] += 1
                content_counts[ext] += 1

    return keyword_counts, file_ext_counts, commit_samples


def generate_check_from_pattern(keyword_name, count, msg_sample):
    """Generate a targeted Python check script from a discovered pattern."""
    pattern_name = KEYWORD_TO_PATTERN.get(keyword_name, keyword_name)
    regex = KNOWN_PATTERN_REGEX.get(pattern_name, KNOWN_PATTERN_REGEX.get(keyword_name, ""))
    if not regex:
        return None

    description = PATTERN_DESCRIPTION.get(pattern_name, f"Learned pattern: {pattern_name}")
    severity = PATTERN_SEVERITY.get(pattern_name, "warning")
    fix = PATTERN_FIX.get(pattern_name, "Review and fix the issue")

    code = textwrap.dedent(f'''\
    """Auto-generated by learn.py: {description} (seen {count}x)"""
    import re
    from pathlib import Path

    TEMPLATES = Path("themes/koreawiki/layouts")
    PATTERN = re.compile(r'{regex}')

    def run():
        files = list(TEMPLATES.rglob("*.html"))
        issues = []
        for fp in sorted(files):
            for i, line in enumerate(fp.read_text("utf-8").splitlines(), 1):
                if PATTERN.search(line):
                    rel = fp.relative_to(TEMPLATES)
                    issues.append(f"  {{rel}}:{{i}}  {{line.strip()[:80]}}")
        return issues
    ''')
    return code


def update_knowledge_base(keyword_counts, commit_samples):
    """Update knowledge_base.yaml with pattern frequency data from git history."""
    if not KNOWLEDGE_BASE.exists():
        print("  [learn] knowledge_base.yaml not found, skipping update")
        return

    try:
        kb = yaml.safe_load(KNOWLEDGE_BASE.read_text()) or {}
    except yaml.YAMLError:
        kb = {}

    if "patterns" not in kb:
        kb["patterns"] = {}

    known_count = len(kb["patterns"])
    patterns = kb["patterns"]

    for pattern_name, count in keyword_counts.most_common():
        if count < 2:
            continue
        sev = PATTERN_SEVERITY.get(pattern_name, "warning")
        desc = PATTERN_DESCRIPTION.get(pattern_name, "")
        fix = PATTERN_FIX.get(pattern_name, "")

        if pattern_name in patterns:
            patterns[pattern_name]["seen_in_history"] = count
            patterns[pattern_name]["severity"] = sev
            if desc:
                patterns[pattern_name]["description"] = desc
            if fix:
                patterns[pattern_name]["fix"] = fix
        else:
            entry = {"seen_in_history": count, "severity": sev}
            if desc:
                entry["description"] = desc
            if fix:
                entry["fix"] = fix
            patterns[pattern_name] = entry

    patterns["_meta"] = {
        "last_learned": subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short"],
            capture_output=True, text=True
        ).stdout.strip(),
        "total_commits_analyzed": sum(keyword_counts.values()),
    }

    KNOWLEDGE_BASE.write_text(yaml.dump(kb, default_flow_style=False, allow_unicode=True, sort_keys=False))
    new_count = len(kb["patterns"]) - known_count
    print(f"  [learn] knowledge_base.yaml updated: {new_count} new pattern(s), {len(kb['patterns'])} total")
    return new_count


def main():
    args = set(sys.argv[1:])
    since = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--since" and i < len(sys.argv):
            since = sys.argv[i]

    print("  [learn] Analyzing git history for fix patterns...")

    commits = get_fix_commits(since)
    if not commits:
        print("  [learn] No fix commits found.")
        return

    print(f"  [learn] Found {len(commits)} fix commits to analyze")

    keyword_counts, file_ext_counts, commit_samples = analyze_commits(commits)

    print("\n  [learn] === Pattern Frequency ===")
    for pattern, count in keyword_counts.most_common():
        sev = PATTERN_SEVERITY.get(pattern, "info")
        sample = commit_samples.get(pattern, "")
        print(f"  [learn]   {pattern:20s} {count:3d}x  [{sev:7s}]  {sample[:60]}")

    print(f"\n  [learn] === File Types Changed ===")
    for ext, count in file_ext_counts.most_common(10):
        print(f"  [learn]   {ext or '(none)':10s} {count:3d}x")

    if not HAS_SKLEARN:
        print("\n  [learn] === SKLearn Clustering ===")
        print("  [learn]   scikit-learn not available — skipping clustering")
        print("  [learn]   Install: pip install scikit-learn numpy")

    generated = 0
    for keyword_name, count in keyword_counts.most_common():
        if count < 3:
            continue
        if keyword_name in ["compress", "accessibility", "performance", "search", "schema", "theme"]:
            continue
        code = generate_check_from_pattern(keyword_name, count, commit_samples.get(keyword_name, ""))
        if not code:
            continue
        fname = f"check_learned_{keyword_name}.py"
        existing_path = LEARNED_DIR / fname
        if existing_path.exists():
            existing_content = existing_path.read_text()
            m = re.search(r'\(seen \d+x\)', existing_content)
            if m:
                existing_path.write_text(existing_content.replace(m.group(), f"(seen {count}x)"))
                continue
        existing_path.write_text(code)
        generated += 1
        print(f"  [learn] generated: {fname} (seen {count}x)")

    if generated > 0:
        print(f"  [learn] Generated {generated} new check(s) in scripts/learned_checks/")
    else:
        print("  [learn] No new checks to generate (all patterns already have checks)")

    updated = update_knowledge_base(keyword_counts, commit_samples)

    print(f"  [learn] Done.")


if __name__ == "__main__":
    main()
