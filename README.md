# KoreaWiki

A production-ready static knowledge wiki for learning Korean language and culture. Built with Hugo, Python, and GitHub Pages.

## Features

- **18 content sections**: Grammar, Vocabulary, TOPIK, Listening, Reading, Writing, Speaking, Culture, History, Society, Travel, Food, K-Drama, K-Pop, Hanja, News, Tools, Blog
- **Custom Hugo theme**: Typography-first, documentation-style original design
- **Dark mode**: Light, dark, and system-preference with persistence
- **Offline search**: Fuse.js powered, instant, no backend (Ctrl+K)
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
