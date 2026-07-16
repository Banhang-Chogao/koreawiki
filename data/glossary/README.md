# KoreaWiki Translation Memory (TM)

Private Korean → Vietnamese linguistic asset for this repository.

## Purpose

Every time a Korean article is translated and published (including the `mm`
workflow), meaningful vocabulary, named entities, idioms, and patterns are
extracted into this Translation Memory. Future translations consult the TM so
terminology stays consistent across KoreaWiki.

## Files (private — not deployed as downloads)

| File | Role |
|------|------|
| `glossary.json` | **Canonical** store (source of truth) |
| `glossary.md` | Human-readable Markdown table |
| `glossary.csv` | Spreadsheet export |
| `glossary.sqlite` | Optional SQLite mirror |
| `meta.json` | Counts and category summary |

These files live under `data/glossary/`. Hugo is configured with
`dataDir = "data-hugo"` (empty) so it does **not** auto-load this folder.
The public Glossary page reads `glossary.json` via `readFile` at build time
only. Raw JSON/CSV/SQLite are never copied into `public/`.

## Public page

- Content: `content/en/glossary/_index.md`
- Route: `/glossary/`
- Footer link: **Glossary**
- Client search (Hangul / Vietnamese / English / romanization, fuzzy, filters)
- Only display fields are embedded in the HTML page (not a raw DB dump)

## CLI

```bash
# Initialize with seed entertainment terms
python3 scripts/glossary.py init

# Before translating — load preferred renderings
python3 scripts/glossary.py consult

# Lookup a term
python3 scripts/glossary.py lookup 배우

# Add / merge one entry (duplicates bump frequency + last_seen)
python3 scripts/glossary.py add \
  --korean 배우 --vietnamese "diễn viên" \
  --category noun --context "ngành giải trí" \
  --source "https://example.com/article"

# Bulk upsert extracted entries (JSON list)
python3 scripts/glossary.py upsert --file /tmp/tm-extract.json

# Quality checks (duplicates, conflicts, missing context/category)
python3 scripts/glossary.py quality

# Admin
python3 scripts/glossary.py merge
python3 scripts/glossary.py edit --id <id> --vietnamese "…"
python3 scripts/glossary.py delete --id <id>

# Export / import
python3 scripts/glossary.py export --format csv -o /tmp/tm.csv
python3 scripts/glossary.py export --format md  -o /tmp/tm.md
python3 scripts/glossary.py export --format json -o /tmp/tm.json
python3 scripts/glossary.py import --format csv --file /tmp/tm.csv

# Rewrite all formats + public _index.md
python3 scripts/glossary.py sync
python3 scripts/glossary.py stats
```

## Entry schema

| Field | Description |
|-------|-------------|
| `korean` | Source term / phrase / pattern |
| `vietnamese` | Preferred translation |
| `romanization` | Optional romaja |
| `pos` | Part of speech |
| `meaning` | Short gloss |
| `context` | Domain / usage context |
| `example` | Example sentence |
| `source_url` | Article URL first observed |
| `first_seen` | ISO date |
| `last_seen` | ISO date (updated on reuse) |
| `frequency` | Observation count |
| `tags` | Free tags |
| `category` | noun, proper_noun, organization, celebrity, movie, drama, location, slang, idiom, grammar, phrase, pattern, … |

Identical `korean` + `vietnamese` pairs are never duplicated: frequency
increases and `last_seen` is refreshed.

## Privacy strategy

1. **Keep raw data under `data/glossary/`** (repository asset, versioned in git).
2. **Hugo `dataDir = "data-hugo"`** (empty) so auto-loading never scans this
   folder (avoids build errors on `.md` / `.sqlite`, and avoids publishing
   raw files). The glossary layout uses `readFile` at build time only.
3. **Do not put JSON/CSV/SQLite under `static/`** — nothing downloadable.
4. **Public page** embeds a filtered JSON blob inside the HTML for client search
   only (korean, vietnamese, romanization, category, context, example, …).
5. Binary SQLite is marked in `.gitattributes` (see repo root).

## Backup

```bash
# Full TM backup (tar)
tar -czf koreawiki-tm-$(date +%Y%m%d).tar.gz data/glossary/

# Or copy JSON alone (canonical)
cp data/glossary/glossary.json ~/backups/glossary-$(date +%Y%m%d).json
```

Commit `data/glossary/` with article PRs so the TM grows with the site history.

## Restore

```bash
# From tarball
tar -xzf koreawiki-tm-YYYYMMDD.tar.gz

# From JSON export
python3 scripts/glossary.py import --format json --file ~/backups/glossary-YYYYMMDD.json --replace
python3 scripts/glossary.py sync
```

## mm workflow integration

When publishing with `mm`:

1. `python3 scripts/glossary.py consult` — prefer existing translations
2. Translate + rewrite article
3. Extract glossary entries → `python3 scripts/glossary.py upsert --file …`
4. `python3 scripts/glossary.py quality`
5. `python3 scripts/glossary.py sync`
6. scientist.md QA → Hugo build → deploy

No separate manual glossary maintenance is required for the happy path.
