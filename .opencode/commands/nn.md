---
description: Publish an English-source article to KoreaWiki (news or ArchDaily) — fetch → EN→VI rewrite → fetch ALL source images → TM extract → Hugo build → QA → deploy. Parallel to mm but for English sources.
agent: general
---

# nn — Publish English-Source Article (→ Vietnamese)

**Sibling of `mm`.** Same pipeline and QA bar; **source language is English** (general news, culture, tech, **or architecture/project pages on [ArchDaily](https://www.archdaily.com)**).

| Command | Source language | Typical sources |
|---------|-----------------|-----------------|
| **`mm`** | Korean | Dispatch, Hankyoreh, OhmyNews, Dailian, Korea Times, … |
| **`nn`** | **English** | Mainstream EN news, blogs, **ArchDaily project pages**, English culture/tech features |

Do **not** use `nn` for Korean-language sources — use `mm` instead.

---

## Step 1 — Get Input

Prompt the user:

```
Paste an English article URL (news / ArchDaily / blog) hoặc dán nội dung text thô tiếng Anh:
```

Accept **one** of the following:

| Input type | How to handle |
|---|---|
| **URL** | Fetch webpage, extract title/body/author/date/**all images** |
| **Raw text** | Use pasted text as body. Ask for: original site/publisher name, publication date, author (if any) |

**Special host — ArchDaily (`archdaily.com` / `archdaily.cn`):**

- Treat as **architecture project feature** (Culture / Feature, sometimes Travel).
- Extract: project title, office/architects, location, year, area, photographer, materials, design team, full project description, **entire photo gallery** (not cover-only).
- Prefer high-res CDN URLs (`images.adsttc.com` … `/large_jpg/` or `/newsletter/` over thumbs).
- Credit photographer + ArchDaily explicitly; never invent credits.
- JS-heavy pages: if `fetch_cover.py --page` only returns og/twitter, harvest gallery URLs from HTML / visible CDN paths and pass repeated `--image`, or `curl` them into `static/images/YYYY/MM/`.
- Resize oversized originals for web (e.g. max edge ~1400px) when files are multi‑MB each.

---

## Step 2 — Fetch & Extract

**If input is a URL:**
Fetch the webpage. Extract:

- title
- subtitle / standfirst
- author / curator
- publisher / site
- publish date
- updated date
- article body (full project text for ArchDaily)
- category hints (news, culture, architecture, …)
- tags
- canonical URL
- **all article image URL(s)** (required — see Step 6)

Ignore ads, comments, recommendations, scripts, navigation, cookie banners, “related projects” side rails when they are pure chrome.

**If input is raw text:**

- Use pasted text as article body
- Use publisher name from user as source
- Use provided date/author if available
- Ask for image URL(s) if any; still try to find the original page URL for full gallery fetch

---

## Step 3 — Consult Translation Memory (required)

Load preferred renderings (names/orgs often already in TM from Hallyu + prior `nn`/`mm` runs):

```bash
python3 scripts/glossary.py consult
```

Optionally:

```bash
python3 scripts/glossary.py lookup <term>
```

**Rules:**

- Prefer existing TM for shared proper nouns (brands, people, places, film/K-pop terms when they appear)
- For architecture: keep office names, project names, and place names accurate (e.g. Localworks, Kijonjo, Will Boase)
- Do not invent alternate spellings for names already in the TM

---

## Step 4–5 — Human rewrite (EN → VI) — **original contribution, full content**

**Goal:** A KoreaWiki piece that reads as **written by a human editor** in Vietnamese —
not a machine-translation dump — while **retaining the full factual content** of the
English source. That active rewrite (structure, wording, sectioning) is intentional
**editorial contribution** (relevant for originality / AdSense thin-content risk):
we **contribute**, we do not republish a gloss of the source.

### Must keep (no content loss)

- All **facts**: who / what / when / where / m² / year / budget / counts / deadlines
- **Names** (people, offices, projects, places, manufacturers) — global EN names OK;
  explain once in VI if helpful
- **Quotes** or architect-provided text claims that carry value (paraphrase only if
  meaning stays identical)
- Specs tables / program lists (Church, rooms, materials…) — do not silently drop rows
- ArchDaily: location, office, photographer, year, area, contractors, key design intent
  from the provided project text

**Forbidden “thinning”:** cover + 2 paragraphs while the source had a full brief;
dropping materials, team, or program “to keep it short.”

### Must change (human + objective voice)

- Natural Vietnamese feature/news prose — **do not calque** English syntax
- **Objective** framing: no marketing hype beyond what the source states
- **Your own** lead and subheads; reorder for clarity if needed
- Light editorial framing (“đây là gì / bối cảnh”) without new facts
- For ArchDaily: lead with **where / who / what**, then program → materials/context →
  embed photos next to related sections

### Self-check before shipping body

1. Same **fact package** as the English source? If thinner → restore missing facts.
2. Still reads like EN→VI line mirror? → rewrite again in human Vietnamese.
3. Any claim not in the source? → **delete** (never invent).
4. Title/description are **original wording**, not only a literal headline clone.

Apply TM terminology from Step 3 when relevant.

Include: title, description, slug (`slug.py`), keywords, categories, tags.

**Section routing (guidance):**

| Source flavor | Prefer |
|---------------|--------|
| General EN news | `news`, `feature`, or topical section |
| Architecture / ArchDaily | `culture` (+ Feature); tags: architecture, materials, country, office |
| Photo-heavy project | still one content file with body gallery — not a separate photos-only dump |

---

## Step 6 — **ALL images** from original source (**MANDATORY effort**)

Same bar as `mm`: **every usable photo**, not cover-only.

| Role | How it ships |
|------|----------------|
| **Best / lead image** | Front matter `cover.image` (+ first body figure if useful) |
| **Every other article photo** | Under `static/images/…` **and** embedded in Markdown near related text |
| Empty gallery | Last resort only after documented failed attempts |

### 6-baseURL — Image URL contract (shared with `mm`; **required for `nn`**)

Site deploys under **`baseURL = https://banhang-chogao.github.io/koreawiki/`**.

| Where | How to write | How it becomes valid HTML |
|-------|----------------|---------------------------|
| Front matter `cover.image` | `images/YYYY/MM/file.jpg` (**no** leading slash) | Template: `{{ cover.image \| relURL }}` → `/koreawiki/images/…` |
| Body Markdown figures | `![alt](/images/YYYY/MM/file.jpg)` **or** `![alt](images/YYYY/MM/file.jpg)` | Hook: `themes/koreawiki/layouts/_default/_markup/render-image.html` → `TrimPrefix "/" \| relURL` → `/koreawiki/images/…` |

**Never** assume `src="/images/…"` works in the browser — that path 404s on GitHub Pages project sites (missing `/koreawiki/`). The render hook is what makes body galleries work for **every** `nn` (and `mm`) post.

**Forbidden in body Markdown:**

- Remote-only embeds: `![](https://cdn…)` after you already host under `static/`
- Invented absolute hosts: `https://banhang-chogao.github.io/images/…` (wrong — still missing `/koreawiki/` if mis-copied)

**Required after Hugo build (Step 11):** open the built article HTML under `public/` and confirm **every** gallery `<img src=` contains `/koreawiki/images/` (or the configured base path). Zero matches of `src="/images/` without `koreawiki`.

### 6a — Locate candidates

| Priority | Source | How |
|----------|--------|-----|
| 1 | User URL | Extract **all** images from that page |
| 2 | Raw text only | Search original by title + publisher → open matching page |
| 3 | Syndicated / AMP / mirror | Prefer publisher canonical |
| 4 | ArchDaily gallery | Harvest `images.adsttc.com` project gallery (large/medium), not only `og:image` |
| 5 | User direct image URL(s) | `--image` (repeatable) |

**Extraction targets:** `og:image`, `twitter:image`, in-article `img`/`srcset`/`data-src`, `link rel=image_src`, JSON-LD, CDN harvest — skip logos, icons, avatars, 1×1, share widgets, related-rail junk.

### 6b — Download **all** into the repo

```bash
# Preferred
python3 scripts/fetch_cover.py --page "https://SOURCE_ARTICLE_URL" --slug "your-article-slug" --all

# ArchDaily / stubborn CDN: add explicit gallery URLs
python3 scripts/fetch_cover.py --page "https://www.archdaily.com/...." --slug "slug" --all \
  --image "https://images.adsttc.com/.../large_jpg/....jpg" \
  --image "https://images.adsttc.com/.../large_jpg/....jpg"

# Inspect only
python3 scripts/fetch_cover.py --page "https://..." --slug "your-article-slug" --dry-run
```

Stdout with `--all` is JSON: `cover`, `count`, `images[]` with `path` / `source_url` / `role`.

Rules (identical spirit to `mm`):

- `static/images/YYYY/MM/` — `<slug>-cover.*`, `<slug>-01.*`, …
- Front matter paths relative to `static/` (e.g. `images/YYYY/MM/file.jpg`) — templates use `relURL`
- Body Markdown: `![alt](/images/YYYY/MM/file.jpg)` — **render-image hook** applies
  `TrimPrefix "/" | relURL` so `baseURL` (`/koreawiki/`) is honored. Without the hook,
  bare `/images/…` 404s on GitHub Pages project sites.
- Dedup; continue on single 403; never remote-only `cover.image` or body `![](https://...)`
- Never fabricate photo credits
- If originals are huge, downscale for web (keep aspect; ~1200–1600px long edge is enough)

### 6c — Wire cover + body gallery

```yaml
cover:
  image: images/YYYY/MM/<slug>-cover.jpg
  alt: "Mô tả ngắn — công trình / địa điểm / sự kiện"
  caption: "Ảnh: [photographer] / [publisher] — không bịa"
```

Body (every extra photo):

```markdown
![Mô tả ảnh](/images/YYYY/MM/<slug>-01.jpg)
*Nguồn ảnh: Will Boase / ArchDaily — không bịa*
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
# source_date = original English publish day (attribution only; not Latest News sort key).
date: 2026-07-16
lastmod: 2026-07-16
source_date: 2026-04-30
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
source: "ArchDaily / New York Times / …"
source_url: "https://..."
copyright: >
  Tóm lược / Việt hóa bởi KoreaWiki. Ảnh và nội dung gốc thuộc chủ sở hữu tương ứng.
  Không bịa nguồn.
external:
  - title: "Original English article"
    url: "https://..."
internal:
  - title: "Bài liên quan trên KoreaWiki"
    url: "en/<section>/<slug>/"
{{</* /article-footer */>}}
```

See `docs/article-footer.md`. FAQ must not invent facts.

---

## Step 9 — Extract glossary entries → Update TM

From **English source + Vietnamese article**, extract useful items:

- Proper nouns (people, offices, places, buildings)
- Architecture / domain terms when they help future consistency
- When a Korean equivalent is known and useful, store **korean + vietnamese** (TM is KO→VI); otherwise skip pure EN-only jargon that has no KO form
- Do **not** invent Korean spellings

If nothing meaningful for TM, skip upsert but still run quality if you touched glossary earlier.

```bash
python3 scripts/glossary.py upsert --file /tmp/koreawiki-tm-nn-extract.json
python3 scripts/glossary.py quality
python3 scripts/glossary.py sync
```

Never put raw glossary DB under `static/` or `public/`.

---

## Step 10 — Run QA

Same as `mm` / scientist.md:

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
print('OK: no bare /images/ src (baseURL-safe for nn/mm galleries)')
"
```

If this fails, do **not** push — fix Markdown paths and ensure  
`themes/koreawiki/layouts/_default/_markup/render-image.html` is present.

---

## Step 12 — Commit

```
feat(culture): add [short EN project/news title] from ArchDaily
# or
feat(news): add English-source article - [short VI title]
```

Include `data/glossary/*` + `content/en/glossary/_index.md` when TM changed; include all new `static/images/…` files.

---

## Step 13 — Push

Only if every QA check passes. On failure: STOP, report errors, do not push.

---

## Pipeline summary

```
EN URL/text → fetch (+ ALL images) → consult TM → EN→VI rewrite
  → fetch_cover.py --all (ArchDaily: full gallery) → Hugo post + body embeds
  → optional TM upsert → scientist QA → Hugo → commit → push
```

---

## Rules

- Never fabricate facts, dates, quotes, or image credits
- Preserve factual accuracy — **rewrite without content loss** (full fact package)
- **Human, objective Vietnamese** — active editorial contribution, not MT paste / calque
  (originality / AdSense-friendly; always attribute the English source)
- Prefer TM for shared terminology
- Always attribute: `Nguồn: [Publisher] — [URL]`
- **Images:** mandatory `fetch_cover.py --page … --all` effort; host everything usable under `static/images/…`
- **baseURL:** body gallery **must** go through Markdown image syntax so `render-image.html` rewrites to `/koreawiki/images/…`. Cover uses front-matter + `relURL`. Run Step 11 smoke test before push.
- **Never ship without** `faq:` (≥2) **and** `{{< article-footer >}}`
- Follow scientist.md and AGENTS.md
- Never push failing code; never bypass QA; never skip Hugo build
- Never expose raw TM files on the public site
- **Do not use `nn` for Korean sources** → use `mm`

## Success summary (return to user)

- title, category, slug, URL path  
- source (publisher + URL)  
- **images:** cover + body paths + count (or none + reason)  
- TM entries added/merged  
- QA / Hugo / commit hash / deploy status  

---

## Relation to `mm`

| | `mm` | `nn` |
|--|------|------|
| Source | Korean | **English** (+ ArchDaily) |
| Translate | KO → VI | **EN → VI** |
| Images | Full gallery from source | Full gallery from source |
| FAQ + footer | Required | Required |
| Homepage sort | First GitHub live | First GitHub live |
| TM | Heavy KO↔VI extract | Lighter; proper nouns + domain |
