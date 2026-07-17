"""Check Hugo templates for image/href paths missing | relURL filter."""
import re, sys
from pathlib import Path

TEMPLATES = Path("themes/koreawiki/layouts")
PATTERN = re.compile(r'\{\{\s*\.Params\.\w+\.(?:image|src|thumbnail|cover)\s*\}\}')
RELURL_CHECK = re.compile(r'\|\s*(relURL|absURL)')

def run():
    files = list(TEMPLATES.rglob("*.html"))
    issues = []
    for fp in sorted(files):
        for i, line in enumerate(fp.read_text("utf-8").splitlines(), 1):
            for m in PATTERN.finditer(line):
                if not RELURL_CHECK.search(line[m.end():]):
                    rel = fp.relative_to(TEMPLATES)
                    issues.append(f"  {rel}:{i}  {m.group()}  (missing | relURL)")
    return issues
