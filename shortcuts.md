# Shortcuts

Tài liệu này là nơi lưu danh sách phím tắt và lệnh nhanh của KoreaWiki.
Mỗi mục nên ghi rõ:
- phím tắt hoặc lệnh
- ngữ cảnh dùng
- hành động
- logic xử lý
- trạng thái hiện tại

## Quy ước trạng thái
- `implemented`: đã có logic trong code
- `declared`: chỉ mới hiển thị trong UI hoặc tài liệu
- `planned`: sẽ làm sau

## Mẫu thêm mới

```md
### `<phím tắt>`
- Loại:
- Ngữ cảnh:
- Hành động:
- Logic:
- Trạng thái:
- File liên quan:
```

## Danh sách hiện tại

| Shortcut | Ngữ cảnh | Hành động | Logic | Trạng thái | File liên quan |
|---|---|---|---|---|---|
| `Ctrl+K` / `Meta+K` | Toàn site | Mở/đóng command palette search | `assets/js/main.js` bắt `keydown` (ctrl/meta + k), gọi `openSearch()` / `closeSearch()`, focus trap trong modal | `implemented` | `assets/js/main.js`, `themes/koreawiki/layouts/partials/header.html`, `themes/koreawiki/layouts/partials/search-modal.html` |
| `/` | Toàn site (không khi đang gõ trong input) | Mở search | `assets/js/main.js` nếu `key === '/'` và target không phải input/textarea/contenteditable thì `openSearch()` | `implemented` | `assets/js/main.js` |
| `Esc` | Search overlay mở | Đóng search | `closeSearch()` + restore focus | `implemented` | `assets/js/main.js` |
| `Enter` | Search overlay | Mở kết quả đang chọn (mặc định kết quả đầu) | `assets/js/search.js` `handleKeydown` → `window.location.href` | `implemented` | `assets/js/search.js` |
| `↑` / `↓` | Search overlay | Di chuyển giữa kết quả | `selectedIndex` + class `selected` + `aria-activedescendant` | `implemented` | `assets/js/search.js` |
| `Tab` | Search overlay | Autocomplete gợi ý / title | `autocompleteTab()` lấy suggestion đầu hoặc title kết quả đầu | `implemented` | `assets/js/search.js` |
| `mm` | `opencode` command | Xuất bản **news tiếng Hàn** → VI + full gallery | `.opencode/commands/mm.md`: fetch → TM → **viết lại human/khách quan, giữ đủ content** (không MT dán) → `fetch_cover.py --all` → Hugo → QA. Góp phần gốc cho originality | `implemented` | `.opencode/commands/mm.md`, `scripts/fetch_cover.py`, `scientist.md` |
| `nn` | `opencode` command | Xuất bản **bài tiếng Anh** (báo / **ArchDaily**) → VI + full gallery | `.opencode/commands/nn.md`: như `mm` nhưng EN→VI; **viết lại human, đủ facts**; gallery + render-image baseURL; faq/footer/QA | `implemented` | `.opencode/commands/nn.md`, `themes/.../render-image.html`, `scientist.md` |
| `glossary` page | Site footer / `/glossary/` | Duyệt bảng thuật ngữ Hàn→Việt | Layout `glossary/list.html` + `assets/js/glossary.js` search (Hangul/VI/romaja, fuzzy, filter, pagination) | `implemented` | `content/en/glossary/`, `themes/koreawiki/layouts/glossary/`, `assets/js/glossary.js` |
| Self-heal CI | GitHub Actions on Build/QA **failure** | Tự phân tích log, fix theo scientist.md, validate, mở PR | `.github/workflows/self-healing.yml` + `scripts/self_healing.py` (max 5 rounds, không force deploy) | `implemented` | `AGENTS.md`, `scientist.md`, `docs/self-healing.md`, `reports/self-healing/` |

## Recent `mm` Runs

Các commit dưới đây là những bài viết gần đây trong git history, cùng thời kỳ với workflow `mm`.
Git không lưu trực tiếp log runtime của phím tắt, nên đây là dấu vết commit tương ứng chứ không phải session log nội bộ.

| Commit | Bài viết | File nội dung | Ảnh | Ghi chú |
|---|---|---|---|---|
| `2d2fb8a` | Kim Bu-jang drama review | `content/en/kdrama/kim-bujang-drama-review-2026.md` | `static/images/2026/07/kimbujang-drama-review-2026.jpg` | Dispatch 2344893 |
| `bfa79e6` | Youth financial counseling feature | `content/en/feature/youth-financial-independence-counseling.md` | Không có | Hankyoreh |
| `e8faecc` | Anne's Library publishing house profile | `content/en/culture/annes-library-publishing-house-profile.md` | Không có | Dailyan |
| `a9f5b97` | Incheon Independent Film Festival interview | `content/en/culture/incheon-independent-film-festival-2026.md` | Không có | OhmyNews |
| `dc26e6d` | TOURS SODA SODA Japan promotion | `content/en/kpop/tours-soda-soda-japan-promotion-2026.md` | `static/images/2026/07/tours-soda-soda-promotion-2026.jpg` | Dispatch |
| `152497d` | Bang Chan winter collection event | `content/en/kpop/bangchan-winter-collection-2026.md` | `static/images/2026/07/bangchan-winter-collection-2026.jpg` | Dispatch |
| `aa0f459` | Gong Yoo first Asia tour | `content/en/artist/gong-yoo-asia-tour-2026.md` | `static/images/2026/07/gongyoo-asia-tour-2026.jpg` | Dispatch |
| `4fa4b5f` | Yoo Ah-in comeback speculation | `content/en/artist/yoo-ah-in-hope-premiere-comeback-speculation.md` | Không có | Xportsnews |
| `e34f941` | 'Hope' opening day box office record | `content/en/movies/hope-opening-day-box-office-2026.md` | `static/images/2026/07/hope-opening-day-2026.jpg` | Dispatch |
| `49ac4d5` | Lee Jong-suk & IU breakup | `content/en/artist/lee-jong-suk-iu-breakup-2026.md` | `static/images/2026/07/lee-jong-suk-iu-breakup-2026.jpg` | Dispatch |

## Cách cập nhật

1. Thêm một dòng mới vào bảng trên khi có shortcut mới.
2. Nếu shortcut đã có code, ghi rõ file liên quan và logic xử lý.
3. Nếu chỉ là mô tả UI hoặc dự định tương lai, đánh dấu `declared` hoặc `planned`.
4. Nếu thay đổi logic, cập nhật cả tài liệu này lẫn file code tương ứng.

## Ghi chú

- Nếu muốn tài liệu này trở thành nguồn sự thật duy nhất cho shortcuts, hãy giữ tên phím tắt và trạng thái đồng nhất với code.
- Các shortcut hiển thị trên UI nhưng chưa có handler thực thi phải được đánh dấu rõ để tránh hiểu nhầm.
