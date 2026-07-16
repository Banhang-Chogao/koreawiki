#!/usr/bin/env python3
"""Generate data-hugo/git_first_live.json — first GitHub live time per content file.

Latest News must order by when a post first went live on GitHub (the commit
that *added* the content file), not by last-touch CommitDate.

Last-touch is wrong after batch edits (footer/FAQ/lint) which re-touch every
file in one commit and scramble the feed.

Keys are paths relative to content/ (matches Hugo .File.Path).
Values are objects:
  { "unix": <int>, "iso": "<RFC3339 UTC>" }
Hugo sorts on unix; displays with time.AsTime on iso
(time.Unix is unavailable / broken on some Hugo versions).

Output goes to data-hugo/ (project dataDir) — not data/ (glossary + sqlite).

Usage:
  python scripts/git_first_live.py
Requires full git history (CI: fetch-depth: 0).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
OUT = ROOT / "data-hugo" / "git_first_live.json"


def first_commit_unix(rel_from_root: str) -> int | None:
    """Unix time of the first commit that added this path."""
    try:
        out = subprocess.check_output(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--follow",
                "--reverse",
                "--format=%ct",
                "--",
                rel_from_root,
            ],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return None
    if out:
        return int(out.splitlines()[0])

    # Fallback: oldest commit that ever touched the file
    try:
        out = subprocess.check_output(
            [
                "git",
                "log",
                "--reverse",
                "--format=%ct",
                "--",
                rel_from_root,
            ],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return None
    if out:
        return int(out.splitlines()[0])
    return None


def main() -> int:
    if not (ROOT / ".git").exists() and not (ROOT / ".git").is_file():
        # worktree .git can be a file pointing at main repo
        print("warn: no .git found; writing empty map", file=sys.stderr)

    mapping: dict[str, dict[str, object]] = {}
    for md in sorted(CONTENT.rglob("*.md")):
        if md.name == "_index.md":
            continue
        rel_root = md.relative_to(ROOT).as_posix()
        key = md.relative_to(CONTENT).as_posix()  # Hugo .File.Path
        ts = first_commit_unix(rel_root)
        if ts is not None:
            iso = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            mapping[key] = {"unix": ts, "iso": iso}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(mapping)} entries → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
