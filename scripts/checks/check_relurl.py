"""Comprehensive template scanner: catch ANY .Params.* in src/href missing relURL.

Scans all Hugo .html templates for src/href/ srcset attributes whose value
comes from a .Params variable without | relURL or | absURL filter.
Catches ANY param key — not just known ones like image/cover/thumbnail.
"""
import re
from pathlib import Path

TEMPLATES = Path("themes/koreawiki/layouts")

# Match: src="{{ ... }}", href="{{ ... }}", srcset="{{ ... }}"
ATTR_PATTERN = re.compile(
    r'(?:src|href|srcset|data-src|poster)\s*=\s*"({{\s*[^}]+}})"'
)

# Inside the {{ }}, find .Params.x.y patterns
PARAM_REF = re.compile(r'\.Params\.\w+(?:\.\w+)*')

# Check if relURL or absURL is already applied
HAS_FILTER = re.compile(r'\|\s*(?:relURL|absURL|relLangURL|absLangURL|safeURL)')
EXTERNAL_PARAMS = {'source_url', 'source_label', 'image_source_url', 'image_creator_url'}

# Also check raw variable assignments from .Params
VAR_PATTERN = re.compile(r'\{\{\s*\$(\w+)\s*:=\s*\.Params\.')
VAR_USE_IN_ATTR = re.compile(r'\{\{\s*\$(\w+)\s*\}\}')

def run():
    files = list(TEMPLATES.rglob("*.html"))
    issues = []

    for fp in sorted(files):
        text = fp.read_text("utf-8")
        lines = text.splitlines()

        # Track vars assigned from .Params
        param_vars = {}
        for i, line in enumerate(lines, 1):
            for m in VAR_PATTERN.finditer(line):
                param_vars[m.group(1)] = i

        # Check src/href attributes
        for i, line in enumerate(lines, 1):
            # Skip lines that are OK
            if HAS_FILTER.search(line):
                continue

            # Check attribute values with {{ }}
            for attr_m in ATTR_PATTERN.finditer(line):
                inner = attr_m.group(1)

                # Check if it uses .Params directly
                for pm in PARAM_REF.finditer(inner):
                    param_name = pm.group().split('.')[-1]
                    if param_name in EXTERNAL_PARAMS:
                        continue
                    if not HAS_FILTER.search(inner):
                        rel = fp.relative_to(TEMPLATES)
                        issues.append(
                            f"  {rel}:{i}  {pm.group()} in src/href  (missing | relURL)"
                        )

                # Check if it uses a var that came from .Params
                for vm in VAR_USE_IN_ATTR.finditer(inner):
                    varname = vm.group(1)
                    if varname in param_vars:
                        if not HAS_FILTER.search(inner):
                            rel = fp.relative_to(TEMPLATES)
                            issues.append(
                                f"  {rel}:{i}  ${varname} (from .Params, line {param_vars[varname]}) in src/href  (missing | relURL)"
                            )

    return issues
