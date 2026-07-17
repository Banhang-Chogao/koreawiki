"""Check Hugo templates for old English date formats."""
import re, sys
from pathlib import Path

TEMPLATES = Path("themes/koreawiki/layouts")
OLD_PATTERNS = [
    (r'\.Format "Jan 2, 2006"', 'English date format "Jan 2, 2006"'),
    (r'\.Format "02/01/2006"', 'Short date format "02/01/2006"'),
]

def run():
    files = list(TEMPLATES.rglob("*.html"))
    issues = []
    for fp in sorted(files):
        for i, line in enumerate(fp.read_text("utf-8").splitlines(), 1):
            for pattern, desc in OLD_PATTERNS:
                if re.search(pattern, line):
                    rel = fp.relative_to(TEMPLATES)
                    issues.append(f"  {rel}:{i}  {desc}")
    return issues
