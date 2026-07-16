---
description: Publish a Korean news article to KoreaWiki with full workflow (fetch → translate → rewrite → TM extract → Hugo build → QA → deploy).
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

Ignore ads, comments, recommendations, scripts, navigation.

**If input is raw text:**
- Use the pasted text as article body
- Use newspaper name provided by user as source
- Use provided date/author if available

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

## Step 4 — Translate into Vietnamese

Preserve facts, names, numbers, timeline, quotations where appropriate. Do not add fabricated information.

Apply TM terminology from Step 3.

## Step 5 — Rewrite in original Vietnamese journalistic style

Original wording, objective tone, professional news writing. Do not closely mirror source sentence structure. Add clear headings and subheadings.

Include: title, description, slug, keywords, summary, categories, tags.

## Step 6 — Handle image

If source provides a reusable featured image:
- Retrieve URL
- Download or reference per site terms
- Generate optimized WebP if appropriate
- Store under `static/images/yyyy/mm/`
- Include attribution: `Photo: [source]` or `Photo by [photographer]`
- Never fabricate attribution

If no reusable image: use no image.

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
  image: ""
  alt: ""
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
URL/text → fetch → consult TM → translate → rewrite → image
  → Hugo article → extract TM → upsert glossary → sync public glossary page
  → scientist.md QA → Hugo build → deploy
```

No manual glossary work required on the happy path.

## Rules

- Never fabricate facts, dates, quotes, or image credits
- Preserve factual accuracy
- Produce original Vietnamese article, not a close translation
- Prefer Translation Memory terminology for consistency
- Luôn dẫn nguồn ở cuối bài: nếu là URL → ghi dạng `Nguồn: [Tên báo] — [URL]`; nếu là text thô → ghi `Nguồn: [Tên báo gốc]`
- **Never ship without** front-matter `faq:` (≥2) **and** `{{< article-footer >}}` (CI rejects). If unsure, run `python3 scripts/apply_article_footer.py --apply` then `python3 scripts/qa.py`
- Follow every rule in scientist.md and AGENTS.md
- Never push failing code
- Never bypass QA
- Never skip Hugo build
- Never publish without successful validation
- Never expose raw TM database files on the public site

Return a success summary: title, category, slug, image status, TM entries added/merged, QA result, build result, git commit hash, deployment status.
