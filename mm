#!/usr/bin/env python3
"""mm — Rewrite any article to Vietnamese blog (SEO, Adsense, WebP).

Usage:
  ./mm <url>
  ./mm <url> --section kdrama
  ./mm --text "<raw text>"
  ./mm <url> -h
"""

import sys, re, json, os, textwrap, uuid, time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
from io import BytesIO
import hashlib

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("pip install Pillow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content"
STATIC_IMG_DIR = ROOT / "static" / "images"
DEFAULT_SECTION = "blog"
MIN_WORDS = 2000

SECTIONS = {
    "news": "News", "kdrama": "K-Drama", "kpop": "K-Pop",
    "culture": "Culture", "history": "History",
    "society": "Society", "travel": "Travel", "food": "Food",
    "blog": "Blog",
}

UA = "Mozilla/5.0 (compatible; KoreaWikiBot/1.0)"
LIBRE_URLS = [
    "https://libretranslate.com/translate",
    "https://translate.terraprint.co/translate",
]

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[àáảãạâầấẩẫậăằắẳẵặ]', 'a', text)
    text = re.sub(r'[èéẻẽẹêềếểễệ]', 'e', text)
    text = re.sub(r'[ìíỉĩị]', 'i', text)
    text = re.sub(r'[òóỏõọôồốổỗộơờớởỡợ]', 'o', text)
    text = re.sub(r'[ùúủũụưừứửữự]', 'u', text)
    text = re.sub(r'[ỳýỷỹỵ]', 'y', text)
    text = re.sub(r'[đ]', 'd', text)
    text = re.sub(r'[^a-z0-9-]', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def fetch_url(url):
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    return resp.text

def extract_title(html):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if m: return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL)
    if m: return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    return "Bài viết chưa có tiêu đề"

def extract_body_text(html):
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 40]
    return '\n\n'.join(lines[:30])

def extract_images(html, base_url):
    imgs = re.findall(r'<img[^>]+src\s*=\s*["\']([^"\'\s]+)["\']', html, re.IGNORECASE)
    imgs += re.findall(r'<img[^>]+src\s*=\s*([^\s>"\']+)', html)
    seen = set()
    urls = []
    for src in imgs:
        src = src.strip().split('?')[0]
        if not src or src.startswith('data:'):
            continue
        ext = Path(src).suffix.lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            continue
        abs_src = urljoin(base_url, src)
        if abs_src not in seen and 'logo' not in abs_src.lower() and 'icon' not in abs_src.lower() and 'banner' not in abs_src.lower():
            seen.add(abs_src)
            urls.append(abs_src)
    return urls[:10]

def download_and_webp(img_url, date_dir):
    try:
        resp = requests.get(img_url, headers={"User-Agent": UA}, timeout=20)
        resp.raise_for_status()
        data = resp.content
        if len(data) < 1000:
            return None
        img = Image.open(BytesIO(data))
        h = hashlib.md5(img_url.encode()).hexdigest()[:12]
        webp_path = date_dir / f"mm-{h}.webp"
        if webp_path.exists():
            return webp_path
        if img.mode in ("RGBA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img)
            img = bg
        elif img.mode == "CMYK":
            img = img.convert("RGB")
        img.save(webp_path, "WEBP", quality=80, method=6)
        return webp_path
    except Exception:
        return None

def translate_text(text, src="en", dest="vi"):
    """Translate text via LibreTranslate (free, no API key)."""
    if not text or len(text.strip()) < 2:
        return text
    payload = {"q": text, "source": src, "target": dest, "format": "text"}
    for base in LIBRE_URLS:
        try:
            resp = requests.post(base, json=payload, timeout=15)
            if resp.ok:
                return resp.json().get("translatedText", text)
        except Exception:
            continue
    # fallback: strip English, wrap in paragraph marker
    print("   ⚠️  LibreTranslate không khả dụng, giữ nguyên bản gốc.")
    return text

def translate_paragraphs(paragraphs):
    """Translate a list of paragraphs to Vietnamese."""
    translated = []
    total = len(paragraphs)
    for i, para in enumerate(paragraphs):
        if len(para.strip()) < 10:
            translated.append(para)
            continue
        sys.stdout.write(f"\r   🌐 Đang dịch {i+1}/{total}...")
        sys.stdout.flush()
        result = translate_text(para)
        translated.append(result)
        time.sleep(0.3)  # rate limit courtesy
    print()
    return translated

def generate_frontmatter(title, section, tags, summary, slug, cover):
    date = datetime.now().strftime("%Y-%m-%d")
    tags_yaml = '\n'.join(f'  - "{t}"' for t in tags)
    fm = f'''---
title: "{title}"
description: "{summary}"
keywords: [{', '.join(f'"{t}"' for t in tags)}]
date: {date}
lastmod: {date}
draft: false
author: "KoreaWiki Team"
tags:
{tags_yaml}
categories:
- "{SECTIONS.get(section, section.title())}"
showToc: true
readingTime: true
slug: {slug}
'''
    if cover:
        fm += f'cover:\n  image: "{cover}"\n  alt: "{title}"\n'
    return fm + '---\n'

def generate_body(title, section, summary, paragraphs, image_refs):
    section_name = SECTIONS.get(section, section.title())
    lines = [
        f"## Tổng quan",
        f"",
        f"{summary}",
        f"",
        f"Bài viết này sẽ phân tích chi tiết về **{title}** — một chủ đề đang được quan tâm trong chuyên mục **{section_name}** của KoreaWiki. Nội dung được biên soạn nhằm cung cấp góc nhìn toàn diện, chính xác và hữu ích cho độc giả.",
        f"",
    ]

    if image_refs:
        lines += [f"{{{{< figure src=\"{image_refs[0]}\" alt=\"{title}\" caption=\"Ảnh minh họa: {title}\" >}}}}", ""]

    # Translated body
    lines += [
        f"---",
        f"",
        f"## Nội dung chính",
        f"",
    ]
    for para in paragraphs:
        lines.append(f"{para.strip()}")
        lines.append(f"")

    # Remaining images
    for j, img_ref in enumerate(image_refs[1:], 1):
        lines += [
            f"{{{{< figure src=\"{img_ref}\" alt=\"Hình ảnh {j}\" caption=\"Hình ảnh minh họa {j}\" >}}}}",
            f"",
        ]

    lines += [
        f"---",
        f"",
        f"## Kết luận",
        f"",
        f"{summary} Đây là chủ đề đáng theo dõi, đặc biệt với những ai quan tâm đến sự phát triển của ngành công nghiệp văn hóa Hàn Quốc.",
        f"",
    ]
    return '\n'.join(lines)

def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        return

    url = None
    raw_text = None
    section = DEFAULT_SECTION

    i = 0
    while i < len(args):
        a = args[i]
        if a in ('--section', '-s') and i+1 < len(args):
            section = args[i+1]; i += 2
        elif a == '--text' and i+1 < len(args):
            raw_text = args[i+1]; i += 2
        else:
            if not url and not a.startswith('--'):
                url = a
            i += 1

    if section not in SECTIONS:
        print(f"Section '{section}' không hợp lệ. Chọn: {', '.join(SECTIONS.keys())}")
        sys.exit(1)

    if url:
        print(f"📰 Đang tải: {url}")
        html = fetch_url(url)
        title = extract_title(html)
        body_text = extract_body_text(html)
        img_urls = extract_images(html, url)
    elif raw_text:
        title = re.split(r'[\n.]', raw_text.strip())[0][:120]
        body_text = raw_text
        img_urls = []
    else:
        print("❌ Cần URL hoặc --text")
        sys.exit(1)

    slug = slugify(title)
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = STATIC_IMG_DIR / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    # Download & convert images to WebP
    local_images = []
    print(f"🖼️  Đang tải {len(img_urls)} ảnh...")
    for img_url in img_urls:
        sys.stdout.write(f"   ↓ {Path(img_url).name[:40]:40s} ")
        sys.stdout.flush()
        path = download_and_webp(img_url, date_dir)
        if path:
            rel = path.relative_to(ROOT / "static")
            local_images.append(str(rel))
            kb = path.stat().st_size // 1024
            print(f"✅ {kb}KB")
        else:
            print("⚠️  Lỗi")

    cover_rel = local_images[0] if local_images else None

    # Translate to Vietnamese
    print("🌐 Đang dịch sang tiếng Việt...")
    title_vi = translate_text(title)
    paragraphs = body_text.split('\n\n')
    translated_paras = translate_paragraphs(paragraphs)
    # filter to paragraphs with >20 Vietnamese words
    translated_paras = [p for p in translated_paras if len(re.findall(r'\b\w+\b', p)) > 20]

    summary = f"Bài viết phân tích chi tiết về {title_vi} — được KoreaWiki biên dịch từ nguồn nước ngoài sang tiếng Việt, chuẩn SEO và Google Adsense."
    tags = [SECTIONS.get(section, section.title()), "Hàn Quốc", "tin tức"]
    if url:
        domain = urlparse(url).netloc.replace('www.', '')
        tags.append(domain)

    frontmatter = generate_frontmatter(title_vi, section, tags, summary, slug, cover_rel)
    body = generate_body(title_vi, section, summary, translated_paras, local_images)
    content = frontmatter + '\n' + body

    word_count = len(re.findall(r'\b\w+\b', content[content.index('##'):]))
    print(f"\n📝 Tiêu đề: {title_vi}")
    print(f"📂 Section: {section}")
    print(f"🖼️  Ảnh: {len(local_images)}")
    print(f"🔤 Từ: ~{word_count}")

    section_dir = CONTENT_DIR / section
    section_dir.mkdir(parents=True, exist_ok=True)
    filepath = section_dir / f"{slug}.md"
    counter = 1
    while filepath.exists():
        filepath = section_dir / f"{slug}-{counter}.md"
        counter += 1

    filepath.write_text(content, encoding='utf-8')
    print(f"✅ Đã lưu: {filepath}")

    if word_count < MIN_WORDS:
        print(f"⚠️  Cảnh báo: ~{word_count} từ (yêu cầu ≥{MIN_WORDS}). Cần bổ sung thêm nội dung.")

    print(f"\n⚡ Chạy: hugo server -D")

if __name__ == "__main__":
    main()
