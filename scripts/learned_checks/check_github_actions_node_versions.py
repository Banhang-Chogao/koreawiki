"""Check: GitHub Actions pinned to Node 20 versions (deprecated on Node 24 runners)."""
import re
from pathlib import Path

WORKFLOWS = Path(".github/workflows")
PATTERNS = {
    "actions/checkout@v4": "→ upgrade to actions/checkout@v5 (Node 24)",
    "actions/setup-python@v5": "→ upgrade to actions/setup-python@v6 (Node 24)",
}

def run():
    issues = []
    if not WORKFLOWS.is_dir():
        return issues
    for fp in sorted(WORKFLOWS.glob("*.yml")):
        text = fp.read_text("utf-8")
        for snippet, msg in PATTERNS.items():
            for lineno, line in enumerate(text.splitlines(), 1):
                if snippet in line:
                    issues.append(f"  {fp.name}:{lineno}  {snippet}  {msg}")
    return issues
