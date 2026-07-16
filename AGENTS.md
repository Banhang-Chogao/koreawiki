# AGENTS.md — KoreaWiki coding agents

Instructions for automated agents (Grok, CI self-heal, mm publisher, etc.).

## Mission

Keep KoreaWiki **building, validating, and deploying green**. Prefer small,
deterministic fixes over large rewrites. Never fabricate news content.

## Always consult

1. **`scientist.md`** — historical bugs + proven fixes (primary recovery brain)
2. **This file (`AGENTS.md`)** — operating rules
3. **`docs/self-healing.md`** — CI self-heal architecture
4. **`.github/workflows/build.yml`** — what “green” means in CI

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
python3 scripts/qa.py
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

## mm publishing

Follow `.opencode/commands/mm.md`:

1. `python3 scripts/glossary.py consult` before translate  
2. Write article  
3. Extract TM → `glossary.py upsert` → `sync`  
4. Run scientist / self-heal validate  
5. Commit + push only when green  

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
