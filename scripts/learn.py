#!/usr/bin/env python3
"""KoreaWiki ML Learning Engine — analyzes git history, extracts fix patterns,
and auto-generates new pre-deploy checks.

Uses scikit-learn to:
  1. Parse git log for fix commits
  2. TF-IDF vectorize commit messages + diff content
  3. Cluster to identify common fix categories
  4. Generate new check scripts from discovered patterns

Usage:
  python scripts/learn.py                          # learn from all history
  python scripts/learn.py --since "2026-01-01"     # learn from specific date
"""

import re, sys, os, json, subprocess, textwrap
from pathlib import Path
from collections import Counter

LEARNED_DIR = Path("scripts/learned_checks")
TEMPLATES_DIR = Path("themes/koreawiki/layouts")

LEARNED_DIR.mkdir(exist_ok=True)

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("  [learn] scikit-learn not installed — using heuristic fallback", file=sys.stderr)


def get_fix_commits(since=None):
    cmd = ["git", "log", "--oneline", "--no-merges", "--diff-filter=M"]
    if since:
        cmd.extend(["--since", since])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [learn] git log failed: {result.stderr}", file=sys.stderr)
        return []

    commits = []
    for line in result.stdout.strip().splitlines():
        sha = line.split()[0]
        commits.append(sha)
    return commits


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


def heuristic_patterns(commits):
    """Fallback heuristic pattern detection when scikit-learn is unavailable."""
    patterns = Counter()
    file_ext_patterns = Counter()

    for sha in commits:
        details = get_commit_details(sha)
        msg_lower = details["message"].lower()

        # Categorize by commit message keywords
        if "relurl" in msg_lower or "relurl" in details["diff"].lower():
            patterns["missing_relurl"] += 1
        if "date" in msg_lower or "format" in msg_lower:
            patterns["date_format"] += 1
        if "slug" in msg_lower:
            patterns["slug_mismatch"] += 1
        if "link" in msg_lower or "broken" in msg_lower:
            patterns["broken_link"] += 1
        if "frontmatter" in msg_lower or "front matter" in msg_lower or "meta" in msg_lower:
            patterns["frontmatter"] += 1
        if "image" in msg_lower or "img" in msg_lower or "cover" in msg_lower:
            patterns["image_path"] += 1
        if "draft" in msg_lower or "publish" in msg_lower:
            patterns["publish_state"] += 1
        if "slug" in msg_lower:
            patterns["slug"] += 1

        # Track file extensions
        for f in details["files"]:
            ext = Path(f).suffix
            if ext:
                file_ext_patterns[ext] += 1

    return patterns, file_ext_patterns


def sklearn_patterns(commits):
    """ML-based pattern detection using TF-IDF + KMeans clustering."""
    if not HAS_SKLEARN or len(commits) < 3:
        return {}, {}

    docs = []
    commit_data = []

    for sha in commits:
        details = get_commit_details(sha)
        text = f"{details['message']}\n{details['diff'][:2000]}"
        docs.append(text)
        commit_data.append(details)

    try:
        vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words="english",
            ngram_range=(1, 3),
            min_df=1
        )
        X = vectorizer.fit_transform(docs)

        n_clusters = min(5, len(commits))
        if n_clusters < 2:
            return heuristic_patterns(commits)

        km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = km.fit_predict(X)

        cluster_patterns = {}
        for cluster_id in range(n_clusters):
            indices = [i for i, l in enumerate(labels) if l == cluster_id]
            if not indices:
                continue

            cluster_docs = [docs[i] for i in indices]
            cluster_vectorizer = TfidfVectorizer(
                max_features=50, stop_words="english"
            )
            try:
                CX = cluster_vectorizer.fit_transform(cluster_docs)
                sums = CX.sum(axis=0).A1
                top_idx = sums.argsort()[-5:][::-1]
                top_terms = [cluster_vectorizer.get_feature_names_out()[i] for i in top_idx if sums[i] > 0]
                if top_terms:
                    cluster_patterns[f"cluster_{cluster_id}"] = {
                        "terms": top_terms,
                        "count": len(indices),
                        "commits": [commit_data[i]["sha"] for i in indices[:3]]
                    }
            except Exception:
                continue

        return cluster_patterns, {}
    except Exception as e:
        print(f"  [learn] sklearn clustering failed: {e}", file=sys.stderr)
        return heuristic_patterns(commits)


def generate_check_from_pattern(pattern_name, pattern_data):
    """Generate a Python check script from a discovered pattern."""
    if isinstance(pattern_data, dict) and "terms" in pattern_data:
        terms = pattern_data["terms"]
        # Build regex from cluster terms
        safe_terms = [re.escape(t) for t in terms if len(t) > 2]
        if not safe_terms:
            return None
        pattern_regex = "|".join(safe_terms[:5])
        description = f"Auto-detected pattern: {', '.join(terms[:3])}"
    elif isinstance(pattern_data, int):
        # Simple count-based pattern
        pattern_regex = {
            "missing_relurl": r'\.Params\.\w+\.(?:image|src|thumbnail|cover)\s*\}\}',
            "date_format": r'\.Format\s+"(?:Jan|02\/01)',
            "slug_mismatch": r'urlize\)\}\}',
        }.get(pattern_name, "")
        description = {
            "missing_relurl": "Image path may need | relURL",
            "date_format": "Date format may not be human-readable VN format",
        }.get(pattern_name, f"Learned pattern: {pattern_name}")
        if not pattern_regex:
            return None
    else:
        return None

    code = textwrap.dedent(f'''\
    """Auto-generated check: {description}"""
    import re
    from pathlib import Path

    TEMPLATES = Path("themes/koreawiki/layouts")
    PATTERN = re.compile(r'{pattern_regex}')

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


def generate_learned_checks(patterns, file_patterns):
    """Generate check scripts from discovered patterns."""
    generated = 0

    if isinstance(patterns, Counter):
        # Heuristic mode results
        threshold = 1
        for pattern_name, count in patterns.items():
            if count < threshold:
                continue
            code = generate_check_from_pattern(pattern_name, count)
            if code:
                fname = f"check_learned_{pattern_name}.py"
                (LEARNED_DIR / fname).write_text(code)
                generated += 1
                print(f"  [learn] generated: {fname} (seen {count}x)")
    elif isinstance(patterns, dict):
        # sklearn mode results
        for cluster_name, data in patterns.items():
            if data.get("count", 0) < 2:
                continue
            code = generate_check_from_pattern(cluster_name, data)
            if code:
                fname = f"check_learned_{cluster_name}.py"
                (LEARNED_DIR / fname).write_text(code)
                generated += 1
                print(f"  [learn] generated: {fname} ({data['count']} commits, terms: {', '.join(data['terms'][:3])})")

    return generated


def main():
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

    if HAS_SKLEARN:
        print(f"  [learn] Using scikit-learn TF-IDF + KMeans clustering")
        patterns, file_patterns = sklearn_patterns(commits)
    else:
        print(f"  [learn] Using heuristic keyword matching (install scikit-learn for ML)")
        patterns, file_patterns = heuristic_patterns(commits)

    generated = generate_learned_checks(patterns, file_patterns)
    print(f"  [learn] Generated {generated} new check(s) in scripts/learned_checks/")

    # Summary stats
    file_exts = dict(file_patterns.most_common(10)) if isinstance(file_patterns, Counter) else {}
    if file_exts:
        print(f"  [learn] Top changed file types: {file_exts}")

    print(f"  [learn] Done.")


if __name__ == "__main__":
    main()
