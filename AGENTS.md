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

### 1 change = 1 deploy

- Mỗi commit deploy độc lập — không gộp nhiều thay đổi vào 1 deploy
- **Self-heal** (auto-fix linter/slug) tự commit + push, tạo 1 workflow riêng
- Nếu self-heal có sửa file → workflow hiện tại **bỏ qua deploy** (set `fixed=true`), fix commit sẽ trigger workflow mới → QA + deploy sạch
- Nếu không có gì để fix → QA + deploy bình thường
- Tuyệt đối KHÔNG dùng `[skip ci]` trong self-heal commit để đảm bảo fix commit luôn được deploy

### CI pipeline flow

```
push → Self-heal (fix linter/slug) → nếu có thay đổi:
  ├─ commit + push (trigger workflow mới)
  └─ skip deploy (fixed=true)
→ nếu không thay đổi:
  ├─ QA → Validate images → WebP → Build → Pagefind → Schema
  └─ Deploy to GitHub Pages
```

### If deploy fails

1. Check run logs: `gh run list --limit 3`
2. View failure: `gh run view <id> --log`
3. Common causes:
   - Missing `permissions:` block (need `pages: write`, `id-token: write`)
   - Missing `actions/upload-pages-artifact@v3` step
   - Missing `actions/configure-pages@v5` + `actions/deploy-pages@v4` steps
   - Node 20 deprecation warnings (safe to ignore)
   - `languageCode` deprecated → use `locale`
   - **QA fail do slug mismatch** → `python scripts/slug.py` tự fix, self-heal push commit mới
   - **QA fail do long lines** → `markdown_lint.py --fix` tự wrap, self-heal push commit mới
   - **Workflow fail dính chùm** → kiểm tra self-heal có set `fixed=true` không; nếu có thì deploy của commit đó đã bị skip, fix commit đã trigger workflow riêng

## Structure

```
content/       → Markdown by section (grammar, kdrama, kpop, news…)
assets/scss/   → Modular SCSS (variables, base, layout, components/)
themes/koreawiki/layouts/ → Hugo templates
scripts/       → Python: qa.py, seo.py, compress_images.py, etc.
static/        → Static assets (images, fonts, favicon)
```

## Agent Rules (Auto-Deploy)

- Viết/modify bài xong → commit + push thẳng lên `main` **ngay lập tức**, không đợi duyệt
- Trước khi commit: chạy `python3 scripts/pre_deploy.py` đảm bảo không lỗi
- ML Learning Engine luôn chạy đầu tiên — phải xác nhận dòng `✔ ML LEARNED: X commits, Y patterns, Z new checks` trên terminal trước khi deploy
- Nếu `pre_deploy.py` báo lỗi → fix triệt để, chạy lại đến khi pass mới push
- Sau build (nếu có Hugo change): chạy `python3 scripts/pre_deploy.py --postbuild` để check output
- Không bao giờ để bug lọt lên production — tự sửa, tự fix, tự push
- Nếu CI workflow fail → check logs, fix ngay, commit + push lại
- Nếu self-heal fix file (slug/long lines) → commit riêng, push, workflow mới sẽ xử lý
- `scripts/pre_deploy.py` là gatekeeper cuối cùng — không bypass
- Luôn check `Hệ thống máy học đã học` message — nếu 0 patterns thì chạy lại `python3 scripts/learn.py`

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

### `tt` — Autonomous Topic Publisher (Codex / Claude / Gemini / OpenCode)

`AGENTS.md` là nguồn chính sách duy nhất cho `tt`; [docs/ai/tt.md](docs/ai/tt.md) chỉ là entrypoint ngắn. Chạy `./tt` (hoặc `python3 scripts/tt.py`) để:

```text
tt                         # tự nghiên cứu và xuất bản tối đa 1 bài
tt <chủ đề>                # nghiên cứu chủ đề chỉ định rồi xuất bản nếu đủ tốt
tt <URL báo Hàn>           # nghiên cứu URL và đối chiếu thêm nguồn độc lập
tt --dry-run               # nghiên cứu, chấm điểm, ghi report; không viết bài
tt --research-only         # chỉ nghiên cứu và ghi report; không gọi AI/không xuất bản
```

Quy trình bắt buộc của `tt`:

- Ưu tiên dữ liệu Google Search Console qua `TT_GSC_QUERIES_JSON` hoặc `TT_GSC_QUERIES_FILE`; fallback là Google News/Google Trends RSS và tín hiệu Naver. Candidate phải có ít nhất hai publisher đáng tin cậy độc lập, nếu có thể.
- Đọc toàn bộ `content/` và lịch sử `reports/tt/` để kiểm tra title, slug, description, tags, keywords, nội dung, intent và keyword cannibalization. Không đủ evidence hoặc bị trùng thì skip thành công.
- Mỗi lần tối đa một bài. Không bịa dữ kiện, ngày, trích dẫn, tên, số liệu, nguồn hoặc attribution ảnh. Ảnh mặc định không dùng nếu chưa xác minh license, tác giả/photographer và creator URL.
- Bài dùng đúng cấu trúc Hugo hiện tại: front matter `description`, ISO datetime có `+07:00`, section hiện hữu, internal/external links và `faq`; template tự render footer nên không chèn shortcode/footer block cuối bài.
- Khi xuất bản, `tt` chạy scientist checklist, front matter/SEO/Markdown/slug/link/image/schema QA; workflow tiếp tục chạy `pre_deploy.py`, Hugo production build, post-build QA, Pagefind search index và schema. Self-heal an toàn tối đa 3 vòng; lỗi sau đó dừng và không push.
- Báo cáo nằm tại `reports/tt/YYYY/MM/`. Workflow dùng `concurrency.group: koreawiki-tt-publisher` và `cancel-in-progress: false`, commit riêng `feat(content): publish <slug> via tt`, rebase an toàn rồi push default branch; không force-push/bypass protection. Nếu không push trực tiếp được, workflow tạo branch + PR và bật auto-merge để GitHub chỉ merge khi required checks xanh.
- AI secrets chỉ được cấp qua GitHub Actions Secrets (`TT_OPENAI_API_KEY`, `TT_ANTHROPIC_API_KEY`, `TT_GEMINI_API_KEY`, model tương ứng); không commit key và không đưa key ra frontend.

Không chạy `tt` publish trên working tree bẩn hoặc sai default branch. Thay đổi không liên quan phải được giữ nguyên.

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
