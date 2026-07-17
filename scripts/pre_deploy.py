#!/usr/bin/env python3
"""KoreaWiki Pre-Deploy Orchestrator — runs all checks before deployment.

Usage:
  python scripts/pre_deploy.py              # standard checks
  python scripts/pre_deploy.py --postbuild   # also run post-build checks
  python scripts/pre_deploy.py --learn       # run ML learning first, then checks
"""

import importlib, pkgutil, sys, subprocess, yaml, time
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
    ("Front Matter Check", [PYTHON, "scripts/frontmatter_check.py"]),
    ("Markdown Lint", [PYTHON, "scripts/markdown_lint.py", "--fix"]),
    ("Slug Check", [PYTHON, "scripts/slug.py", "--check"]),
    ("Link Check", [PYTHON, "scripts/check_links.py"]),
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
    do_learn = "--learn" in args or "-l" in args

    kb = load_knowledge_base()
    pattern_count = len(kb.get("patterns", {}))
    print(f"\nKoreaWiki Pre-Deploy Check\n")
    print(f"Knowledge base: {pattern_count} known patterns\n")

    all_issues = []
    failed = False

    # Phase 1: ML learning (optional)
    if do_learn:
        print("--- Phase 0: ML Learning ---")
        r = subprocess.run([PYTHON, "scripts/learn.py"], capture_output=True, text=True)
        print(r.stdout)
        if r.stderr.strip():
            print(r.stderr, file=sys.stderr)
        if r.returncode != 0:
            print("  [ML Learn] completed (new checks may have been generated)")

    # Phase 2: External scripts
    print("--- Phase 1: External Checks ---")
    ext_issues = run_external()
    all_issues.extend(ext_issues)
    if ext_issues:
        print(f"\n  → {len(ext_issues)} external check(s) failed\n")

    # Phase 3: Module checks (template patterns)
    print("--- Phase 2: Template Pattern Checks ---")
    mod_issues = run_module_checks()
    all_issues.extend(mod_issues)
    if mod_issues:
        print(f"\n  → {len(mod_issues)} template pattern issue(s) found\n")
    else:
        print("  (no template pattern issues)\n")

    # Phase 4: Learned checks
    learned_issues = run_learned_checks()
    all_issues.extend(learned_issues)
    if learned_issues:
        print(f"\n  → {len(learned_issues)} learned check issue(s) found\n")

    # Phase 5: Post-build checks
    if do_postbuild:
        print("--- Phase 3: Post-Build Checks ---")
        pb_issues = []
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

    # Report
    total = len(all_issues)
    if total:
        print(f"\n{'='*50}")
        print(f"RESULT: {total} issue(s) found — DEPLOY BLOCKED")
        print(f"{'='*50}\n")
        sys.exit(1)
    else:
        print(f"\n{'='*50}")
        print("RESULT: All checks passed — ready to deploy")
        print(f"{'='*50}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
