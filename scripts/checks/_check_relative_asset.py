"""Post-build: check built HTML for relative asset paths (missing /koreawiki/)."""
import re, sys
from pathlib import Path

PUBLIC = Path("public")
PATTERN = re.compile(
    r'(src|href)\s*=\s*"(?!https?://|/|#|data:|mailto:)([^"]+)"'
)

def run():
    if not PUBLIC.is_dir():
        return []

    issues = []
    for fp in sorted(PUBLIC.rglob("*.html")):
        for m in PATTERN.finditer(fp.read_text("utf-8", errors="replace")):
            val = m.group(2)
            if val and not val.startswith(("%7B%7B", "{{")):
                rel = fp.relative_to(PUBLIC)
                issues.append(f"  {rel}  {m.group(1)}=\"{val}\"")
    return issues
