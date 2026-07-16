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

## Entry 009 — 2026-07-16: Added `mm` command — Korean news publishing workflow

**Added:** `.opencode/commands/mm.md` — a full workflow for publishing Korean news articles.

**Workflow:** URL → fetch → extract → translate → rewrite → image handle → Hugo front matter → Markdown → QA → build → commit → push.

**Trigger:** Type `mm` in opencode.

**Rules:** Never fabricate facts/dates/quotes/credits. Never push failing code. Follow all scientist.md QA rules.

---

## Entry 010 — 2026-07-16: Slug auto-generates from Vietnamese title with correct transliteration

**Error:** `scripts/seo.py` rejected slug `gong-yoo-tổ-chức-tour-fan-meeting-châu-á-đầu-tiên-sau-25-năm-sự-nghiệp` — regex `^[a-z0-9\-]+$` doesn't allow Vietnamese characters.

**Root Cause:** `slug.py` used `\w` in regex which matches Unicode word chars (Vietnamese letters pass through). `seo.py` requires pure ASCII slugs.

**Fix:**
1. `slugify()` now transliterates `đ→d`, decomposes accents via `unicodedata.normalize('NFD')`, strips combining marks `[\u0300-\u036f]`, then keeps only `[a-z0-9\s-]`.
2. `slug.py` always auto-generates slug from title (no manual override).
3. `seo.py` regex `^[a-z0-9\-]+$` remains unchanged — slugs are now guaranteed ASCII.

**Files affected:** `scripts/slug.py`
- Added `import unicodedata`
- Added `VIET_MAP` translation table for `đ/Đ`
- Changed regex from `\w` to `[a-z0-9]` after NFD + combining mark removal
- Removed "keep existing slug" logic

**Example:** Title `today đi` → slug `today-di` ✅

**Detection:** `python scripts/seo.py` CI step

**Prevention:** Slug is always derived from title; no manual slug editing needed.

---

## Entry 011 — 2026-07-16: Article content merged but not deployed (workflow cancelled by newer push)

**Error:** Bài viết mới được thêm trong commit `49ac4d5` (file `.md` + ảnh) nhưng không xuất hiện trên GitHub Pages.

**Root Cause:** Commit `49ac4d5` trigger workflow run `29476989154`, nhưng bị **cancel** vì commit mới hơn (`ee90910`) được push lên cùng lúc. Commit `ee90910` chỉ update `shortcuts.md` chứ không include nội dung bài viết, nên deploy thành công nhưng thiếu nội dung.

**Fix:** Push một empty commit để trigger lại workflow:
```bash
git commit --allow-empty -m "redeploy article" && git push
```

**Detection:** Kiểm tra GitHub Actions — thấy commit chứa nội dung article có status `cancelled` với annotation "Canceling since a higher priority waiting request for pages exists".

**Prevention:** Khi push nhiều commit liên tiếp, đợi workflow hiện tại chạy xong trước khi push commit mới. Nếu workflow bị cancel, push empty commit để trigger lại.

---

## Entry 012 — 2026-07-16: Smart Search Engine (Pagefind) rebuild

**Change:** Hoàn thiện KoreaWiki Smart Search — thay skeleton Fuse/Pagefind dở bằng full client-side search trên Pagefind.

**Architecture decisions:**
1. **Pagefind primary** — full-text, fuzzy, prefix, multilingual, Web Worker built-in, zero backend, GitHub Pages + offline.
2. **Không dùng Lunr** — yếu fuzzy/multilingual so với Pagefind.
3. **Không MiniSearch song song** (v1) — dataset ~50–10k bài, Pagefind đủ; ranking/filter nâng cao làm client-side sau khi Pagefind trả kết quả.
4. **Index tự động** — `hugo && npx pagefind --site public` (local `npm run build`, CI `build.yml`). Không maintain search.json thủ công.
5. **Chỉ index article** — `data-pagefind-body` trên `<article>` single; home/list/taxonomy/header/footer `data-pagefind-ignore`.
6. **Section slug** — không dùng `.Section` (bị = `en` do multilingual nesting); parse từ `File.Dir` / URL → `news`, `kpop`, …
7. **Client layer** (`assets/js/search.js`) — synonym/romanization expand, advanced operators (`tag:`, `year:`, `author:`, …), re-rank (title > tags > body + recency/pin/weight), history/clicks, debounce 50ms, highlight + snippet ~160 chars.
8. **Keyboard** — Ctrl/Cmd+K, `/`, Esc, ↑↓, Enter, Tab autocomplete, focus trap.
9. **SEO** — `robots.txt` Disallow `/pagefind/`; không load pagefind-ui.css (nặng, không dùng).

**Files:**
- `assets/js/search.js`, `assets/js/main.js`, `assets/scss/_search.scss`
- `themes/koreawiki/layouts/partials/pagefind-meta.html` (new)
- `themes/koreawiki/layouts/_default/{baseof,single,list}.html`, `index.html`
- `themes/koreawiki/layouts/partials/{search-modal,scripts,header}.html`
- `layouts/robots.txt`, `pagefind.yml`, `package.json`, `.github/workflows/build.yml`
- `i18n/{en,ko,vi}.toml`, `README.md`, `shortcuts.md`

**Verify:** `hugo && npx pagefind --site public` → Indexed **50 pages** (= 50 articles), 6 filters, 2 sorts. Section filters: kpop, news, artist, …

**Prevention:** Sau mỗi Hugo build luôn chạy Pagefind (script `build` + CI). Không gắn `data-pagefind-body` lên `<body>`.

---

## Entry 026 — 2026-07-16: mm must fetch ALL images (not cover-only)

**Change:** `mm` Step 6 downloads **every usable photo** from the original article, not
just the first cover. Cover still goes to front matter; additional images are saved as
`<slug>-01`, `-02`, … and **embedded in the Markdown body**.

**Helper:** `python3 scripts/fetch_cover.py --page URL --slug … --all` → JSON
`{cover, count, images[]}`. Also improves extraction (lazy attrs, srcset, JSON-LD,
CDN URL harvest, content-hash dedup, browser UA, story-folder filter).

**Why:** Cover-only left multi-photo Dispatch/Kakao pieces looking empty mid-article.

---

## Entry 027 — 2026-07-16: Body Markdown images ignored baseURL

**Error:** ArchDaily/`nn` post had cover OK but body gallery 404.

**Root cause:** Cover uses `{{ cover.image | relURL }}` → `/koreawiki/images/…`.
Body `![…](/images/…)` rendered as `src="/images/…"` (site root of github.io,
**missing** `/koreawiki/`). Files existed under `static/` and returned 200 at
`/koreawiki/images/…`.

**Fix:** `themes/koreawiki/layouts/_default/_markup/render-image.html` —
`strings.TrimPrefix "/" | relURL` for non-http destinations.

**Prevention:** mm/nn docs note body images must go through the render hook.

---

## Entry 026 — 2026-07-16: Permanent shortcut `nn` (English → Vietnamese)

**Added:** `.opencode/commands/nn.md` — durable agent command parallel to `mm`.

| | `mm` | `nn` |
|--|------|------|
| Source | Korean news | **English** news/blog **or ArchDaily** projects |
| Translate | KO → VI | EN → VI |
| Images | `fetch_cover.py --all` | same (+ ArchDaily full gallery rules) |
| QA / footer / FAQ | required | required |

**Docs:** `shortcuts.md` row; use `nn` not `mm` for EN URLs.

---

## Entry 025 — 2026-07-16: Localize EN scaffold posts → Vietnamese

**Fact:** ~40 posts from initial blog scaffold were **demo English** content with
**picsum.photos** placeholder covers — not real Korean-source news (unlike `mm`).

**Action:** Keep them (images are worth it) as first-class posts:
- Download covers → `static/images/sample/`
- Translate title/desc/body/faq → Vietnamese
- Mark `sample_origin: scaffold`

**Script:** `python3 scripts/localize_sample_posts.py --apply`
(Requires `deep-translator` or `XAI_API_KEY` / `OPENAI_API_KEY`.)

---

## Entry 024 — 2026-07-16: mm must fetch cover from original source

**Change:** `mm` Step 6 is mandatory effort: extract `og:image` / body images from the
original Korean article, download into `static/images/YYYY/MM/`, set `cover.image`.

**Helper:** `python3 scripts/fetch_cover.py --page URL --slug …` (or `--image URL`).
**Superseded in part by Entry 026** (`--all` gallery).

**QA:** `scripts/optimize_images.py` also checks front-matter `cover.image` exists under
`static/` and rejects remote-only covers.

**Why:** Posts without thumbnails look broken on hero / Latest News; recent mm runs often
skipped images even when the source had a lead photo.

---

## Entry 023 — 2026-07-16: Latest News = first GitHub live (not last-touch)

**Error:** Sort by `.GitInfo.CommitDate` (last touch) was scrambled by batch commits
(`fac8288` article-footer/FAQ on all posts) — every old post shared one commit time.

**Correct logic:** Latest News = thứ tự bài **mới lên live GitHub** (first commit that
*added* the file), tuần tự newest-first. Batch re-touches must not reshuffle the feed.

**Fix:**
- `scripts/git_first_live.py` → `data-hugo/git_first_live.json` (path → first-add unix)
- `layouts/index.html` + `partials/home/hero.html` sort/display from that map
- CI/package.json run the script before `hugo`
- Mount `data-hugo` → `data` so Hugo does not load `data/glossary/*.sqlite`

**Requires:** `fetch-depth: 0` (already set).

---

## Entry 022 — 2026-07-16: Latest News ordered by GitHub live time

**Change:** Homepage feed sorted by `.GitInfo.CommitDate` (superseded by Entry 023).

**Intent:** "Latest News" = thứ tự bài **lên live GitHub**, không phải ngày báo gốc.

**Requires:** `enableGitInfo = true` + CI `fetch-depth: 0` (already set).

**Display:** Card/hero time uses the same live/git timestamp so UI matches order.
**Superseded:** last-touch GitInfo fails after batch edits → Entry 023 first-add map.

---

## Entry 021 — 2026-07-16: Homepage missing new post (date = source date too old)

**Error:** Bài mm mới (Dispatch Kim Myung-soo) không thấy trên trang chủ dù đã deploy.

**Root cause:** Homepage `ByDate.Reverse` + pagination. Front matter `date` bị set = ngày báo gốc (2026-06-24) trong khi feed đang đầy bài 2026-07-14…16 → bài mới rơi **page 5**.

**Fix:**
- `date` / `lastmod` = ngày đăng KoreaWiki (thường là hôm nay)
- `source_date` = ngày bài gốc (hiển thị phụ, không dùng sort)
- Document in `mm.md` + comment in `layouts/index.html`

**Prevention:** mm Step 7 never uses only source date for `date` when it is older than current homepage window.

---

## Entry 020 — 2026-07-16: Enforce article-footer + faq on every post

**Rule:** Mọi bài (mm / tay / AI / import) **bắt buộc** có:
1. front matter `faq:` (≥2 `{q,a}`) → "Bài này trả lời"
2. shortcode `article-footer` → nguồn, links, copyright, FAQ UI

**Enforcement:** `scripts/qa.py` fails CI if missing. Auto-fix:
`python3 scripts/apply_article_footer.py --apply` (+ self-healing calls it).

**Docs:** `AGENTS.md` mandatory section, `archetypes/*`, `docs/article-footer.md`, `mm.md` rules.

---

## Entry 019 — 2026-07-16: "Bài này trả lời" jump links to FAQ

**Added:** Under article title, `answers-toc` lists FAQ questions from front matter `faq:`.

**Behavior:** Click → smooth scroll to `#faq-N` + open matching `<details>` in `article-footer`.

**Files:** `themes/koreawiki/layouts/partials/answers-toc.html`, `single.html`, `article-footer.html` (ids), `assets/js/main.js`, `_article-footer.scss`, i18n `answers_toc`.

**Authoring:** Put `faq:` in front matter (source of truth for both TOC and bottom FAQ).

---

## Entry 018 — 2026-07-16: Article footer macro (source / links / FAQ)

**Added:** Hugo shortcode `article-footer` for per-article end blocks (SEOMONEY-style UI).

**Sections:** external links · internal links · copyright/source · FAQ accordion.

**Usage:** YAML body inside `{{</* article-footer */>}}` … `{{</* /article-footer */>}}`.

**Files:** `themes/koreawiki/layouts/shortcodes/article-footer.html`, `assets/scss/_article-footer.scss`, `docs/article-footer.md`; mm workflow step 8b.

**Example:** `content/en/kpop/tours-soda-soda-japan-promotion-2026.md`

**Prevention:** Only cite real sources; never fabricate FAQ facts.

---

## Entry 017 — 2026-07-16: Self-host IBM Plex Sans site-wide

**Change:** Entire site font-family → **"IBM Plex Sans"** self-hosted (no Google Fonts).

**Assets:** `static/fonts/ibm-plex-sans/` + `assets/fonts/ibm-plex-sans/` (Regular/Medium/SemiBold/Bold + italics + variable).

**CSS:** `assets/scss/_fonts.scss` (@font-face, `font-display: swap`); `--font-sans` starts with `"IBM Plex Sans"` then system/Korean OS fallbacks for Hangul.

**Note:** IBM Plex Sans has limited Hangul — Korean glyphs fall back to Apple SD Gothic Neo / Malgun Gothic in the stack.

**Verify:** CSS contains `@font-face` + `IBM Plex Sans`; fonts served under `/fonts/ibm-plex-sans/`.

---

## Entry 016 — 2026-07-16: Native typography system (zero webfonts)

**Change:** Full typography redesign for premium Korean digital newspaper feel using **OS system fonts only**.

**Stack:**
- Default: `system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, …`
- Korean `:lang(ko)`: Apple SD Gothic Neo → Malgun Gothic → Noto Sans KR (local only)
- Mono: `ui-monospace, SFMono-Regular, Menlo, Consolas, …`

**Removed:** Pretendard / Noto Serif KR as primary; no Google Fonts / @font-face / external font URLs.

**Also:** fluid `clamp()` type scale, editorial nav (800 / uppercase / letter-spacing), article display title, blockquote treatment, body lh 1.75, measure ~72ch, taller nav.

**Files:** `assets/scss/_variables.scss`, `_typography.scss` (new), `_base.scss`, `_header.scss`, `_article.scss`, `_footer.scss`, `_buttons.scss`, `_hero.scss`, `_search.scss`, `main.scss`

**Verify:** Hugo build OK; CSS contains `system-ui`, no `Pretendard`/`googleapis`/`@font-face`.

**Prevention:** Never add `fonts.googleapis.com` or bundled webfonts without explicit product decision.

---

## Entry 015 — 2026-07-16: Self-Healing CI/CD system

**Added:** Automatic recovery when Build & Deploy or QA fails.

**Components:**
- `AGENTS.md` — agent recovery protocol (always consult scientist.md)
- `scripts/self_healing.py` — analyze logs, apply playbook fixes, validate, report
- `.github/workflows/self-healing.yml` — trigger on `workflow_run` failure
- `docs/self-healing.md` — architecture
- `reports/self-healing/` — logs + RECOVERY_REPORT.md

**Flow:** failure → download logs → fix (max 5 rounds) → validate → PR → merge only if green → normal deploy. Never force deploy while red.

**Known auto-fixes:** missing draft/keywords/author, markdown wrap, slugs, Hugo `try`→`fileExists` (0.126), glossary sync.

**Prevention:** Keep playbook entries in scientist.md; agents must run `self_healing.py recover` on any red CI.

---

## Entry 014 — 2026-07-16: Homepage restored to chronological news feed

**Change:** Removed per-category “latest in every section” homepage layout; restored classic newsroom feed.

**Removed:**
- `home/sections-grid.html` (latest post per category — caused clutter + duplicates)
- Homepage category blocks: photos / videos / opinion sections
- Unused wiki-era partials: featured-grid, latest-news, categories, popular-topics, featured-guides, learning-paths, newsletter, latest-articles, search-box

**Restored (`layouts/index.html`):**
1. Global sort: all `RegularPages` (except `type=page`) by `date` descending  
2. Hero on page 1 only (1 featured + up to 3 side — not repeated in the grid)  
3. Unified Latest / Older article grid  
4. Hugo pagination (`paginate = 12`)  
5. Exactly one card per article; no category loops

**Preserved:** Category list pages (`_default/list.html`), article single layout, SEO, search, RSS, URLs.

**Verify:** Homepage dates newest→oldest; no duplicate permalinks; `/kpop/` etc. still section-only; `hugo` + QA pass.

**Prevention:** Do not add per-section homepage queries; keep a single chronological paginator.

---

## Entry 013 — 2026-07-16: Translation Memory (TM) & Glossary system

**Added:** Permanent Korean → Vietnamese Translation Memory and public Glossary page.

**Storage (private repository asset):**
- `data/glossary/glossary.json` — canonical TM
- `data/glossary/glossary.md` / `.csv` / `.sqlite` — exports
- `data/glossary/README.md` — backup/restore & CLI docs

**Public:**
- Route `/glossary/` via `content/en/glossary/_index.md`
- Layout `themes/koreawiki/layouts/glossary/list.html`
- Client search `assets/js/glossary.js` (Hangul / Vietnamese / romanization, fuzzy, filters, pagination)
- Styles `assets/scss/_glossary.scss`
- Footer link **Glossary**

**CLI:** `scripts/glossary.py` — init, consult, lookup, add, upsert, edit, delete, merge, import/export, quality, sync, stats.

**mm integration:** `.opencode/commands/mm.md` now requires:
1. `glossary.py consult` before translate  
2. Extract + `upsert` + `sync` after article write  
3. Privacy check: no raw TM files under `public/`

**Privacy rules:**
- Raw TM stays under `data/glossary/` (json/md/csv/sqlite)
- Hugo `dataDir = "data-hugo"` (empty) so auto-loader never scans TM files
- Glossary layout uses `readFile` at build time; no raw DB under `public/`
- Do not put JSON/CSV/SQLite under `static/`
- `.gitignore` blocks accidental static/public TM dumps
- `.gitattributes` marks SQLite as binary

**Prevention:** Always run `python3 scripts/glossary.py sync` after TM changes; never put TM under `static/`; keep `dataDir = "data-hugo"`.

---

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

### Regenerate all slugs from titles
```bash
python3 scripts/slug.py
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
