# Article Footer Macro

> **BẮT BUỘC** cho mọi bài viết, mọi cách soạn (`mm`, `nn`, `th`, thủ công, AI, import…).
> `scripts/qa.py` fail nếu thiếu `faq:` hoặc `article-footer`.
> Auto-fill: `python3 scripts/apply_article_footer.py --apply`

Shortcode `article-footer` thêm khối cuối bài (kiểu SEOMONEY):

1. **Liên kết ngoài** (nếu có)  
2. **Liên kết nội bộ** (nếu có)  
3. **Bản quyền & ghi nguồn**  
4. **FAQ** (accordion)

## "Bài này trả lời" (đầu bài)

Đặt FAQ trong **front matter** — partial `answers-toc` tự hiện ngay dưới tiêu đề:

```yaml
faq:
  - q: "SODA SODA phát hành khi nào?"
    a: "Ngày **4 tháng 8 năm 2026**."
  - q: "Pop-up store mở ở đâu?"
    a: "Tokyo, Osaka, Fukuoka."
```

Mỗi câu là link `#faq-1`, `#faq-2`, … nhảy xuống FAQ cuối bài và **tự mở** accordion.

## Cách dùng footer

Cuối file Markdown của bài (FAQ có thể bỏ nếu đã có trong front matter):

````markdown
{{</* article-footer */>}}
source: "Dispatch"
source_url: "https://example.com/article"
copyright: >
  Một phần dữ liệu tham khảo từ Dispatch.
  Bài viết chỉ tổng hợp / phân tích.
external:
  - title: "Nguồn gốc"
    url: "https://example.com/"
internal:
  - title: "Bài liên quan trên KoreaWiki"
    url: "en/kpop/some-slug/"
faq:
  - q: "Câu hỏi 1?"
    a: "Trả lời **markdown** được."
  - q: "Câu hỏi 2?"
    a: "Trả lời 2."
{{</* /article-footer */>}}
````

## Trường YAML

| Field | Type | Mô tả |
|-------|------|--------|
| `source` | string | Tên nguồn (dùng nếu không có `copyright`) |
| `source_url` | string | URL nguồn |
| `copyright` | string | Đoạn bản quyền / ghi nguồn (markdown) |
| `external` | list `{title, url}` | Link ngoài |
| `internal` | list `{title, url}` | Link trong site (`en/section/slug/`) |
| `faq` | list `{q, a}` | FAQ; `a` hỗ trợ markdown |

Chỉ render block nào có dữ liệu. FAQ dùng `<details>` (mở câu đầu).

## mm / nn / th workflow

Khi publish bài với `mm`, `nn`, hoặc `th`, nên điền:

- Nguồn báo gốc → `source` / `source_url` / `copyright`
- 1–3 internal links cùng chuyên mục
- External links thực sự dùng trong bài
- 3–5 FAQ ngắn (không bịa sự kiện)

## Ghi chú biên tập / `copyright` — wording công khai (bắt buộc khéo)

**Không** viết công khai kiểu “viết lại”, “rewrite”, “dịch từ”, “tóm lược / Việt hóa
dựa trên bài X”, “copy”, “đạo” — nghe như đạo văn và xấu cho độc giả + AdSense.

**Có** ghi nguồn lịch sự: bài thuộc KoreaWiki desk; **tham khảo** hồ sơ / thông cáo /
mục từ **công khai**; credit ảnh; không bổ sung số liệu ngoài nguồn.

### Mẫu tốt (ArchDaily / hồ sơ dự án)

```markdown
## Ghi chú biên tập

Bài của **KoreaWiki Culture Desk**. Thông tin kỹ thuật theo **hồ sơ dự án công khai**
của [văn phòng] (đăng trên ArchDaily). Specs bám nguồn đã dẫn; không bổ sung số liệu
ngoài hồ sơ. Ảnh © **[photographer]**.
```

```yaml
copyright: >
  Bài **KoreaWiki Culture Desk**. Tham khảo hồ sơ dự án công khai trên ArchDaily.
  Ảnh: **[photographer]**. Bản quyền hình ảnh thuộc chủ sở hữu; dùng với mục đích
  thông tin. Vui lòng dẫn nguồn khi trích dẫn.
```

### Mẫu tốt (thông cáo / báo)

```markdown
Bài của **KoreaWiki Newsroom**. Số liệu và mốc thời gian theo **thông cáo / bài**
của [nguồn] ngày [YYYY-MM-DD]; không suy diễn ngoài nguồn.
```

### Cấm trong body / FAQ / description / copyright

| Cấm | Thay bằng |
|-----|-----------|
| viết lại / rewrite | biên soạn / trình bày bằng tiếng Việt |
| Việt hóa dựa trên… | tham khảo hồ sơ / thông cáo công khai |
| tóm lược từ bài X | theo thông tin công khai đã dẫn |
| Giữ đủ specs từ nguồn (giọng “copy”) | Specs bám nguồn đã dẫn; không bổ sung số liệu |

## File kỹ thuật

- Shortcode: `themes/koreawiki/layouts/shortcodes/article-footer.html`
- Styles: `assets/scss/_article-footer.scss`
