# KoreaWiki

A static knowledge wiki for learning Korean language and culture. Built with Hugo, Python, and GitHub Pages.

## Sections

8 main navigation sections — content lives under `content/`:

| Section | Description | Status |
|---------|-------------|--------|
| Grammar | Korean sentence structure, particles, tenses | Active |
| Vocabulary | Essential words, phrases, thematic lists | Active |
| TOPIK | Test preparation guides and practice | Active |
| Culture | Customs, honorifics, traditions | Active |
| Travel | Travel phrases, location guides | Active |
| Food | Korean cuisine, dishes, food culture | Active |
| K-Drama | Drama reviews, recommendations | Placeholder |
| History | Language and cultural history | Active |

Additional content directories not in main nav: Blog, Hanja, K-Pop, Listening, News, Reading, Society, Speaking, Tools, Writing.

## Tech Stack

- [Hugo Extended](https://gohugo.io/) v0.126+
- Python 3.12+
- SCSS (modular architecture)
- Vanilla JavaScript
- [Fuse.js](https://fusejs.io/)
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
│   └── js/             # Vanilla JS + Fuse.js
├── config/             # Hugo configuration
├── content/            # Markdown content by section
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
| `translate.py` | Export for translation |
| `optimize_images.py` | Validate image refs |
| `check_links.py` | Internal link checking |
| `generate_schema.py` | Schema.org validation |
| `markdown_lint.py` | Markdown formatting |
| `frontmatter_check.py` | Front matter correctness |

## Features

- **Multilingual**: English, Korean (한국어), Vietnamese (Tiếng Việt)
- **SEO**: robots.txt, sitemap.xml, RSS, JSON Feed, OpenGraph, Twitter Cards, Schema.org
- **Search**: Fuse.js powered, instant (Ctrl+K)
- **Dark mode**: Light, dark, system-preference with persistence
- **Performance**: Minified assets, lazy loading, zero CLS design
- **Python tooling**: QA, SEO, link/image/schema validation, markdown linting
- **CI/CD**: Automated build, QA, and deployment via GitHub Actions

## Deployment

Push to `main` triggers automatic GitHub Pages deployment:

1. Build workflow runs QA, builds site, uploads artifact
2. Deploys artifact to Pages

## License

MIT
