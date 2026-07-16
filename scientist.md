# Scientist Log — KoreaWiki Bug History & Fixes

> Scientist (과학자): chuyên lưu lại lịch sử fix lỗi, dùng lịch sử này để fix toàn bộ lỗi của blog — kiểu như khoa học gia, chuyên sửa chữa quá khứ lẫn cái mới phát sinh hiện tại.

## Entry 001 — 2026-07-16: Missing `draft` field in all articles

**Error:** `scripts/qa.py` failed with "Missing: 'draft'" in all 40 articles.

**Root Cause:** Sample articles were generated without the `draft: false` field in frontmatter. The QA script (`scripts/qa.py`) validates that every article has a `draft` field.

**Fix:** Added `draft: false` to all 40 article frontmatter files.

**Files affected:** `content/en/*/*.md` (40 files, excluding `_index.md`)

**Detection:** QA pipeline step in `.github/workflows/build.yml`

**Prevention:** Add `draft` to required fields in content generation template.

---

## Entry 002 — 2026-07-16: Corrupted frontmatter in `videos/korean-creator-economy-boom.md`

**Error:** QA script reported "No valid front matter" for one file.

**Root Cause:** The file contained tool call artifacts (task agent JSON/RPC output) instead of YAML frontmatter and article content.

**Fix:** Replaced corrupted file with proper frontmatter and full article content.

**File affected:** `content/en/videos/korean-creator-economy-boom.md`

**Detection:** QA pipeline step

**Prevention:** Validate generated files immediately after creation; add automated YAML frontmatter validation.

---

## Entry 003 — 2026-07-16: Missing `keywords` field in all 40 articles

**Error:** `scripts/seo.py` failed with "Missing keywords" for all 40 articles.

**Root Cause:** Sample articles lacked the `keywords` field (list of 3+) in frontmatter.

**Fix:** Added `keywords` derived from existing `tags`, `categories`, and section name. Script automatically added up to 5 relevant keywords per article.

**Files affected:** `content/en/*/*.md` (40 files)

**Detection:** SEO pipeline step

**Prevention:** Include `keywords` in content generation template; add pre-commit hook to validate SEO fields.

---

## Entry 004 — 2026-07-16: GitHub Actions deploy failed — two-workflow artifact issue

**Error:** `deploy-pages@v4` could not find the deployment artifact. The build (`build.yml`) and deploy (`deploy.yml`) were in separate workflows.

**Root Cause:** `upload-pages-artifact` and `deploy-pages` must run within the same workflow job for the artifact to be accessible.

**Fix:** Consolidated both steps into a single `build.yml` workflow; deleted `deploy.yml`.

**Files affected:** `.github/workflows/build.yml`, `.github/workflows/deploy.yml`

**Detection:** Manual review of GitHub Actions logs

**Prevention:** Always run build + deploy in a single workflow when using `actions/deploy-pages@v4`.

---

## Entry 005 — 2026-07-16: Wiki theme rebuild to news/magazine layout

**Change:** Complete rewrite from wiki-style theme to premium digital newspaper layout.

**Details:** 15 SCSS component files, new Hugo layouts (baseof, header, footer, homepage, single, list), 55 content files across 15 sections, updated config with i18n and menus.

**Trigger:** User requested news/magazine design with blue/orange color scheme.

**Files affected:** ~124 files changed, 2055 insertions, 958 deletions.

---

## Entry 006 — 2026-07-16: Breadcrumb appears on homepage

**Error:** Homepage showed breadcrumb navigation (Home / section title) which is inappropriate for the landing page.

**Root Cause:** `baseof.html` rendered breadcrumb unconditionally with `{{ partial "breadcrumb" . }}` even when `.IsHome` was true.

**Fix:** Added condition to skip breadcrumb on homepage: `{{ if and (not .IsHome) ... }}`

**File affected:** `themes/koreawiki/layouts/_default/baseof.html`

**Detection:** Visual review of rendered homepage

**Prevention:** Always guard breadcrumb/section-header partials against `.IsHome`.

---

## Entry 007 — 2026-07-16: Markdown lint failures (trailing whitespace + long lines)

**Error:** `scripts/markdown_lint.py` reported 201 issues across all 40 articles.

**Root Cause:** Two rule violations: (1) trailing whitespace (2+ spaces before newline) in many paragraphs, (2) lines exceeding 200 characters.

**Fix:** Automated fix script removed trailing whitespace and broke long lines (>180 chars) at word boundaries.

**Files affected:** All 40 article files

**Detection:** QA pipeline step `python scripts/markdown_lint.py`

**Prevention:** Add markdown-lint pre-commit hook; set editor to trim trailing whitespace on save.

---

## Entry 008 — 2026-07-16: Missing slug field in all 40 articles

**Error:** `scripts/slug.py --check` reported 40 files need slug normalization.

**Root Cause:** Articles had no `slug` field in frontmatter. The slug script generates a URL-safe slug from the title.

**Fix:** Ran `python3 scripts/slug.py` (without `--check`) to auto-add normalized slugs.

**Files affected:** All 40 article files

**Detection:** QA pipeline step `python scripts/slug.py --check`

**Prevention:** Add `slug` to content generation template; run `slug.py` during content creation.

---

## Fix Replay Scripts

To re-apply all known fixes to fresh content:

### Fix missing `draft` field
```bash
python3 -c "
import glob, re
for f in glob.glob('content/en/**/*.md', recursive=True):
    if '_index' in f: continue
    with open(f) as fh: c = fh.read()
    if 'draft:' not in c:
        c = re.sub(r'^(date:.*)\n', r'\1\ndraft: false\n', c, flags=re.MULTILINE)
        with open(f, 'w') as fh: fh.write(c)
"
```

### Fix trailing whitespace + long lines
```bash
python3 << 'PYEOF'
import re
from pathlib import Path
for fp in sorted(Path("content/en").rglob("*.md")):
    if fp.name == "_index.md": continue
    text = fp.read_text("utf-8")
    text = re.sub(r'  +(\n)', r'\1', text)
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if len(line) > 200 and not line.startswith("|"):
            broken = []
            while len(line) > 180:
                break_at = line.rfind(" ", 0, 180)
                if break_at == -1: break_at = 180
                broken.append(line[:break_at])
                line = line[break_at:].strip()
            if line: broken.append(line)
            lines[i] = "\n".join(broken)
    fp.write_text("\n".join(lines), "utf-8")
PYEOF
```

### Fix missing `keywords` field
```bash
python3 << 'PYEOF'
import yaml, re
from pathlib import Path
content_dir = Path("content/en")
for fp in sorted(content_dir.rglob("*.md")):
    if fp.name == "_index.md": continue
    text = fp.read_text("utf-8")
    parts = text.split("---")
    if len(parts) < 3: continue
    meta = yaml.safe_load(parts[1])
    if not meta or meta.get("keywords"): continue
    tags = meta.get("tags", [])
    section = fp.parent.name
    kw = [section] + tags[:4] if tags else [section, "korea", "entertainment"]
    meta["keywords"] = kw[:5]
    new_fm = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()
    text = f"---\n{new_fm}\n---\n{parts[2].strip()}\n"
    fp.write_text(text, "utf-8")
PYEOF
```
