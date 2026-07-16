# AGENTS.md — KoreaWiki coding agents

Instructions for automated agents (Grok, CI self-heal, mm publisher, etc.).

## Mission

Keep KoreaWiki **building, validating, and deploying green**. Prefer small,
deterministic fixes over large rewrites. Never fabricate news content.

## Mandatory article features (every post, every authoring path)

**No article may ship without these — whether written via `mm`, manual edit,
AI agent, import, or any other workflow.** CI (`scripts/qa.py`) will fail.

| Feature | Where | Purpose |
|---------|--------|---------|
| `faq:` list in front matter (≥2 items `{q,a}`) | YAML top of file | Renders **“Bài này trả lời”** under the title; anchors `#faq-1`… |
| `{{< article-footer >}}` … `{{< /article-footer >}}` | End of body | Copyright/source, internal links, external links, FAQ accordion |

### Authoring checklist (required)

1. Write body (facts only; no fabrication).  
2. Set `faq:` in front matter (2–4 Q&A grounded in the article).  
3. Close body with `article-footer` (source, links, copyright).  
4. Or batch-fill missing pieces:

```bash
python3 scripts/apply_article_footer.py --apply
python3 scripts/qa.py
```

Docs: `docs/article-footer.md` · archetype: `archetypes/default.md`

## Always consult

1. **`scientist.md`** — historical bugs + proven fixes (primary recovery brain)
2. **This file (`AGENTS.md`)** — operating rules
3. **`docs/self-healing.md`** — CI self-heal architecture
4. **`docs/article-footer.md`** — required end-of-article blocks
5. **`.github/workflows/build.yml`** — what “green” means in CI

## When CI / deploy fails

**Immediately enter recovery mode.** Do not ignore red workflows.

```
Failure detected
  → download workflow logs
  → python3 scripts/self_healing.py recover --log <log>
  → re-run validations until green (max 5 rounds)
  → commit fix on branch self-heal/… + open PR
  → merge only if checks green (never force deploy)
```

### Required commands

```bash
# Full automatic recovery (analyze + fix + validate + report)
python3 scripts/self_healing.py recover --log /path/to/workflow.log --round 1

# Steps individually
python3 scripts/self_healing.py analyze --log /path/to/workflow.log
python3 scripts/self_healing.py fix --log /path/to/workflow.log
python3 scripts/self_healing.py validate
```

### Validation suite (all must pass)

```bash
python3 scripts/qa.py   # includes faq + article-footer enforcement
python3 scripts/seo.py
python3 scripts/frontmatter_check.py
python3 scripts/markdown_lint.py
python3 scripts/check_links.py
python3 scripts/slug.py --check
python3 scripts/optimize_images.py
hugo --minify --gc          # CI uses Hugo 0.126.0 — avoid APIs newer than 0.126
python3 scripts/generate_schema.py
```

Or: `python3 scripts/self_healing.py validate`

### Reports

Every recovery writes under:

```
reports/self-healing/<timestamp>-<run_id>/
  workflow.log
  diagnostics.json
  root_cause.md
  patch_summary.json
  validation_summary.json
  deployment_summary.json
  RECOVERY_REPORT.md
  STATUS                 # recovered | failed
```

## Auto-fix categories (safe / deterministic)

| Category | Typical signal | Auto-fix |
|----------|----------------|----------|
| QA / front matter | Missing `draft` | Insert `draft: false` |
| SEO | Missing keywords / author | Derive keywords; default author |
| Markdown | Trailing spaces, lines >200 | Reformat (no content invention) |
| Slug | Invalid / missing slug | `scripts/slug.py` |
| Hugo 0.126 | `function "try" not defined` | Replace with `fileExists` + `readFile` |
| Glossary | TM desync | `scripts/glossary.py sync` |

If a fix is **not** in the playbook / `scientist.md`, stop after 5 rounds, write
`RECOVERY_REPORT.md`, and leave a PR or issue for humans. **Do not force deploy.**

## Safety rules

1. **Never fabricate** facts, quotes, dates, image credits, or article body text  
2. **Never delete** valid content to silence a linter  
3. **Never force** GitHub Pages deploy while validations are red  
4. **Preserve** git history — fix commits / PRs only  
5. **Max 5** self-heal rounds per failure chain (`[self-heal N/5]` in commit message)  
6. **Hugo CI = 0.126.0** — do not use `try`, or other post-0.126-only template funcs without bumping `HUGO_VERSION` in workflows  
7. **Private TM** stays under `data/glossary/` — never publish raw JSON/CSV/SQLite under `static/` or `public/`

## Publishing shortcuts (`mm` / `nn` / `th`)

| Command | When |
|---------|------|
| **`mm`** | Source article is **Korean** → Vietnamese — `.opencode/commands/mm.md` |
| **`nn`** | Source article is **English** (general news/blog **or ArchDaily**) → Vietnamese — `.opencode/commands/nn.md` |
| **`th`** | **Thailand market**: Thai **or** English source related to Thailand → Vietnamese — `.opencode/commands/th.md` |

All three require full image gallery fetch (`scripts/fetch_cover.py --all`), `faq` + `article-footer`, QA, and Hugo build before push.

**Images + baseURL (critical for `nn` ArchDaily galleries and all body galleries):**

- Host files under `static/images/YYYY/MM/`
- `cover.image`: `images/…` (no leading `/`) → templates use `relURL`
- Body: `![alt](/images/…)` → **must** use Markdown image syntax so  
  `themes/koreawiki/layouts/_default/_markup/render-image.html` emits  
  `/koreawiki/images/…` (site `baseURL`). Bare browser path `/images/…` **404s**.
- After `hugo`, built HTML must **not** contain `src="/images/` without `koreawiki`

Shared steps:

1. `python3 scripts/glossary.py consult` before translate  
2. **Human rewrite** into Vietnamese (KO→VI / EN→VI / TH→VI for `th`): objective,
   natural voice, **full facts retained** (no thin MT paste) — original editorial
   contribution  
3. **Body length ≥ 2,000 words** (`python3 scripts/wordcount_article.py <post.md> --min 2000`).
   Expand with real reader value (context, FAQ, term explainers), never empty padding.
   (AdSense has no official 2k rule; we use 2k as our substance floor.)  
4. Fetch **all** usable source images → `static/images/…` + body Markdown embeds  
5. Extract TM → `glossary.py upsert` → `sync` (lighter for pure EN / pure TH when no
   KO terms; **never invent Hangul** for Thai-only words)  
6. Run scientist / QA validate + baseURL image smoke test  
7. Commit + push only when green  

## Commit style

- `feat(scope): …` new capability  
- `fix(scope): …` bugfix  
- `fix(self-heal): … [self-heal N/5]` automated recovery only  

Author email for pushes that must pass GitHub privacy checks:

`292648126+Banhang-Chogao@users.noreply.github.com`

## After recovery

1. Merge PR when required checks are green  
2. Let **Build & Deploy** publish Pages  
3. Append outcome to `scientist.md` if not already auto-appended  
4. Confirm live site + Actions run = success  
