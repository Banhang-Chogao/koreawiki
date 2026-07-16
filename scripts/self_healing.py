#!/usr/bin/env python3
"""KoreaWiki Self-Healing — detect CI failures, apply scientist.md fixes, re-validate.

Usage:
  python3 scripts/self_healing.py analyze --log path/to/log.txt
  python3 scripts/self_healing.py fix [--log path]
  python3 scripts/self_healing.py validate
  python3 scripts/self_healing.py recover --log path [--round N]
  python3 scripts/self_healing.py report --status failed|success

Exit codes:
  0  recovered / validations green
  1  partial — report written, manual intervention needed
  2  hard fail / max rounds exceeded
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports" / "self-healing"
SCIENTIST = ROOT / "scientist.md"
CONTENT = ROOT / "content"
MAX_ROUNDS = 5
NOREPLY_EMAIL = "292648126+Banhang-Chogao@users.noreply.github.com"

# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

CATEGORY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("hugo", re.compile(r"hugo|Error: error building site|parse failed|template:|function \".+\" not defined", re.I)),
    ("markdown", re.compile(r"markdown|Trailing whitespace|Line \d+ >200|Vague link", re.I)),
    ("python_qa", re.compile(r"scripts/qa\.py|Missing: 'draft'|No valid front matter|QA passed", re.I)),
    ("seo", re.compile(r"scripts/seo\.py|Missing keywords|Invalid slug|Description <|Title >", re.I)),
    ("frontmatter", re.compile(r"frontmatter|front matter|yaml|YAML", re.I)),
    ("links", re.compile(r"check_links|broken link|internal link", re.I)),
    ("images", re.compile(r"optimize_images|image|missing image|cover\.image", re.I)),
    ("slug", re.compile(r"slug\.py|Slugs need updating|Invalid slug", re.I)),
    ("schema", re.compile(r"generate_schema|schema\.org|JSON-LD", re.I)),
    ("workflow", re.compile(r"deploy-pages|upload-pages-artifact|actions/|Process completed with exit code", re.I)),
    ("dependency", re.compile(r"npm|pip|ModuleNotFound|package\.json|node_modules", re.I)),
    ("config", re.compile(r"hugo\.toml|config/|dataDir|paginate", re.I)),
    ("glossary", re.compile(r"glossary|translation memory|glossary\.json", re.I)),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run(cmd: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def ensure_reports_dir(run_id: str = "") -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"{stamp}" + (f"-{run_id}" if run_id else "")
    path = REPORTS / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_log(path: Path | None) -> str:
    if path and path.exists():
        return path.read_text("utf-8", errors="replace")
    # Fallback: last report log
    env_log = os.environ.get("SELF_HEAL_LOG", "")
    if env_log and Path(env_log).exists():
        return Path(env_log).read_text("utf-8", errors="replace")
    return ""


def categorize(log: str) -> list[str]:
    cats: list[str] = []
    for name, pat in CATEGORY_PATTERNS:
        if pat.search(log):
            cats.append(name)
    return cats or ["unknown"]


def extract_root_causes(log: str) -> list[str]:
    """Pull high-signal error lines from CI logs."""
    causes: list[str] = []
    patterns = [
        r"Error: .+",
        r"ERROR .+",
        r"##\[error\].+",
        r"function \"[^\"]+\" not defined",
        r"Missing: '[^']+'",
        r"Missing keywords",
        r"No valid front matter",
        r"Slugs need updating.+",
        r"Found \d+ markdown issues",
        r"SEO issues in \d+ files",
        r"Process completed with exit code \d+",
        r"parse failed:.+",
        r"failed to load data:.+",
    ]
    for line in log.splitlines():
        s = line.strip()
        if not s:
            continue
        for pat in patterns:
            if re.search(pat, s, re.I):
                # strip GHA timestamps / group prefixes
                clean = re.sub(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*", "", s)
                clean = re.sub(r"^##\[[^\]]+\]", "", clean).strip()
                if clean and clean not in causes:
                    causes.append(clean[:400])
                break
    return causes[:30]


# ---------------------------------------------------------------------------
# Auto-fixes (deterministic, from scientist.md playbook)
# ---------------------------------------------------------------------------


def fix_missing_draft() -> list[str]:
    changed: list[str] = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md":
            continue
        text = fp.read_text("utf-8")
        if not text.startswith("---"):
            continue
        if re.search(r"(?m)^draft:\s*", text):
            continue
        # insert after first date: line or after opening ---
        new, n = re.subn(
            r"(?m)^(date:.*\n)",
            r"\1draft: false\n",
            text,
            count=1,
        )
        if n == 0:
            new = text.replace("---\n", "---\ndraft: false\n", 1)
        if new != text:
            fp.write_text(new, "utf-8")
            changed.append(str(fp.relative_to(ROOT)))
    return changed


def fix_missing_keywords() -> list[str]:
    import yaml

    changed: list[str] = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md":
            continue
        text = fp.read_text("utf-8")
        parts = text.split("---")
        if len(parts) < 3:
            continue
        try:
            meta = yaml.safe_load(parts[1])
        except Exception:
            continue
        if not meta or meta.get("keywords"):
            continue
        tags = meta.get("tags") or []
        section = fp.parent.name
        kw = [section] + list(tags)[:4] if tags else [section, "korea", "entertainment"]
        meta["keywords"] = kw[:5]
        if not meta.get("author"):
            meta["author"] = "KoreaWiki Newsroom"
        new_fm = yaml.dump(
            meta, default_flow_style=False, allow_unicode=True, sort_keys=False
        ).strip()
        fp.write_text(f"---\n{new_fm}\n---\n{parts[2].lstrip()}", "utf-8")
        changed.append(str(fp.relative_to(ROOT)))
    return changed


def fix_missing_author() -> list[str]:
    import yaml

    changed: list[str] = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md":
            continue
        text = fp.read_text("utf-8")
        parts = text.split("---")
        if len(parts) < 3:
            continue
        try:
            meta = yaml.safe_load(parts[1])
        except Exception:
            continue
        if not meta or meta.get("author"):
            continue
        meta["author"] = "KoreaWiki Newsroom"
        new_fm = yaml.dump(
            meta, default_flow_style=False, allow_unicode=True, sort_keys=False
        ).strip()
        fp.write_text(f"---\n{new_fm}\n---\n{parts[2].lstrip()}", "utf-8")
        changed.append(str(fp.relative_to(ROOT)))
    return changed


def fix_markdown_formatting() -> list[str]:
    changed: list[str] = []
    for fp in sorted(CONTENT.rglob("*.md")):
        if fp.name == "_index.md":
            continue
        text = fp.read_text("utf-8")
        new = re.sub(r"  +(\n)", r"\1", text)
        lines = new.split("\n")
        out: list[str] = []
        dirty = False
        for line in lines:
            if len(line) > 200 and not line.startswith("|") and not line.startswith("http"):
                while len(line) > 180:
                    break_at = line.rfind(" ", 0, 180)
                    if break_at == -1:
                        break_at = 180
                    out.append(line[:break_at])
                    line = line[break_at:].lstrip()
                    dirty = True
            out.append(line)
        new2 = "\n".join(out)
        if new2 != text:
            fp.write_text(new2, "utf-8")
            changed.append(str(fp.relative_to(ROOT)))
            dirty = True
        elif new != text:
            fp.write_text(new, "utf-8")
            changed.append(str(fp.relative_to(ROOT)))
    return changed


def fix_slugs() -> list[str]:
    proc = run([sys.executable, str(ROOT / "scripts" / "slug.py")])
    if proc.returncode != 0 and "Normalized" not in (proc.stdout or ""):
        # slug.py returns 0 when fixing without --check
        pass
    changed: list[str] = []
    for line in (proc.stdout or "").splitlines():
        if line.strip().startswith("- "):
            changed.append(f"content/{line.strip()[2:]}")
    if "Normalized" in (proc.stdout or ""):
        return changed or ["(slugs normalized)"]
    return changed


def fix_hugo_try_function() -> list[str]:
    """Scientist Entry: Hugo 0.126 lacks try — replace with fileExists + readFile."""
    changed: list[str] = []
    layouts = list((ROOT / "themes").rglob("*.html")) + list((ROOT / "layouts").rglob("*.html"))
    # Pattern: {{ with try (readFile "path") }} ... {{ else }} ... {{ end }}{{ end }}
    # Simpler: any occurrence of function try
    try_re = re.compile(
        r"\{\{\s*with\s+try\s+\(readFile\s+\"([^\"]+)\"\)\s*\}\}"
        r"(.*?)"
        r"\{\{\s*end\s*\}\}",
        re.S,
    )
    for fp in layouts:
        text = fp.read_text("utf-8")
        if "try" not in text or "readFile" not in text:
            # also bare {{ try ...
            if not re.search(r"\{\{[^}]*\btry\b", text):
                continue
        original = text
        # Replace common try(readFile) blocks used in glossary
        def replacer(m: re.Match[str]) -> str:
            path = m.group(1)
            body = m.group(2)
            # strip nested else branches loosely
            return (
                f'{{{{ if fileExists "{path}" }}}}\n'
                f'  {{{{ with readFile "{path}" }}}}\n'
                f"{body}"
                f"  {{{{ end }}}}\n"
                f"{{{{ end }}}}"
            )

        text2 = try_re.sub(replacer, text)
        # Nuclear safe: comment-out bare try tokens that still parse-fail
        # Replace `try (` with nothing won't work. Replace `try ` function calls:
        text2 = re.sub(
            r"\{\{\s*with\s+try\s+",
            "{{ with ",
            text2,
        )
        # If still has try as function: {{ try something }}
        text2 = re.sub(r"\{\{\s*try\s+", "{{ /* try-removed */ ", text2)
        if text2 != original:
            fp.write_text(text2, "utf-8")
            changed.append(str(fp.relative_to(ROOT)))
    return changed


def fix_glossary_sync() -> list[str]:
    gjson = ROOT / "data" / "glossary" / "glossary.json"
    if not gjson.exists():
        return []
    proc = run([sys.executable, str(ROOT / "scripts" / "glossary.py"), "sync"])
    if proc.returncode == 0:
        return ["data/glossary/*", "content/en/glossary/_index.md"]
    return []


def fix_article_features() -> list[str]:
    """Ensure every post has faq: + article-footer (mandatory product features)."""
    script = ROOT / "scripts" / "apply_article_footer.py"
    if not script.exists():
        return []
    proc = run([sys.executable, str(script), "--apply"])
    if proc.returncode != 0:
        return []
    # mark as changed if script reported updates
    out = (proc.stdout or "") + (proc.stderr or "")
    if "updated" in out:
        return ["content/** (faq + article-footer via apply_article_footer.py)"]
    return []


def apply_fixes(categories: list[str], log: str) -> dict[str, list[str]]:
    """Apply safe deterministic fixes. Never fabricates article content."""
    applied: dict[str, list[str]] = {}

    # Always run content hygiene known from scientist.md when QA/SEO/markdown fail
    always_content = any(
        c in categories
        for c in ("python_qa", "seo", "frontmatter", "markdown", "slug", "unknown")
    )
    if always_content or "Missing: 'draft'" in log or "draft" in log.lower():
        ch = fix_missing_draft()
        if ch:
            applied["missing_draft"] = ch

    if (
        always_content
        or "article-footer" in log
        or "faq:" in log
        or "Bài này trả lời" in log
        or "apply_article_footer" in log
    ):
        ch = fix_article_features()
        if ch:
            applied["article_features"] = ch

    if always_content or "keywords" in log.lower() or "seo" in categories:
        ch = fix_missing_keywords()
        if ch:
            applied["missing_keywords"] = ch
        ch = fix_missing_author()
        if ch:
            applied["missing_author"] = ch

    if always_content or "markdown" in categories or "Trailing whitespace" in log:
        ch = fix_markdown_formatting()
        if ch:
            applied["markdown_format"] = ch

    if always_content or "slug" in categories or "slug" in log.lower():
        ch = fix_slugs()
        if ch:
            applied["slugs"] = ch

    if "hugo" in categories or "function \"try\" not defined" in log or "try" in log:
        ch = fix_hugo_try_function()
        if ch:
            applied["hugo_try"] = ch

    if "glossary" in categories or "glossary" in log.lower():
        ch = fix_glossary_sync()
        if ch:
            applied["glossary_sync"] = ch

    # If still no applied fixes and log empty, run full hygiene suite once
    if not applied and not log.strip():
        for name, fn in (
            ("missing_draft", fix_missing_draft),
            ("missing_keywords", fix_missing_keywords),
            ("missing_author", fix_missing_author),
            ("article_features", fix_article_features),
            ("markdown_format", fix_markdown_formatting),
            ("slugs", fix_slugs),
            ("hugo_try", fix_hugo_try_function),
        ):
            ch = fn()
            if ch:
                applied[name] = ch

    return applied


# ---------------------------------------------------------------------------
# Validation (mirrors .github/workflows/build.yml + scientist.md)
# ---------------------------------------------------------------------------

VALIDATION_STEPS: list[tuple[str, list[str]]] = [
    ("qa", [sys.executable, "scripts/qa.py"]),
    ("seo", [sys.executable, "scripts/seo.py"]),
    ("frontmatter", [sys.executable, "scripts/frontmatter_check.py"]),
    ("markdown_lint", [sys.executable, "scripts/markdown_lint.py"]),
    ("links", [sys.executable, "scripts/check_links.py"]),
    ("slugs", [sys.executable, "scripts/slug.py", "--check"]),
    ("images", [sys.executable, "scripts/optimize_images.py"]),
    ("hugo", ["hugo", "--minify", "--gc"]),
    ("schema", [sys.executable, "scripts/generate_schema.py"]),
]


def validate_all() -> dict[str, Any]:
    results: dict[str, Any] = {"ok": True, "steps": {}}
    for name, cmd in VALIDATION_STEPS:
        # hugo may not exist in minimal envs
        if name == "hugo":
            which = run(["which", "hugo"])
            if which.returncode != 0:
                results["steps"][name] = {
                    "ok": False,
                    "skipped": False,
                    "output": "hugo not installed",
                }
                results["ok"] = False
                continue
        proc = run(cmd)
        ok = proc.returncode == 0
        out = ((proc.stdout or "") + (proc.stderr or "")).strip()
        results["steps"][name] = {"ok": ok, "output": out[-4000:]}
        if not ok:
            results["ok"] = False
    return results


# ---------------------------------------------------------------------------
# Scientist integration
# ---------------------------------------------------------------------------


def append_scientist_entry(summary: dict[str, Any]) -> None:
    if not SCIENTIST.exists():
        return
    entry = f"""
## Entry AUTO — {datetime.now(timezone.utc).strftime("%Y-%m-%d")}: Self-healing recovery

**Trigger:** CI/CD failure (workflow run `{summary.get("run_id", "?")}`)

**Root causes:**
{chr(10).join("- " + c for c in summary.get("root_causes", [])[:10]) or "- (see report)"}

**Categories:** {", ".join(summary.get("categories", []))}

**Auto-fixes applied:** {", ".join(summary.get("fixes", {}).keys()) or "none"}

**Validation:** {"GREEN" if summary.get("validation_ok") else "RED"}

**Report:** `{summary.get("report_dir", "reports/self-healing/")}`

**Prevention:** Self-healing workflow re-runs on next failure (max {MAX_ROUNDS} rounds).

---
"""
    text = SCIENTIST.read_text("utf-8")
    # Insert after title block (after first --- following intro) — append before "To re-apply"
    marker = "\nTo re-apply all known fixes"
    if marker in text:
        text = text.replace(marker, entry + marker, 1)
    else:
        text = text.rstrip() + "\n" + entry
    SCIENTIST.write_text(text, "utf-8")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def write_report(
    report_dir: Path,
    *,
    log: str,
    categories: list[str],
    root_causes: list[str],
    fixes: dict[str, list[str]],
    validation: dict[str, Any],
    round_n: int,
    run_id: str,
    status: str,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "workflow.log").write_text(log or "(no log captured)\n", "utf-8")
    diag = {
        "timestamp": utc_now(),
        "run_id": run_id,
        "round": round_n,
        "max_rounds": MAX_ROUNDS,
        "categories": categories,
        "root_causes": root_causes,
        "status": status,
    }
    (report_dir / "diagnostics.json").write_text(
        json.dumps(diag, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    (report_dir / "root_cause.md").write_text(
        "# Root Cause Analysis\n\n"
        + "\n".join(f"- `{c}`" for c in categories)
        + "\n\n## Signals\n\n"
        + "\n".join(f"- {x}" for x in root_causes)
        + "\n",
        "utf-8",
    )
    patch = {
        "fixes": {k: v for k, v in fixes.items()},
        "files_touched": sorted({f for fs in fixes.values() for f in fs}),
    }
    (report_dir / "patch_summary.json").write_text(
        json.dumps(patch, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    (report_dir / "validation_summary.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )

    remaining = [
        name
        for name, step in validation.get("steps", {}).items()
        if not step.get("ok")
    ]
    md = f"""# Recovery Report

- **Timestamp:** {diag["timestamp"]}
- **Run ID:** {run_id or "n/a"}
- **Round:** {round_n} / {MAX_ROUNDS}
- **Status:** {status}

## Root Cause

Categories: {", ".join(categories)}

### Signals
{chr(10).join("- " + x for x in root_causes) or "- (none extracted)"}

## Files Changed
{chr(10).join("- `" + f + "`" for f in patch["files_touched"]) or "- (no automatic patches)"}

## Fixes Applied
{chr(10).join("- **" + k + "**: " + str(len(v)) + " file(s)" for k, v in fixes.items()) or "- none"}

## Validation
{"ALL GREEN" if validation.get("ok") else "REMAINING FAILURES: " + ", ".join(remaining)}

## Remaining Errors
"""
    for name in remaining:
        out = validation["steps"][name].get("output", "")
        md += f"\n### {name}\n```\n{out[-1500:]}\n```\n"

    if status != "recovered":
        md += """
## Suggested Manual Fix

1. Open the workflow log in `workflow.log`.
2. Consult `scientist.md` for a matching past entry.
3. Apply a minimal fix; never fabricate content.
4. Run `python3 scripts/self_healing.py validate`.
5. Commit and push — do **not** force-deploy while validations are red.
"""
    report_path = report_dir / "RECOVERY_REPORT.md"
    report_path.write_text(md, "utf-8")
    (report_dir / "deployment_summary.json").write_text(
        json.dumps(
            {
                "timestamp": utc_now(),
                "status": status,
                "deploy_forced": False,
                "note": "Deploy only after validations are green via normal Build & Deploy workflow.",
            },
            indent=2,
        )
        + "\n",
        "utf-8",
    )
    return report_path


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_analyze(args: argparse.Namespace) -> int:
    log = read_log(Path(args.log) if args.log else None)
    cats = categorize(log)
    causes = extract_root_causes(log)
    print(json.dumps({"categories": cats, "root_causes": causes}, indent=2, ensure_ascii=False))
    return 0


def cmd_fix(args: argparse.Namespace) -> int:
    log = read_log(Path(args.log) if args.log else None)
    cats = categorize(log) if log else ["unknown"]
    fixes = apply_fixes(cats, log)
    print(json.dumps(fixes, indent=2, ensure_ascii=False))
    return 0 if fixes else 1


def cmd_validate(args: argparse.Namespace) -> int:
    results = validate_all()
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if results["ok"] else 1


def cmd_recover(args: argparse.Namespace) -> int:
    round_n = int(args.round or 1)
    run_id = args.run_id or os.environ.get("SELF_HEAL_RUN_ID", "")
    log = read_log(Path(args.log) if args.log else None)
    report_dir = ensure_reports_dir(run_id or "local")

    if round_n > MAX_ROUNDS:
        validation = validate_all()
        write_report(
            report_dir,
            log=log,
            categories=categorize(log),
            root_causes=extract_root_causes(log),
            fixes={},
            validation=validation,
            round_n=round_n,
            run_id=run_id,
            status="max_rounds_exceeded",
        )
        print(f"MAX ROUNDS ({MAX_ROUNDS}) exceeded. See {report_dir}")
        return 2

    categories = categorize(log)
    root_causes = extract_root_causes(log)
    fixes: dict[str, list[str]] = {}

    # Multi-pass fix+validate within this invocation (up to remaining rounds budget)
    for attempt in range(1, MAX_ROUNDS + 1):
        if attempt > 1 or round_n > 1:
            print(f"== Self-heal pass {attempt} (round {round_n}) ==")
        fixes_pass = apply_fixes(categories, log)
        for k, v in fixes_pass.items():
            fixes.setdefault(k, [])
            for f in v:
                if f not in fixes[k]:
                    fixes[k].append(f)

        validation = validate_all()
        if validation["ok"]:
            status = "recovered"
            write_report(
                report_dir,
                log=log,
                categories=categories,
                root_causes=root_causes,
                fixes=fixes,
                validation=validation,
                round_n=round_n,
                run_id=run_id,
                status=status,
            )
            summary = {
                "run_id": run_id,
                "root_causes": root_causes,
                "categories": categories,
                "fixes": fixes,
                "validation_ok": True,
                "report_dir": str(report_dir.relative_to(ROOT)),
            }
            if not args.no_scientist:
                append_scientist_entry(summary)
            # marker for workflow
            (report_dir / "STATUS").write_text("recovered\n", "utf-8")
            print(f"RECOVERED after pass {attempt}. Report: {report_dir}")
            return 0

        # Feed validation failures into next categorize
        fail_blob = "\n".join(
            validation["steps"][s].get("output", "")
            for s in validation["steps"]
            if not validation["steps"][s].get("ok")
        )
        log = log + "\n" + fail_blob
        categories = list(dict.fromkeys(categories + categorize(fail_blob)))
        if not fixes_pass:
            break  # no more automatic patches

    validation = validate_all()
    status = "failed"
    write_report(
        report_dir,
        log=log,
        categories=categories,
        root_causes=root_causes,
        fixes=fixes,
        validation=validation,
        round_n=round_n,
        run_id=run_id,
        status=status,
    )
    (report_dir / "STATUS").write_text("failed\n", "utf-8")
    summary = {
        "run_id": run_id,
        "root_causes": root_causes,
        "categories": categories,
        "fixes": fixes,
        "validation_ok": False,
        "report_dir": str(report_dir.relative_to(ROOT)),
    }
    if not args.no_scientist:
        append_scientist_entry(summary)
    print(f"FAILED to fully recover. Report: {report_dir}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="KoreaWiki self-healing recovery")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("analyze", help="Categorize failure log")
    s.add_argument("--log", default=None)
    s.set_defaults(func=cmd_analyze)

    s = sub.add_parser("fix", help="Apply deterministic auto-fixes")
    s.add_argument("--log", default=None)
    s.set_defaults(func=cmd_fix)

    s = sub.add_parser("validate", help="Run full scientist/CI validation suite")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("recover", help="Full recovery: fix → validate → report")
    s.add_argument("--log", default=None)
    s.add_argument("--round", type=int, default=1)
    s.add_argument("--run-id", default="")
    s.add_argument("--no-scientist", action="store_true")
    s.set_defaults(func=cmd_recover)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    code = args.func(args)
    sys.exit(code if isinstance(code, int) else 0)


if __name__ == "__main__":
    main()
