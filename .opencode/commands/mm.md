---
description: Publish a Korean news article to KoreaWiki with full workflow (fetch → translate → rewrite → fetch ALL source images → TM extract → Hugo build → QA → deploy).
agent: general
---

# mm — Publish Korean News Article

## Step 1 — Get Input

Prompt the user:

```
Paste a Korean news article URL hoặc dán nội dung text thô:
```

Accept **one** of the following:

| Input type | How to handle |
|---|---|
| **URL** | Fetch webpage, extract title/body/author/date/image |
| **Raw text** | Use the pasted text as article body. Ask user for: original newspaper name (tên báo gốc), publication date, author (nếu có) |

## Step 2 — Fetch & Extract

**If input is a URL:**
Fetch the webpage. Extract:

- title
- subtitle
- author
- publisher
- publish date
- updated date
- article body
- category
- tags
- canonical URL
- **all article image URL(s)** (required attempt — see Step 6; not just the lead photo)

Ignore ads, comments, recommendations, scripts, navigation.

**If input is raw text:**
- Use the pasted text as article body
- Use newspaper name provided by user as source
- Use provided date/author if available
- **Ask user for image URL(s)** if they have any; still try to locate the original article URL to fetch **all** images (Step 6)

## Step 3 — Consult Translation Memory (required)

**Before translating**, load preferred Korean → Vietnamese renderings:

```bash
python3 scripts/glossary.py consult
```

Optionally look up specific terms:

```bash
python3 scripts/glossary.py lookup <term>
```

**Rules:**
- Prefer existing TM translations whenever appropriate
- Maintain terminology consistency with prior articles
- Do not invent alternate spellings for names/orgs already in the TM

## Step 4–5 — Human rewrite (KO → VI) — **original contribution, full content**

**Goal:** A KoreaWiki article that reads as **written by a human editor**, not a
paste of machine translation — while **keeping every material fact** from the source.
This is intentional editorial contribution (structure, wording, framing), relevant
for originality (e.g. AdSense / thin-content policies): we **contribute**, we do not
mirror the source sentence-by-sentence.

### Must keep (no content loss)

- All **facts**: who / what / when / where / numbers / money / counts / deadlines
- **Names** (people, orgs, titles, places) — use TM spellings when present
- **Quotes** that carry news value (or paraphrase carefully **without** changing meaning)
- **Timeline** and causal claims present in the source
- Key **context** paragraphs (background, “why it matters”) — do not drop for brevity
- Source-specific details (program names, product lines, court/agency names, etc.)

**Forbidden “thinning”:** cutting half the article, dropping secondary but real facts,
or summarizing so hard that a reader loses information the source provided.

### Must change (human + objective voice)

- **Rewrite** into natural Vietnamese news prose: rhythm, paragraphing, connectors
- **Do not calque** Korean word order or stock press-release formulas
- **Objective** tone: no hype, no fan bias, no invented opinion
- **Original structure**: your own lead, subheads, and section order (as long as facts stay)
- Add light **editorial glue** only when it clarifies (e.g. one-line “đây là gì / vì sao
  đáng chú ý”) — still no new facts
- Prefer concrete verbs and short–medium sentences over stiff translationese

### Length bar (substance for AdSense-friendly pages)

**Reality check:** Google AdSense does **not** publish a hard “must be 2,000 words”
rule. What hurts is **thin / scraped / low-value** pages. Still, for KoreaWiki we set
a **clear length target** so every `mm` post is a real feature, not a 400-word gloss.

| Bar | Vietnamese body words* | When |
|-----|------------------------|------|
| **Hard minimum** | **≥ 2,000** | Ship blocker for `mm` (fail Step 10 if below) |
| **Healthy target** | **2,000–2,800** | Default aim after human rewrite + allowed expansion |
| **Stretch** | 2,800–3,500 | Long explainers only if still useful (not fluff) |

\*Count = body only (no YAML, no `article-footer` block). Measure with:

```bash
python3 scripts/wordcount_article.py content/en/<section>/<file>.md --min 2000
```

**How to reach ≥ 2,000 without padding spam** (allowed expansion — still objective):

1. **Keep every source fact** (baseline), then **expand for Vietnamese readers**:
   - Explain orgs/terms (who is this agency? what is Talk Channel / 경일?) in plain VI
   - “Bối cảnh” / “Vì sao đáng chú ý” grounded in the source story
   - Timeline / bullet recap of numbers already in the source
2. **Deeper FAQ** (5–8 items) — answers only from article facts
3. **Section “Điểm độc giả cần nhớ”** — structured recap, not new claims
4. **Internal links** with 1–3 sentences of relevance to older KoreaWiki posts
5. **Caption + short orientation** under photos (who/where) from known credits
6. Optional short **glossary box** of 4–8 terms used in the piece (KO + VI)

**Forbidden length hacks:**

- Repeating the same paragraph / synonym salad
- Keyword stuffing (“Hàn Quốc” every sentence)
- Invented stats, quotes, or drama not in the source
- Copy-paste English/Korean blobs to inflate count

If the Korean source is very short, you **still** hit 2,000 by **reader-value expansion**
above — never by fabrication. Prefer quality over empty bulk; if stuck under 2,000 after
honest expansion, keep expanding FAQ/context until the bar is met.

### Self-check before shipping body

1. Could a reader get the **same factual package** as the Korean source? If not → add back.
2. Does it still **sound translated line-by-line**? If yes → rewrite paragraphs again.
3. Any number/name you cannot find in the source? → **remove** (never invent).
4. Title/description are **new wording**, not a direct gloss of the original headline only.
5. **`wordcount_article.py --min 2000` passes.**

Apply TM terminology from Step 3.

Include: title, description, slug, keywords, categories, tags (+ clear headings in body).

## Step 6 — **ALL images** from original source (**MANDATORY effort**)

**Policy:** Every `mm` post **must try hard** to pull **every usable photo** from the
**original Korean article** (or a known original-page URL) — **not only one cover**.

| Role | How it ships |
|------|----------------|
| **Best / lead image** | Front matter `cover.image` + usually also first figure in body if useful |
| **Every other article photo** | Hosted under `static/images/…` and **embedded in the Markdown body** between related sections |
| Empty gallery | Last resort only after documented failed attempts |

**Do not** stop after the first successful download. **Do not** leave body photos only on the remote CDN.

### 6a — Locate candidates (try all that apply)

| Priority | Source | How |
|----------|--------|-----|
| 1 | User pasted a **URL** | Extract **all** images from that page |
| 2 | User pasted **raw text** only | Search original by title + author/publisher → open matching page |
| 3 | Syndicated / Daum / Naver copy | Follow to publisher canonical if present |
| 4 | User provides direct image URL(s) | Pass each as `--image` (repeatable) |

**Extraction targets (script collects all, then filters junk):**

1. `og:image` / `og:image:secure_url`
2. `twitter:image` / `twitter:image:src`
3. In-article `<img>` / `srcset` / lazy `data-src` / `data-original` (skip logos, icons, avatars, 1×1, share buttons, related-rail thumbs, YouTube sidebar)
4. `link rel="image_src"` / thumbnail meta
5. JSON-LD / inline script image URLs + CDN URL harvest in HTML

### 6b — Download **all** into the repo (required)

**Always use `--all` for `mm`** (JSON stdout lists every saved file):

```bash
# Preferred: every image on the original article page
python3 scripts/fetch_cover.py --page "https://SOURCE_ARTICLE_URL" --slug "your-article-slug" --all

# Extra direct URLs (merge + download all)
python3 scripts/fetch_cover.py --page "https://SOURCE" --slug "slug" --all \
  --image "https://CDN/.../extra1.jpg" --image "https://CDN/.../extra2.jpg"

# Inspect candidates only
python3 scripts/fetch_cover.py --page "https://..." --slug "your-article-slug" --dry-run
```

Stdout (with `--all`) is JSON:

```json
{
  "cover": "images/YYYY/MM/<slug>-cover.jpg",
  "count": 3,
  "images": [
    {"path": "images/YYYY/MM/<slug>-cover.jpg", "source_url": "...", "role": "cover"},
    {"path": "images/YYYY/MM/<slug>-01.jpg", "source_url": "...", "role": "body"},
    {"path": "images/YYYY/MM/<slug>-02.jpg", "source_url": "...", "role": "body"}
  ]
}
```

Rules:

- Save under `static/images/YYYY/MM/` (script default uses current UTC year/month)
- Filenames: `<slug>-cover.<ext>`, then `<slug>-01.<ext>`, `<slug>-02.<ext>`, …
- Paths in front matter / Markdown are **relative to `static/`** (no leading domain)
- Dedup by URL identity + content hash; skip tracking pixels / logos automatically
- If one URL 403s, continue with the rest — do not abort the whole gallery
- Fallback: `curl -L -A "Mozilla/5.0 ..." -o static/images/...` for any remaining known CDN URLs
- **Never** leave remote-only `https://...` in `cover.image` or body `![](https://...)`
- **Never fabricate** photo credits; attribute publisher / photographer only when known

### 6c — Wire front matter (cover) **and** body (gallery)

**Cover (required when Step 6 saved ≥1 image):**

```yaml
cover:
  image: images/YYYY/MM/<slug>-cover.jpg
  alt: "Mô tả ngắn, có tên người/sự kiện nếu biết"
  caption: "Nguồn ảnh: [Tên báo / phóng viên] — không bịa"
```

**Body (required for every additional `role: body` image — and recommended for cover too if it is a story photo):**

Place figures near the related paragraph/heading (not all dumped only at the end unless the source is a pure photo gallery):

```markdown
![Mô tả ảnh 1](/images/YYYY/MM/<slug>-cover.jpg)
*Nguồn ảnh: Dispatch / Plus M — không bịa*

## Tiêu đề mục tiếp

Nội dung…

![Mô tả ảnh 2](/images/YYYY/MM/<slug>-01.jpg)
*Chú thích ngắn nếu có trên bài gốc*
```

- Body Markdown: `![alt](/images/YYYY/MM/file.jpg)` **or** `![alt](images/YYYY/MM/file.jpg)` —
  both work via `themes/.../render-image.html` (`TrimPrefix "/" | relURL`) so paths honor
  `baseURL = …/koreawiki/`. Do **not** rely on browser-root `/images/…` alone.
- Keep caption factual (credit from source page only)
- If the source has **N** content photos, the published post should host **N** (minus true duplicates / junk)

### 6d — When you may ship without images

Only if **all** of the following are true:

1. No usable `og:image` / body image on the source (or source is text-only paywall)
2. Search for the original article found no matching page with photos
3. User did not provide any image URL
4. You report in the success summary: `images: none (reason: …)`

Do **not** skip Step 6 because “optional” or “can add later.”
Do **not** ship only the cover when the source page clearly has more article photos.

## Step 7 — Generate Hugo front matter

```yaml
---
title: ""
description: ""
# CRITICAL for homepage: date = when the post goes live on KoreaWiki (usually today).
# Do NOT use the source newspaper's old date alone — that buries the post under older feed pages.
date: 2026-07-16
lastmod: 2026-07-16
source_date: 2026-06-24   # optional: original publish date of the Korean source
slug: ""
categories: []
tags: []
draft: false
cover:
  image: images/2026/07/example-slug-cover.jpg   # required when Step 6 succeeded
  alt: "Mô tả ảnh cover"
  caption: "Ảnh: [nguồn gốc] — không bịa"
faq: []   # required
---
```

**Homepage / Latest News sort:** ordered by **first GitHub live time** — the commit that
*added* the content file on `main` (`scripts/git_first_live.py` → `data-hugo/git_first_live.json`).
Not newspaper `date`, and not last-touch (batch footer/FAQ edits must not reshuffle the feed).
`source_date` is attribution only. Still set `date`/`lastmod` to publish day for SEO and fallbacks.

## Step 8 — Generate Markdown article

Beautiful typography, SEO friendly, internal links, related articles placeholder, proper heading hierarchy, valid Markdown, Hugo compatible.

### Step 8b — FAQ front matter + article footer (required)

1. Add `faq:` list in YAML front matter (drives **"Bài này trả lời"** under the title
   and FAQ anchors `#faq-1` … at the bottom).
2. Append `article-footer` shortcode at the end of the body (source / links / FAQ).
   If `faq` is already in front matter, you may omit `faq:` inside the shortcode.

```markdown
{{</* article-footer */>}}
source: "Tên báo gốc"
source_url: "https://..."
copyright: >
  Ghi nguồn / bản quyền ngắn gọn. Không bịa.
external:
  - title: "..."
    url: "https://..."
internal:
  - title: "Bài liên quan trên KoreaWiki"
    url: "en/<section>/<slug>/"
faq:
  - q: "Câu hỏi thực tế từ bài?"
    a: "Trả lời ngắn, đúng facts đã có."
{{</* /article-footer */>}}
```

Rules: only real sources and links; FAQ must not invent facts. See `docs/article-footer.md`.

## Step 9 — Extract glossary entries → Update Translation Memory

From the source Korean text and the Vietnamese article, extract meaningful items:

- Korean word / phrase / sentence pattern
- Proper noun, organization, celebrity
- Movie title, drama title, location
- Slang, idiom, grammar pattern

For each item collect:

| Field | Required |
|-------|----------|
| korean | yes |
| vietnamese | yes |
| romanization | optional |
| pos | optional |
| meaning | optional |
| context | preferred |
| example | preferred |
| source_url | yes (article URL or empty for raw text) |
| category | preferred |
| tags | optional |

Write a JSON array to a temp file, then upsert (merges duplicates, bumps frequency, updates last_seen):

```bash
python3 scripts/glossary.py upsert --file /tmp/koreawiki-tm-extract.json
python3 scripts/glossary.py quality
python3 scripts/glossary.py sync
```

**Never create duplicate entries** — the CLI merges identical korean+vietnamese pairs.

Do **not** place raw JSON/CSV/SQLite under `static/` or `public/`. TM stays in `data/glossary/`.

## Step 10 — Run QA

Execute every validation from scientist.md:

- **Word count:** `python3 scripts/wordcount_article.py <this-post.md> --min 2000`
- Markdown lint
- Hugo build
- Internal links
- Front matter validation
- SEO validation
- Image validation
- Schema validation
- Broken links
- Accessibility checks
- Glossary quality (non-blocking unless critical): `python3 scripts/glossary.py quality`

Auto-fix every issue until all checks pass.

## Step 11 — Verify `hugo` build

Build succeeds with no warnings, no errors.

Confirm:

- Glossary page builds at `/glossary/`
- No `glossary.json` / `glossary.csv` / `glossary.sqlite` files appear under `public/` as downloadable assets

```bash
hugo --minify --gc
# privacy check (must print nothing / exit 0 with no hits)
! find public -iname '*glossary*.json' -o -iname '*glossary*.csv' -o -iname '*glossary*.sqlite' | grep -q .
```

## Step 12 — Commit

```
feat(news): add Korean news article - [title]
```

Include updated `data/glossary/*` and `content/en/glossary/_index.md` when TM changed.

## Step 13 — Push

Only if every QA check passes. If any validation fails, STOP, display errors, do not push.

## Pipeline summary

```
URL/text → fetch (+ ALL image candidates) → consult TM → translate → rewrite
  → fetch_cover.py --all (cover + every body photo) → Hugo article with gallery
  → extract TM → upsert glossary → sync public glossary page
  → scientist.md QA → Hugo build → deploy
```

No manual glossary work required on the happy path. **Full image gallery from source** is part of the happy path (not cover-only).

## Rules

- Never fabricate facts, dates, quotes, or image credits
- Preserve factual accuracy — **rewrite without content loss** (full fact package)
- **Human, objective Vietnamese** — active editorial contribution, not MT paste / calque
  (helps originality; still always attribute the Korean source)
- **Length:** body **≥ 2,000 words** (`scripts/wordcount_article.py --min 2000`); expand
  with reader value, never fluff or invented facts
- Prefer Translation Memory terminology for consistency
- Luôn dẫn nguồn ở cuối bài: nếu là URL → ghi dạng `Nguồn: [Tên báo] — [URL]`; nếu là text thô → ghi `Nguồn: [Tên báo gốc]`
- **Images:** **must attempt** `python3 scripts/fetch_cover.py --page URL --slug … --all`. Host **every** usable source photo under `static/images/…`. Set `cover` from the best image; **embed the rest in the body**. Remote-only image URLs are not allowed.
- **Never ship without** front-matter `faq:` (≥2) **and** `{{< article-footer >}}` (CI rejects). If unsure, run `python3 scripts/apply_article_footer.py --apply` then `python3 scripts/qa.py`
- Follow every rule in scientist.md and AGENTS.md
- Never push failing code
- Never bypass QA
- Never skip Hugo build
- Never publish without successful validation
- Never expose raw TM database files on the public site

Return a success summary: title, category, slug, **image status** (`cover` + list of body paths + source URLs, or `none` + reason), TM entries added/merged, QA result, build result, git commit hash, deployment status.
