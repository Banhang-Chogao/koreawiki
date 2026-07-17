"""Post-build: inspect built HTML for ANY relative asset paths that would break
on subdirectory pages. Checks src, href, srcset, data-src, poster, and inline CSS url().

This is the final safety net — catches everything, regardless of template code.
"""
import re
from pathlib import Path

PUBLIC = Path("public")

# Match src, href, srcset, data-src, poster attributes
ATTR_PATTERN = re.compile(
    r'(?:src|href|srcset|data-src|poster)\s*=\s*"(?!https?://|/|#|data:|mailto:)([^"]+)"'
)

# Match inline CSS url(...) with relative paths
CSS_URL_PATTERN = re.compile(
    r'url\(\s*"(?!https?://|/|data:)([^"]+)"\s*\)'
)
CSS_URL_PATTERN2 = re.compile(
    r"url\(\s*'(?!https?://|/|data:)([^']+)'\s*\)"
)

# Match <source srcset="..."> patterns
SOURCE_PATTERN = re.compile(
    r'<source\s[^>]*srcset\s*=\s*"(?!https?://|/)([^"]+)"'
)

def run():
    if not PUBLIC.is_dir():
        return []

    issues = []
    html_files = sorted(PUBLIC.rglob("*.html"))

    for fp in html_files:
        text = fp.read_text("utf-8", errors="replace")
        rel = fp.relative_to(PUBLIC)

        # Check src/href/srcset/data-src/poster
        for m in ATTR_PATTERN.finditer(text):
            val = m.group(1)
            # Skip Hugo template residue and valid relative refs
            if val and not val.startswith(("%7B%7B", "{{", "%7B%20")):
                issues.append(f"  {rel}  {m.group(0)[:100]}")

        # Check inline CSS url()
        for m in CSS_URL_PATTERN.finditer(text):
            val = m.group(1)
            if val and not val.startswith(("%7B%7B", "{{")):
                issues.append(f"  {rel}  css url({val})")

        for m in CSS_URL_PATTERN2.finditer(text):
            val = m.group(1)
            if val and not val.startswith(("%7B%7B", "{{")):
                issues.append(f"  {rel}  css url({val})")

        # Check <source srcset>
        for m in SOURCE_PATTERN.finditer(text):
            val = m.group(1)
            if val and not val.startswith(("%7B%7B", "{{")):
                issues.append(f"  {rel}  {m.group(0)[:100]}")

    return issues
