# Article Footer Macro

Shortcode `article-footer` thêm khối cuối bài (kiểu SEOMONEY):

1. **Liên kết ngoài** (nếu có)  
2. **Liên kết nội bộ** (nếu có)  
3. **Bản quyền & ghi nguồn**  
4. **FAQ** (accordion)

## Cách dùng

Cuối file Markdown của bài:

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

## mm workflow

Khi publish bài với `mm`, nên điền:

- Nguồn báo gốc → `source` / `source_url` / `copyright`
- 1–3 internal links cùng chuyên mục
- External links thực sự dùng trong bài
- 3–5 FAQ ngắn (không bịa sự kiện)

## File kỹ thuật

- Shortcode: `themes/koreawiki/layouts/shortcodes/article-footer.html`
- Styles: `assets/scss/_article-footer.scss`
