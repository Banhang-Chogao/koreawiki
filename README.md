# KoreaWiki

A production-ready static knowledge wiki for learning Korean language and culture. Built with Hugo, Python, and GitHub Pages.

## Features

- **18 content sections**: Grammar, Vocabulary, TOPIK, Listening, Reading, Writing, Speaking, Culture, History, Society, Travel, Food, K-Drama, K-Pop, Hanja, News, Tools, Blog
- **Custom Hugo theme**: Typography-first, documentation-style original design
- **Dark mode**: Light, dark, and system-preference with persistence
- **Smart search**: Pagefind full-text engine, command palette (Ctrl/Cmd+K or `/`), fuzzy + multilingual, offline, no backend
- **Internationalization**: English, Korean (한국어), Vietnamese (Tiếng Việt)
- **Full SEO**: robots.txt, sitemap.xml, RSS, JSON Feed, OpenGraph, Twitter Cards, Schema.org (Article, Organization, Breadcrumb, SearchAction)
- **Performance**: Minified assets, lazy loading, responsive images, zero CLS design
- **Accessibility**: WCAG 2.2 AA compliant, keyboard navigation, skip links, semantic HTML
- **Python tooling**: QA, SEO validation, link checking, image validation, schema validation, markdown linting
- **GitHub Actions**: Automated build, QA, and Pages artifact deployment

## Tech Stack

- [Hugo Extended](https://gohugo.io/) v0.126+
- Python 3.12+
- SCSS (modular architecture)
- Vanilla JavaScript
- [Pagefind](https://pagefind.app/) (client-side full-text search)
- GitHub Pages + Actions

## Quick Start

```bash
git clone https://github.com/Banhang-Chogao/koreawiki.git
cd koreawiki

pip install pyyaml

# QA checks
python scripts/qa.py
python scripts/seo.py
python scripts/check_links.py

# Development server
hugo server -D
```

Visit `http://localhost:1313`.

## Project Structure

```
koreawiki/
├── archetypes/          # Content templates
├── assets/
│   ├── scss/           # Modular SCSS files
│   └── js/             # Vanilla JS + Pagefind smart search + glossary
├── config/             # Hugo configuration
├── content/            # Markdown content by section
├── data/glossary/      # Private Translation Memory (not deployed as files)
├── i18n/               # Translation strings (en, ko, vi)
├── layouts/            # Root-level templates (robots.txt, 404)
├── scripts/            # Python automation scripts
├── static/             # Static assets
└── themes/koreawiki/   # Original custom theme
```

### Python Scripts

| Script | Purpose |
|--------|---------|
| `qa.py` | Front matter validation |
| `seo.py` | SEO metadata checks |
| `publish.py` | Set draft=false |
| `slug.py` | Normalize URL slugs |
| `translate.py` | Export for translation (+ TM hints) |
| `glossary.py` | Translation Memory & Glossary manager |
| `self_healing.py` | CI failure recovery (scientist playbook) |
| `apply_article_footer.py` | Batch FAQ + article-footer for all posts |
| `optimize_images.py` | Validate image refs |
| `check_links.py` | Internal link checking |
| `generate_schema.py` | Schema.org validation |
| `markdown_lint.py` | Markdown formatting |
| `frontmatter_check.py` | Front matter correctness |

## Translation Memory & Glossary

KoreaWiki builds a private Korean → Vietnamese Translation Memory under
`data/glossary/` every time articles are published (including the `mm` command).

| Public | Private |
|--------|---------|
| Browseable page at `/glossary/` | Raw `glossary.json` / `.csv` / `.md` / `.sqlite` |
| Footer link **Glossary** | Repository asset only — not downloadable from the site |

```bash
python3 scripts/glossary.py init      # seed TM
python3 scripts/glossary.py consult   # before translating
python3 scripts/glossary.py upsert -f entries.json
python3 scripts/glossary.py quality
python3 scripts/glossary.py sync
```

Backup / restore procedures: see [`data/glossary/README.md`](data/glossary/README.md).

## Self-Healing CI/CD

When **Build & Deploy** or **QA** fails, GitHub Actions runs
**Self-Healing Recovery** automatically:

1. Download workflow logs  
2. Apply deterministic fixes from `scientist.md` / `AGENTS.md`  
3. Re-validate (Hugo, QA, SEO, links, …) — max 5 rounds  
4. Open a `self-heal/…` PR (auto-merge only if fully green)  
5. Never force-deploy while checks are red  

```bash
python3 scripts/self_healing.py recover --log /tmp/workflow.log
```

See [`docs/self-healing.md`](docs/self-healing.md) and [`AGENTS.md`](AGENTS.md).

## Deployment

Push to `main` triggers automatic GitHub Pages deployment:

1. **Build workflow** — runs QA, builds site, uploads artifact
2. **Deploy workflow** — deploys artifact to Pages

### Custom Domain

1. Add CNAME record pointing to `banhang-chogao.github.io`
2. Set `baseURL` in `config/_default/hugo.toml`
3. Enable custom domain in repository Pages settings

## Configuration

Main config: `config/_default/hugo.toml`

Key parameters: `baseURL`, `params.search`, `params.darkMode`, `params.seo`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push and open a Pull Request

All content must pass QA checks before merging.

## License

MIT
