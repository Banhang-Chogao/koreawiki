# AGENTS.md — KoreaWiki

## Project

Hugo static site on GitHub Pages — Korean entertainment & culture hub (K-Drama, K-Pop, celebrity news, lifestyle).
BaseURL: `https://banhang-chogao.github.io/koreawiki`
Theme: `themes/koreawiki/` (custom)

## Quick Commands

```bash
hugo server -D              # Dev server
hugo --minify --gc          # Production build
python3 scripts/qa.py       # Front matter validation
python3 scripts/seo.py      # SEO checks
python3 scripts/compress_images.py  # Generate WebP
```

## Build & Deploy

CI runs on push to `main` via `.github/workflows/build.yml`.

If deploy fails:
1. Check run logs: `gh run list --limit 3`
2. View failure: `gh run view <id> --log`
3. Common causes:
   - Missing `permissions:` block (need `pages: write`, `id-token: write`)
   - Missing `actions/upload-pages-artifact@v3` step
   - Missing `actions/configure-pages@v5` + `actions/deploy-pages@v4` steps
   - Node 20 deprecation warnings (safe to ignore)
   - `languageCode` deprecated → use `locale`

## Structure

```
content/       → Markdown by section (grammar, kdrama, kpop, news…)
assets/scss/   → Modular SCSS (variables, base, layout, components/)
themes/koreawiki/layouts/ → Hugo templates
scripts/       → Python: qa.py, seo.py, compress_images.py, etc.
static/        → Static assets (images, fonts, favicon)
```

## Rules

- System fonts only — no `@font-face`, no Google Fonts
- Images: always use `partial "cover-img"` for WebP + fallback
- No CSS transitions or animations (performance)
- All images: `loading="lazy"` (except hero: `loading="eager" fetchpriority="high"`)
- Cards: 16:9 aspect-ratio, 8px border-radius
- Navbar: Tibetan sky blue background (`#1565c0`), white text, uppercase bold
- Maintain all URLs, SEO, RSS, sitemap, search index
- Never break multilingual (en/ko/vi)
- Dark mode via `data-theme="dark"` on `<html>`
- No external JS libraries beyond Fuse.js (search)

## Deploy Fixes

| Symptom | Fix |
|---------|-----|
| "No artifacts named github-pages" | Check `actions/upload-pages-artifact` step exists |
| "Fetching artifact metadata failed" | Re-run workflow (transient GH API issue) |
| Build OK but deploy fails | Check permissions block has `pages: write` + `id-token: write` |
| `languageCode` deprecation warning | Change to `locale` in hugo.toml |
| WebP files not served | Ensure WebP is committed (not gitignored); `mm` writes WebP-only. `compress_images.py` only converts JPEG/PNG → WebP |

## Color Reference

- Navbar bg: `#1565c0` (light), `#0d47a1` (dark), hover: `#0d47a1` (light) / `#1565c0` (dark)
- Text: `#111827`
- Accent: `#dc2626`
- Primary: `#1e3a5f`

## Shortcuts

| Command | Description |
|---------|-------------|
| `./mm <url>` | Rewrite article → Vietnamese blog (SEO, Adsense, ≥2000 words) |
| `./mm <url> --section kdrama` | Specify content section |
| `./mm <url> -h` | Help |
| `python3 scripts/glossary.py add <kr> <vi>` | Add glossary entry |
| `python3 scripts/glossary.py search <q>` | Search TM |
| `python3 scripts/glossary.py merge` | Merge duplicates |
| `python3 scripts/glossary.py validate` | Quality check |
| `python3 scripts/glossary.py export --format csv` | Export to CSV |
| `python3 scripts/glossary.py import <file>` | Import entries |
| `python3 scripts/glossary.py stats` | TM statistics |

### mm — Vietnamese Blog Generator

See `shortcuts.md` for the complete agent-agnostic workflow.

**Requires:** `pip install requests Pillow`

### Glossary — Translation Memory

KoreaWiki's private Korean→Vietnamese TM lives in `data/glossary/glossary.json`.

| File | Purpose | Private |
|------|---------|---------|
| `data/glossary/glossary.json` | Master TM (all fields) | ✅ |
| `data/glossary/public.json` | Sanitized subset for Hugo | ❌ (read by Hugo) |
| `scripts/glossary_export/` | CSV/MD/SQLite exports | ✅ (gitignored) |

**Public glossary page:** `/glossary/` — searchable table with Hangul/Vi/En search, category filter, pagination, dark mode.

**Privacy:** Raw TM (frequency, source URLs, timestamps) stays in `glossary.json` — NOT exposed on public site. Hugo only reads `public.json` which contains sanitized fields.
