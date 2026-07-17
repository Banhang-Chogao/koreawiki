# AGENTS.md — KoreaWiki

## Project

Hugo static site on GitHub Pages.
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
- Navbar: red background (`#e53e3e`), white text, uppercase bold
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
| WebP files not served | Run `compress_images.py` before `hugo` in CI |

## Color Reference

- Navbar bg: `#e53e3e` (light), `#991b1b` (dark)
- Text: `#111827`
- Accent: `#dc2626`
- Primary: `#1e3a5f`

## Shortcuts

| Command | Description |
|---------|-------------|
| `./mm <url>` | Rewrite article → Vietnamese blog (SEO, Adsense, ≥2000 words) |
| `./mm <url> --section kdrama` | Specify content section |
| `./mm <url> -h` | Help |

### mm — Vietnamese Blog Generator

Rewrites any article from any language into a Vietnamese Hugo blog post with:
- Full frontmatter (title, description, tags, categories, slug, date)
- SEO-optimized structure (H2 → H3 → FAQ)
- Google Adsense compliant formatting
- 2000+ word target
- Saves to `content/<section>/<slug>.md`

**Requires:** `pip install requests`
