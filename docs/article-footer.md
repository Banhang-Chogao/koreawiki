# Article footer

Mỗi bài viết tự động gọi `themes/koreawiki/layouts/partials/article-footer.html` sau `.Content`. Partial dùng chung render theo thứ tự:

1. Liên kết nội bộ (nếu có).
2. Liên kết bên ngoài (nếu có).
3. FAQ (nếu có).
4. `Bản quyền & Ghi nguồn` — luôn có, kể cả khi bài không có nguồn ngoài.

Không chèn shortcode hoặc heading nguồn/bản quyền vào Markdown. Dữ liệu chỉ đặt trong front matter.

## Nguồn tham khảo

Chuẩn hiện tại là danh sách có tên và URL:

```yaml
sources:
  - name: "Tên nguồn"
    url: "https://example.org/bai-goc"
```

Các bài cũ dùng `source`/`source_label`/`source_url` vẫn được partial đọc tương thích, nhưng bài mới phải dùng `sources`. URL phải là HTTP(S), tên và URL không được rỗng, `null`, `unknown` hoặc placeholder.

## Credit ảnh

Chỉ khai báo khi đã xác minh dữ liệu:

```yaml
image_credits:
  - platform: "Nền tảng"
    photographer: "Tác giả/photographer"
    author_url: "https://example.org/author"
    license: "Tên license"
```

Partial bỏ qua trường thiếu và không tự suy đoán credit từ caption, nội dung bài hoặc tên file ảnh.

## Kiểm tra

`python3 scripts/check_article_footer.py` kiểm tra front matter, URL, dữ liệu placeholder và block Markdown thủ công. Sau production build, chạy thêm:

```bash
python3 scripts/check_article_footer.py --postbuild
```

Styles dùng chung nằm ở `assets/scss/_article-footer.scss`.
