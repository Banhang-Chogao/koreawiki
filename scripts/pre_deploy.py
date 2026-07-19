#!/usr/bin/env python3
"""KoreaWiki Pre-Deploy Orchestrator — runs all checks before deployment.

Usage:
  python scripts/pre_deploy.py              # standard checks
  python scripts/pre_deploy.py --postbuild   # also run post-build checks
   python scripts/pre_deploy.py               # ML learning always runs first
"""

import importlib, pkgutil, sys, subprocess, yaml, time, re
from pathlib import Path

SCRIPTS = Path("scripts")
CHECKS_DIR = SCRIPTS / "checks"
LEARNED_DIR = SCRIPTS / "learned_checks"
KNOWLEDGE_BASE = SCRIPTS / "knowledge_base.yaml"
sys.path.insert(0, str(SCRIPTS))

PYTHON = "python3" if sys.platform == "darwin" else "python"

EXTERNAL_CHECKS = [
    ("Front Matter", [PYTHON, "scripts/qa.py"]),
    ("SEO", [PYTHON, "scripts/seo.py"]),
    ("SEO Audit", [PYTHON, "scripts/seo_audit.py"]),
    ("Front Matter Check", [PYTHON, "scripts/frontmatter_check.py"]),
    ("Markdown Lint", [PYTHON, "scripts/markdown_lint.py"]),
    ("Slug Check", [PYTHON, "scripts/slug.py", "--check"]),
    ("Link Check", [PYTHON, "scripts/check_links.py"]),
    ("Article Footer", [PYTHON, "scripts/check_article_footer.py"]),
    ("News Sitemap", [PYTHON, "scripts/check_news_sitemap.py"]),
    ("Image Rights", [PYTHON, "scripts/check_image_rights.py"]),
    ("Calendar", [PYTHON, "scripts/check_calendar.py"]),
]

def load_knowledge_base():
    try:
        return yaml.safe_load(KNOWLEDGE_BASE.read_text()) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}

def run_module_checks():
    issues = []
    for importer, modname, ispkg in pkgutil.iter_modules([str(CHECKS_DIR)]):
        mod = importlib.import_module(f"checks.{modname}")
        if hasattr(mod, "run"):
            try:
                result = mod.run()
                if result:
                    issues.extend(result)
                    for line in result:
                        print(f"  [{modname}] {line}")
            except Exception as e:
                issues.append(f"[{modname}] ERROR: {e}")
                print(f"  [{modname}] ERROR: {e}", file=sys.stderr)
    return issues

def run_learned_checks():
    if not LEARNED_DIR.is_dir():
        return []
    issues = []
    sys.path.insert(0, str(SCRIPTS))
    for fp in sorted(LEARNED_DIR.glob("check_*.py")):
        modname = f"learned_checks.{fp.stem}"
        try:
            mod = importlib.import_module(modname)
            if hasattr(mod, "run"):
                result = mod.run()
                if result:
                    issues.extend(result)
                    for line in result:
                        print(f"  [learned:{fp.stem}] {line}")
        except Exception as e:
            issues.append(f"[learned:{fp.stem}] ERROR: {e}")
            print(f"  [learned:{fp.stem}] ERROR: {e}", file=sys.stderr)
    return issues

def run_external():
    issues = []
    for label, cmd in EXTERNAL_CHECKS:
        start = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - start
        if r.returncode != 0:
            issues.append(f"[{label}] FAILED (rc={r.returncode}, {elapsed:.1f}s)")
            print(f"  [{label}] FAILED:")
            if r.stdout.strip():
                for line in r.stdout.strip().splitlines():
                    print(f"    {line}")
            if r.stderr.strip():
                for line in r.stderr.strip().splitlines():
                    print(f"    {line}", file=sys.stderr)
        else:
            print(f"  [{label}] passed ({elapsed:.1f}s)")
    return issues

def main():
    args = set(sys.argv[1:])
    do_postbuild = "--postbuild" in args or "-p" in args

    print(f"\n{'='*55}")
    print(f"  KOREAWIKI PRE-DEPLOY ORCHESTRATOR")
    print(f"{'='*55}\n")

    # ──────────────────────────────────────────────────
    # PHASE 0: MACHINE LEARNING — always run
    # ──────────────────────────────────────────────────
    print("─── Phase 0: [ML Learning Engine] ───────────────────────")
    print("     Analyzing git history for fix patterns...\n")
    r = subprocess.run([PYTHON, "scripts/learn.py"], capture_output=True, text=True)

    # Parse learn.py output for a clean summary
    learn_lines = r.stdout.strip().splitlines()
    pattern_count = 0
    generated_count = 0
    analyzed_count = 0
    kb_updated = False

    for line in learn_lines:
        print(f"  {line}")
        if "knowledge_base" in line and "updated" in line:
            kb_updated = True
            m = re.search(r'(\d+) total', line)
            if m: pattern_count = int(m.group(1))
        if "Found" in line and "fix commits" in line:
            m = re.search(r'Found (\d+)', line)
            if m: analyzed_count = int(m.group(1))
        if "generated" in line and ".py" in line:
            generated_count += 1
        if "No new checks" in line:
            pass

    if r.returncode != 0:
        print(f"\n  ⚠  [ML Learn] completed with warnings — continuing anyway\n")

    print(f"\n  ✓ Hệ thống máy học đã học: {analyzed_count} commit phân tích,"
          f" {pattern_count} patterns trong knowledge_base,"
          f" {generated_count} check mới tạo/hôm nay")
    print(f"  ────────────────────────────────────────────────────────\n")

    kb = load_knowledge_base()
    all_issues = []
    failed = False

    # Phase 1: External scripts
    print("─── Phase 1: External Checks ────────────────────────────")
    ext_issues = run_external()
    all_issues.extend(ext_issues)
    if ext_issues:
        print(f"\n  → {len(ext_issues)} external check(s) failed\n")

    # Phase 2: Module checks (template patterns)
    print("─── Phase 2: Template Pattern Checks ────────────────────")
    mod_issues = run_module_checks()
    all_issues.extend(mod_issues)
    if mod_issues:
        print(f"\n  → {len(mod_issues)} template pattern issue(s) found\n")
    else:
        print("  (no template pattern issues)\n")

    # Phase 3: Learned checks (advisory only — do NOT block deploy)
    print("─── Phase 3: Learned Checks (ML-generated) ──────────────")
    learned_issues = run_learned_checks()
    if learned_issues:
        print(f"\n  → {len(learned_issues)} learned check issue(s) found (advisory)")
    else:
        print("  (no learned check issues)\n")

    # Phase 4: Post-build checks
    if do_postbuild:
        print("─── Phase 4: Post-Build Checks ─────────────────────────")
        pb_issues = []
        footer_result = subprocess.run(
            [PYTHON, "scripts/check_article_footer.py", "--postbuild"],
            capture_output=True, text=True,
        )
        if footer_result.returncode != 0:
            pb_issues.append("[Article Footer] FAILED")
            if footer_result.stdout.strip():
                for line in footer_result.stdout.strip().splitlines():
                    print(f"  {line}")
            if footer_result.stderr.strip():
                print(footer_result.stderr, file=sys.stderr)
        else:
            print("  [Article Footer] passed")
        for label, cmd in (
            ("News Sitemap", [PYTHON, "scripts/check_news_sitemap.py", "--postbuild"]),
            ("Schema", [PYTHON, "scripts/generate_schema.py"]),
        ):
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode:
                pb_issues.append(f"[{label}] FAILED")
                if result.stdout.strip():
                    for line in result.stdout.strip().splitlines():
                        print(f"  {line}")
            else:
                print(f"  [{label}] passed")
        try:
            mod = importlib.import_module("checks._check_relative_asset")
            result = mod.run()
            if result:
                pb_issues.extend(result)
                for line in result:
                    print(f"  {line}")
        except Exception as e:
            pb_issues.append(str(e))
            print(f"  ERROR: {e}", file=sys.stderr)
        all_issues.extend(pb_issues)
        if pb_issues:
            print(f"\n  → {len(pb_issues)} post-build issue(s) found\n")
        else:
            print("  (no post-build issues)\n")

    # Report — only hard checks block deploy
    hard_total = len(all_issues)
    print(f"\n{'='*55}")
    if hard_total:
        print(f"  ✖ DEPLOY BLOCKED: {hard_total} hard issue(s) found")
        print(f"{'='*55}\n")
        sys.exit(1)
    else:
        print(f"  ✔ ML LEARNED: {analyzed_count} commits, {pattern_count} patterns, {generated_count} new checks")
        if learned_issues:
            print(f"  ✔ ADVISORY: {len(learned_issues)} warning(s) — non-blocking")
        print(f"  ✔ READY TO DEPLOY")
        print(f"{'='*55}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
