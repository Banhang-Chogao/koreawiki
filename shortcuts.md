# Shortcuts — KoreaWiki

## `mm` — Vietnamese Blog Generator

Publish a Korean news article to the KoreaWiki blog with a single command.

### Trigger

```
mm
```

### Workflow

#### Step 1 — URL Input

Prompt the user:

```
Paste a Korean news article URL:
```

Accept only one URL.

#### Step 2 — Fetch & Extract

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

Ignore:

- ads
- comments
- recommendations
- scripts
- navigation

#### Step 3 — Translate

Translate the article into Vietnamese.

Requirements:

- Preserve facts, names, numbers, timeline.
- Preserve quotations where appropriate.
- Do not add fabricated information.

#### Step 4 — Rewrite

Rewrite the translated article in an original Vietnamese journalistic style.

Requirements:

- Original wording, objective tone, professional news writing.
- Do not closely mirror the source's sentence structure.
- Add clear headings and subheadings.
- Produce a complete SEO-friendly article.

Include:

- title
- description
- slug
- keywords
- summary
- categories
- tags

#### Step 5 — Image

If the source page provides an article image that is licensed or otherwise permissible to reference:

- retrieve the featured image URL
- download or reference it according to the site's terms
- generate an optimized WebP version if appropriate
- store it under `static/images/yyyy/mm/`

Generate proper attribution. Example:

```
Image credit:
Photo: Dispatch
Source: https://example.com/article
```

If photographer information exists, include `Photo by ...`.

If no reusable image is available, use no image.

Never fabricate attribution.

#### Step 6 — Front Matter

Generate Hugo front matter:

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

#### Step 7 — Markdown Article

Generate the Markdown article.

Requirements:

- Beautiful typography
- SEO friendly
- Internal links
- Related articles placeholder
- Proper heading hierarchy
- Valid Markdown
- Hugo compatible

#### Step 8 — QA

Execute all validations:

| Check | Command |
|-------|---------|
| Markdown lint | `python3 scripts/markdown_lint.py` |
| Hugo build | `hugo --minify --gc` |
| Front matter validation | `python3 scripts/qa.py` |
| SEO validation | `python3 scripts/seo.py` |
| Image validation | `python3 scripts/optimize_images.py` |
| Schema validation | `python3 scripts/generate_schema.py` |
| Broken links | `python3 scripts/check_links.py` |
| Slug validation | `python3 scripts/slug.py --check` |
| WebP generation | `python3 scripts/compress_images.py` |
| Accessibility | Check alt texts, heading hierarchy, contrast |

Automatically fix every issue until all checks pass.

#### Step 9 — Verify Build

```bash
hugo --minify --gc
```

Build must succeed with no warnings and no errors.

#### Step 10 — Commit

```bash
git add -A
git commit -m "feat(news): <short description>"
```

#### Step 11 — Push

```bash
git push origin main
```

Only push if every QA check passes successfully.

If any validation fails, STOP. Display the errors. Do not push.

### Rules

- Never fabricate facts, dates, quotes, or image credits.
- Preserve factual accuracy.
- Produce an original Vietnamese article, not a close translation.
- Cite the original article URL in the Sources section.
- Never push failing code.
- Never bypass QA.
- Never skip Hugo build.
- Never publish without a successful validation pipeline.

### Return

Return a success summary including:

- title
- category
- slug
- image status
- QA result
- build result
- git commit hash
- deployment status
