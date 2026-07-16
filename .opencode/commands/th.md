---
description: Publish a Thailand-related article to KoreaWiki (Thai or English source) — fetch → TH/EN→VI rewrite → fetch ALL source images → optional TM → Hugo build → QA → deploy. Parallel to mm/nn for Thai market.
agent: general
---

# th — Publish Thailand-Market Article (→ Vietnamese)

**Sibling of `mm` and `nn`.** Same pipeline and QA bar; **market is Thailand**.
Source language is **Thai** or **English** (any blog, news, feature, culture/travel/food/business piece **related to Thailand**).

| Command | Source language | Typical sources / market |
|---------|-----------------|--------------------------|
| **`mm`** | Korean | Dispatch, Hankyoreh, OhmyNews, Dailian, Korea Times, … |
| **`nn`** | English (general / ArchDaily) | Mainstream EN news, blogs, architecture |
| **`th`** | **Thai or English (Thailand)** | Bangkok Post, The Nation Thailand, Thai PBS, Khaosod English, Coconuts Bangkok, The Thaiger, Thai PBS World, Matichon, Thairath, Sanook, Pantip essays, EN blogs about Bangkok/Thailand, Thai tourism/culture/food features |

**When to use `th`:**

- Source is **Thai language**, or
- Source is **English** but clearly **about Thailand** (Bangkok, Chiang Mai, Phuket, Thai politics/economy/culture/food/travel, Thai brands, Thai entertainment, ASEAN angles centered on Thailand)

**Do not** use `th` for:

- Pure Korean sources → use **`mm`**
- General English with **no Thailand angle** (and not ArchDaily-style projects you already route via `nn`) → use **`nn`**
- Fabricated “Thailand” packaging of unrelated content

---

## Step 1 — Get Input

Prompt the user:

```
Paste a Thailand-related article URL (Thai or English) hoặc dán nội dung text thô (tiếng Thái / tiếng Anh về Thái Lan):
```

Accept **one** of the following:

| Input type | How to handle |
|---|---|
| **URL** | Fetch webpage, extract title/body/author/date/**all images** |
| **Raw text** | Use pasted text as body. Ask for: original site/publisher name, publication date, author (if any), language (Thai / English) |

**Detect source language early:**

| Signal | Treat as |
|--------|----------|
| Thai script (U+0E00–U+0E7F) in body/title | **TH → VI** |
| English body + Thailand topic | **EN → VI** (Thailand angle) |
| Mixed (EN with Thai names/quotes) | EN→VI for prose; keep Thai proper nouns accurate |

---

## Step 2 — Fetch & Extract

**If input is a URL:**
Fetch the webpage. Extract:

- title
- subtitle / standfirst
- author / byline
- publisher / site
- publish date
- updated date
- article body (full feature text for longform)
- category hints (news, culture, travel, food, business, entertainment, …)
- tags
- canonical URL
- **all article image URL(s)** (required — see Step 6)

Ignore ads, comments, recommendations, scripts, navigation, cookie banners, related-rail junk, LINE/share widgets.

**If input is raw text:**

- Use pasted text as article body
- Use publisher name from user as source
- Use provided date/author if available
- Ask for image URL(s) if any; still try to find the original page URL for full gallery fetch

**Common Thai / Thailand hosts (non-exhaustive):**

- English: `bangkokpost.com`, `nationthailand.com`, `thaipbsworld.com`, `khaosodenglish.com`, `coconuts.co`, `thethaiger.com`, `timothydemaster.com` / travel blogs, official tourism sites
- Thai: `thairath.co.th`, `matichon.co.th`, `sanook.com`, `bbc.com/thai`, `thai.news`, major broadcaster sites
- Prefer **publisher canonical** over AMP/syndication mirrors when both exist

---

## Step 3 — Consult Translation Memory (required)

Load preferred renderings (shared names/places/brands may already exist from Hallyu + prior runs):

```bash
python3 scripts/glossary.py consult
```

Optionally:

```bash
python3 scripts/glossary.py lookup <term>
```

**Rules:**

- Prefer existing TM for shared proper nouns (people, brands, places, K-culture terms when they appear in Thailand context)
- Keep Thai place names, brand names, and royal/official titles accurate (do not invent romanizations)
- Do not invent alternate spellings for names already in the TM
- TM store is **KO→VI** (`korean` field required by schema). For pure Thai terms with no Korean form, **do not invent Hangul** — skip upsert or only store when a known Korean equivalent is genuinely useful (Step 9)

---

## Step 4 — Translate Thai or English → Vietnamese

Preserve facts, names, numbers, timeline, quotations where appropriate. **Do not fabricate.**

### If source is Thai (TH → VI)

- Translate meaning into natural Vietnamese; do not calque Thai word order
- Keep established Thai proper nouns when that is the global standard; give Vietnamese gloss once if helpful (e.g. place names)
- Thai royal / formal titles: render carefully; do not invent ranks or protocol
- Transliteration: prefer common Vietnamese media usage (Bangkok, Chiang Mai, Phuket, …) over ad-hoc schemes

### If source is English about Thailand (EN → VI)

- Same bar as `nn`: natural Vietnamese, not English calque
- Keep established English/Thai romanized proper nouns when global standard; explain once in Vietnamese if helpful
- Apply TM terminology from Step 3 when relevant

---

## Step 5 — Rewrite in original Vietnamese journalistic / feature style

- Original wording, objective tone
- Clear headings and subheadings
- Lead with who / what / where (Thailand angle clear early)
- Include: title, description, slug (Vietnamese-friendly via `slug.py` conventions), keywords, categories, tags

**Section routing (guidance):**

| Source flavor | Prefer |
|---------------|--------|
| Breaking / hard news | `news` |
| Long feature / analysis | `feature` |
| Culture, lifestyle, design | `culture` |
| Food / restaurants | `food` |
| Travel / destinations | `travel` |
| Fashion / beauty | `fashion` |
| Entertainment (Thai drama, idols, film) | `movies`, `tv`, `artist`, or `culture` as fits |
| Opinion | `opinion` |

Always tag Thailand clearly, e.g. `thailand`, `bangkok`, topic tags — so the piece is discoverable even inside a Korea-named site.

---

## Step 6 — **ALL images** from original source (**MANDATORY effort**)

Same bar as `mm` / `nn`: **every usable photo**, not cover-only.

| Role | How it ships |
|------|----------------|
| **Best / lead image** | Front matter `cover.image` (+ first body figure if useful) |
| **Every other article photo** | Under `static/images/…` **and** embedded in Markdown near related text |
| Empty gallery | Last resort only after documented failed attempts |

### 6-baseURL — Image URL contract (shared with `mm`/`nn`; **required for `th`**)

Site deploys under **`baseURL = https://banhang-chogao.github.io/koreawiki/`**.

| Where | How to write | How it becomes valid HTML |
|-------|----------------|---------------------------|
| Front matter `cover.image` | `images/YYYY/MM/file.jpg` (**no** leading slash) | Template: `{{ cover.image \| relURL }}` → `/koreawiki/images/…` |
| Body Markdown figures | `![alt](/images/YYYY/MM/file.jpg)` **or** `![alt](images/YYYY/MM/file.jpg)` | Hook: `themes/koreawiki/layouts/_default/_markup/render-image.html` → `TrimPrefix "/" \| relURL` → `/koreawiki/images/…` |

**Never** assume bare `src="/images/…"` works — that path 404s on GitHub Pages project sites (missing `/koreawiki/`).

**Forbidden in body Markdown:**

- Remote-only embeds: `![](https://cdn…)` after you already host under `static/`
- Invented absolute hosts missing `/koreawiki/`

**Required after Hugo build (Step 11):** every gallery `<img src=` in built HTML contains `/koreawiki/images/` (or configured base path). Zero matches of `src="/images/` without `koreawiki`.

### 6a — Locate candidates

| Priority | Source | How |
|----------|--------|-----|
| 1 | User URL | Extract **all** images from that page |
| 2 | Raw text only | Search original by title + publisher → open matching page |
| 3 | Syndicated / AMP / mirror | Prefer publisher canonical |
| 4 | Thai portals (heavy chrome) | Prefer in-article figures over sidebar/related thumbs |
| 5 | User direct image URL(s) | `--image` (repeatable) |

**Extraction targets:** `og:image`, `twitter:image`, in-article `img`/`srcset`/`data-src`, `link rel=image_src`, JSON-LD, CDN harvest — skip logos, icons, avatars, 1×1, share widgets, related-rail junk.

### 6b — Download **all** into the repo

```bash
# Preferred
python3 scripts/fetch_cover.py --page "https://SOURCE_ARTICLE_URL" --slug "your-article-slug" --all

# Extra direct CDN URLs when the page is JS-heavy
python3 scripts/fetch_cover.py --page "https://SOURCE" --slug "slug" --all \
  --image "https://CDN/.../extra1.jpg" --image "https://CDN/.../extra2.jpg"

# Inspect only
python3 scripts/fetch_cover.py --page "https://..." --slug "your-article-slug" --dry-run
```

Stdout with `--all` is JSON: `cover`, `count`, `images[]` with `path` / `source_url` / `role`.

Rules (identical spirit to `mm`/`nn`):

- `static/images/YYYY/MM/` — `<slug>-cover.*`, `<slug>-01.*`, …
- Front matter paths relative to `static/` (e.g. `images/YYYY/MM/file.jpg`) — templates use `relURL`
- Body Markdown: `![alt](/images/YYYY/MM/file.jpg)` — **render-image hook** applies `baseURL`
- Dedup; continue on single 403; never remote-only `cover.image` or body `![](https://...)`
- Never fabricate photo credits
- If originals are huge, downscale for web (~1200–1600px long edge is enough)

### 6c — Wire cover + body gallery

```yaml
cover:
  image: images/YYYY/MM/<slug>-cover.jpg
  alt: "Mô tả ngắn — địa điểm / sự kiện Thái Lan"
  caption: "Ảnh: [photographer] / [publisher] — không bịa"
```

Body (every extra photo):

```markdown
![Mô tả ảnh](/images/YYYY/MM/<slug>-01.jpg)
*Nguồn ảnh: Bangkok Post — không bịa*
```

### 6d — Ship without images only if

1. No usable images on source / paywall text-only  
2. No matching original page with photos  
3. User provided no image URLs  
4. Summary reports `images: none (reason: …)`

---

## Step 7 — Generate Hugo front matter

```yaml
---
title: ""
description: ""
# CRITICAL: date / lastmod = KoreaWiki go-live day (usually today).
# source_date = original Thai/EN publish day (attribution only; not Latest News sort key).
date: 2026-07-16
lastmod: 2026-07-16
source_date: 2026-07-10
slug: ""
categories: []
tags: []
draft: false
cover:
  image: images/2026/07/example-slug-cover.jpg
  alt: "Mô tả ảnh cover"
  caption: "Ảnh: [nguồn] — không bịa"
faq: []   # required ≥2
---
```

**Homepage / Latest News:** sort by **first GitHub live** (`scripts/git_first_live.py` → `data-hugo/git_first_live.json`). `source_date` never sorts the feed.

After writing title, ensure slug matches site rules:

```bash
python3 scripts/slug.py --check
# or normalize if needed: python3 scripts/slug.py
```

Title length ≤120 characters (QA). Wrap body lines ≤200 chars (markdown lint).

---

## Step 8 — Generate Markdown article

Beautiful typography, SEO friendly, internal links, proper heading hierarchy, valid Markdown, Hugo compatible.

### Step 8b — FAQ + article-footer (required)

1. Front-matter `faq:` (≥2) — drives **"Bài này trả lời"**
2. Body ends with `article-footer` shortcode

```markdown
{{</* article-footer */>}}
source: "Bangkok Post / The Nation / Thairath / …"
source_url: "https://..."
copyright: >
  Bài **KoreaWiki**. Tham khảo nguồn công khai đã dẫn. Ảnh và bản quyền hình thuộc
  chủ sở hữu; dùng với mục đích thông tin. Không bịa nguồn.
external:
  - title: "Bài gốc (Thái / Anh)"
    url: "https://..."
internal:
  - title: "Bài liên quan trên KoreaWiki"
    url: "en/<section>/<slug>/"
{{</* /article-footer */>}}
```

**Public wording:** never on-page `viết lại` / `rewrite` / `Việt hóa dựa trên…`. Prefer
“Bài của KoreaWiki… tham khảo nguồn **công khai**… Ảnh © …”. See `docs/article-footer.md`.

FAQ must not invent facts.

---

## Step 9 — Extract glossary entries → Update TM

TM schema is **Korean → Vietnamese**. For `th` runs:

| Source mix | What to upsert |
|------------|----------------|
| Thai-only terms | Prefer **skip** (no invented Hangul). Do not force-fit Thai into `korean` field |
| EN Thailand terms with known Korean form | Optional: store **korean + vietnamese** when accurate and useful |
| Shared brands / K-culture / places already in TM | Bump via normal consult/upsert when they appear |
| Nothing meaningful for KO→VI | Skip upsert; still run quality if glossary was touched earlier |

```bash
# Only when you have real KO→VI entries
python3 scripts/glossary.py upsert --file /tmp/koreawiki-tm-th-extract.json
python3 scripts/glossary.py quality
python3 scripts/glossary.py sync
```

Never put raw glossary DB under `static/` or `public/`.

---

## Step 10 — Run QA

Same as `mm` / `nn` / scientist.md:

```bash
python3 scripts/qa.py
python3 scripts/seo.py
python3 scripts/frontmatter_check.py
python3 scripts/markdown_lint.py
python3 scripts/check_links.py
python3 scripts/slug.py --check
python3 scripts/optimize_images.py
```

Auto-fix until green. (`check_links` accepts `/images/…` static assets.)

---

## Step 11 — Verify Hugo build

```bash
python3 scripts/git_first_live.py
hugo --minify --gc
! find public -iname '*glossary*.json' -o -iname '*glossary*.csv' -o -iname '*glossary*.sqlite' | grep -q .
```

**Image baseURL smoke test (mandatory when the post embeds body photos):**

```bash
# After hugo — must exit 0. Bare src=/images/ (no /koreawiki/) is a ship blocker.
python3 -c "
from pathlib import Path
import re, sys
bad=[]
for html in Path('public').rglob('**/index.html'):
    t=html.read_text(encoding='utf-8', errors='ignore')
    if re.search(r'src=[\"\\']?/images/', t):
        bad.append(str(html))
if bad:
    print('FAIL: bare /images/ without baseURL in:'); [print(' ',b) for b in bad[:20]]
    sys.exit(1)
print('OK: no bare /images/ src (baseURL-safe for th/nn/mm galleries)')
"
```

If this fails, do **not** push — fix Markdown paths and ensure  
`themes/koreawiki/layouts/_default/_markup/render-image.html` is present.

---

## Step 12 — Commit

```
feat(travel): add Thailand-source article - [short VI title]
# or
feat(news): add Thailand-source article - [short VI title]
# or
feat(culture): add Thailand-source article - [short VI title]
```

Include `data/glossary/*` + `content/en/glossary/_index.md` when TM changed; include all new `static/images/…` files.

Author email for pushes that must pass GitHub privacy checks:

`292648126+Banhang-Chogao@users.noreply.github.com`

---

## Step 13 — Push

Only if every QA check passes. On failure: STOP, report errors, do not push.

---

## Pipeline summary

```
TH or EN (Thailand) URL/text → fetch (+ ALL images) → consult TM
  → TH/EN→VI rewrite → fetch_cover.py --all → Hugo post + body embeds
  → optional TM upsert (KO→VI only when real) → scientist QA → Hugo → commit → push
```

---

## Rules

- Never fabricate facts, dates, quotes, or image credits
- Preserve factual accuracy
- Produce **original Vietnamese** prose, not a close calque of Thai or English
- Prefer TM for shared terminology; **never invent Korean** for Thai-only terms
- Always attribute: `Nguồn: [Publisher] — [URL]`
- **Images:** mandatory `fetch_cover.py --page … --all` effort; host everything usable under `static/images/…`
- **baseURL:** body gallery **must** go through Markdown image syntax so `render-image.html` rewrites to `/koreawiki/images/…`. Cover uses front-matter + `relURL`. Run Step 11 smoke test before push.
- **Never ship without** `faq:` (≥2) **and** `{{< article-footer >}}`
- Follow scientist.md and AGENTS.md
- Never push failing code; never bypass QA; never skip Hugo build
- Never expose raw TM files on the public site
- **Do not use `th` for pure Korean sources** → use `mm`
- **Do not use `th` for general EN with no Thailand angle** → use `nn`

## Success summary (return to user)

- title, category, slug, URL path  
- source language (Thai / English) + publisher + URL  
- **images:** cover + body paths + count (or none + reason)  
- TM entries added/merged (or skipped)  
- QA / Hugo / commit hash / deploy status  

---

## Relation to `mm` / `nn`

| | `mm` | `nn` | `th` |
|--|------|------|-----|
| Market / filter | Korea (Korean news) | General EN (+ ArchDaily) | **Thailand** (Thai **or** EN about TH) |
| Source language | Korean | English | **Thai or English** |
| Translate | KO → VI | EN → VI | **TH→VI or EN→VI** |
| Images | Full gallery from source | Full gallery from source | Full gallery from source |
| FAQ + footer | Required | Required | Required |
| Homepage sort | First GitHub live | First GitHub live | First GitHub live |
| TM | Heavy KO↔VI extract | Lighter; proper nouns + domain | Light; only real KO→VI, never fake Hangul |
