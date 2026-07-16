---
description: Publish a Korean news article to KoreaWiki with full workflow (fetch → translate → rewrite → Hugo build → QA → deploy).
agent: general
---

# mm — Publish Korean News Article

## Step 1 — Get URL

Prompt the user:

```
Paste a Korean news article URL:
```

Accept exactly one URL.

## Step 2 — Fetch & Extract

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

## Step 3 — Translate into Vietnamese

Preserve facts, names, numbers, timeline, quotations where appropriate. Do not add fabricated information.

## Step 4 — Rewrite in original Vietnamese journalistic style

Original wording, objective tone, professional news writing. Do not closely mirror source sentence structure. Add clear headings and subheadings.

Include: title, description, slug, keywords, summary, categories, tags.

## Step 5 — Handle image

If source provides a reusable featured image:
- Retrieve URL
- Download or reference per site terms
- Generate optimized WebP if appropriate
- Store under `static/images/yyyy/mm/`
- Include attribution: `Photo: [source]` or `Photo by [photographer]`
- Never fabricate attribution

If no reusable image: use no image.

## Step 6 — Generate Hugo front matter

```toml
+++
title=""
description=""
date=""
updated=""
slug=""
categories=[]
tags=[]
draft=false
cover=""
+++
```

## Step 7 — Generate Markdown article

Beautiful typography, SEO friendly, internal links, related articles placeholder, proper heading hierarchy, valid Markdown, Hugo compatible.

## Step 8 — Run QA

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

Auto-fix every issue until all checks pass.

## Step 9 — Verify `hugo` build

Build succeeds with no warnings, no errors.

## Step 10 — Commit

```
feat(news): add Korean news article - [title]
```

## Step 11 — Push

Only if every QA check passes. If any validation fails, STOP, display errors, do not push.

## Rules

- Never fabricate facts, dates, quotes, or image credits
- Preserve factual accuracy
- Produce original Vietnamese article, not a close translation
- Cite original article URL in Sources section
- Follow every rule in scientist.md
- Never push failing code
- Never bypass QA
- Never skip Hugo build
- Never publish without successful validation

Return a success summary: title, category, slug, image status, QA result, build result, git commit hash, deployment status.
