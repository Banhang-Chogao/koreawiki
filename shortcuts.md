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
| `Ctrl+K` / `Meta+K` | Toàn site | Mở hộp tìm kiếm | `assets/js/main.js` bắt `keydown`, nếu `ctrlKey` hoặc `metaKey` và `key === 'k'` thì `preventDefault()` rồi click nút `[data-search-toggle]` đầu tiên | `implemented` | `assets/js/main.js`, `themes/koreawiki/layouts/partials/header.html`, `themes/koreawiki/layouts/partials/home/search-box.html` |
| `Esc` | Toàn site, đặc biệt trong search overlay | Đóng hộp tìm kiếm | `assets/js/main.js` bắt `keydown`, nếu `key === 'Escape'` thì gọi `closeSearch()` | `implemented` | `assets/js/main.js`, `themes/koreawiki/layouts/partials/search-modal.html` |
| `Enter` | Search overlay | Chọn kết quả | Hiện chỉ có hint trong UI; `assets/js/search.js` chưa có handler chọn kết quả bằng Enter | `declared` | `themes/koreawiki/layouts/partials/search-modal.html`, `assets/js/search.js` |
| `↑` / `↓` | Search overlay | Di chuyển giữa các kết quả | Hiện chỉ có hint trong UI; `assets/js/search.js` chưa có logic điều hướng bằng phím mũi tên | `declared` | `themes/koreawiki/layouts/partials/search-modal.html`, `assets/js/search.js` |
| `mm` | `opencode` command | Chạy workflow xuất bản bài news tiếng Hàn | File `.opencode/commands/mm.md` định nghĩa luồng: lấy URL hoặc text thô, dịch, viết lại, QA, build, commit, push | `implemented` | `.opencode/commands/mm.md`, `scientist.md` |

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

## Cách cập nhật

1. Thêm một dòng mới vào bảng trên khi có shortcut mới.
2. Nếu shortcut đã có code, ghi rõ file liên quan và logic xử lý.
3. Nếu chỉ là mô tả UI hoặc dự định tương lai, đánh dấu `declared` hoặc `planned`.
4. Nếu thay đổi logic, cập nhật cả tài liệu này lẫn file code tương ứng.

## Ghi chú

- Nếu muốn tài liệu này trở thành nguồn sự thật duy nhất cho shortcuts, hãy giữ tên phím tắt và trạng thái đồng nhất với code.
- Các shortcut hiển thị trên UI nhưng chưa có handler thực thi phải được đánh dấu rõ để tránh hiểu nhầm.
