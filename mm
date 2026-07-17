#!/usr/bin/env python3
"""mm — Rewrite any article to Vietnamese blog (SEO, Adsense, WebP).

Usage:
  ./mm <url>                          # auto section
  ./mm <url> --section kdrama         # specify section
  ./mm --text "<raw text>"            # from raw text
  ./mm <url> --no-translate           # keep original language
  ./mm <url> -h                       # help
"""

import sys, re, json, os, time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
from io import BytesIO
import hashlib

try:
    import requests
except ImportError:
    print("pip install requests"); sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("pip install Pillow"); sys.exit(1)

ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content"
STATIC_IMG_DIR = ROOT / "static" / "images"
DEFAULT_SECTION = "blog"
MIN_WORDS = 2000
MAX_IMG = 10

SECTIONS = {
    "blog": "Blog", "kdrama": "K-Drama", "kpop": "K-Pop",
    "news": "News", "culture": "Culture", "history": "History",
    "society": "Society", "travel": "Travel", "food": "Food",
}

UA = "Mozilla/5.0 (compatible; KoreaWikiBot/1.0)"
LIBRE_MIRRORS = [
    "https://libretranslate.com/translate",
    "https://translate.terraprint.co/translate",
    "https://translate.api.skit.ai/translate",
]

SECTION_HINTS = {
    "blog": [],
    "kdrama": ["drama", "series", "episode", "điện ảnh", "phim truyền hình",
               "k-drama", "korean drama", "tv show", "netflix", "đạo diễn",
               "diễn viên", "kịch bản", "tập phim"],
    "kpop": ["k-pop", "kpop", "music video", "album", "concert", "ca sĩ",
             "nhóm nhạc", "idol", "comeback", "fan meeting", "stage",
             "entertainment", "award show"],
    "news": ["breaking", "update", "announce", "reported", "confirmed",
             "tin tức", "mới nhất", "phát ngôn", "cập nhật"],
    "culture": ["tradition", "festival", "custom", "heritage", "văn hóa",
                "truyền thống", "lễ hội", "văn hóa đại chúng"],
    "travel": ["travel", "tour", "destination", "du lịch", "điểm đến",
               "khám phá", "chuyến đi"],
}

# ---------- helpers ----------

def vi_slug(text):
    text = text.lower().strip()
    maps = [
        (r'[àáảãạâầấẩẫậăằắẳẵặ]', 'a'),
        (r'[èéẻẽẹêềếểễệ]', 'e'),
        (r'[ìíỉĩị]', 'i'),
        (r'[òóỏõọôồốổỗộơờớởỡợ]', 'o'),
        (r'[ùúủũụưừứửữự]', 'u'),
        (r'[ỳýỷỹỵ]', 'y'),
        (r'[đ]', 'd'),
    ]
    for pattern, repl in maps:
        text = re.sub(pattern, repl, text)
    text = re.sub(r'[^a-z0-9-]', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def vi_word_count(text):
    return len(text.split())

def fetch(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.text

# ---------- HTML parsing ----------

def meta_content(html, name):
    m = re.search(rf'<meta[^>]+(?:name|property)=["\']{name}["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m: return m.group(1)
    m = re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\']{name}["\']', html, re.I)
    if m: return m.group(1)
    return None

def extract_title(html):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if m: return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL)
    if m: return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    return "Bài viết"

def extract_author(html):
    a = meta_content(html, "author") or meta_content(html, "article:author")
    if a: return re.sub(r'<[^>]+>', '', a).strip()
    m = re.search(r'<a[^>]+rel=["\']author["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.I)
    if m: return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    return None

def extract_date(html):
    d = meta_content(html, "article:published_time") or meta_content(html, "date") or meta_content(html, "datePublished")
    if d: return d.strip()
    m = re.search(r'datetime=["\'](\d{4}-\d{2}-\d{2})', html)
    if m: return m.group(1)
    return None

def extract_body_text(html):
    # try <article> first
    m = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
    body = m.group(1) if m else html
    # try <main> if no article
    if not m:
        m2 = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL)
        if m2: body = m2.group(1)
    text = re.sub(r'<script[^>]*>.*?</script>', '', body, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL)
    text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL)
    text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL)
    text = re.sub(r'<aside[^>]*>.*?</aside>', '', text, flags=re.DOTALL)
    text = re.sub(r'<figure[^>]*>.*?</figure>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 50]
    return '\n\n'.join(lines)

def extract_images(html, base_url):
    imgs = re.findall(r'<img[^>]+src\s*=\s*["\']([^"\'\s]+)["\']', html, re.I)
    imgs += re.findall(r'<img[^>]+src\s*=\s*([^\s>"\']+)', html)
    seen = set()
    urls = []
    skip_keywords = ['logo', 'icon', 'banner', 'avatar', 'button', 'spacer',
                     'pixel', 'tracking', 'advertising', 'ads/', 'banner',
                     'loader', 'spinner', 'placeholder']
    for src in imgs:
        src = src.strip().rsplit('?', 1)[0]
        if not src or src.startswith('data:'):
            continue
        if any(k in src.lower() for k in skip_keywords):
            continue
        ext = Path(src).suffix.lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            continue
        abs_src = urljoin(base_url, src)
        if abs_src not in seen:
            seen.add(abs_src)
            urls.append(abs_src)
    return urls[:MAX_IMG]

def download_webp(img_url, date_dir):
    try:
        r = requests.get(img_url, headers={"User-Agent": UA}, timeout=20)
        r.raise_for_status()
        data = r.content
        if len(data) < 1000:
            return None
        img = Image.open(BytesIO(data))
        h = hashlib.md5(img_url.encode()).hexdigest()[:12]
        path = date_dir / f"mm-{h}.webp"
        if path.exists():
            return path
        if img.mode in ("RGBA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA":
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img)
            img = bg
        elif img.mode == "CMYK":
            img = img.convert("RGB")
        img.save(path, "WEBP", quality=80, method=6)
        return path
    except Exception:
        return None

# ---------- translation ----------

def translate(text, src="en", dest="vi", max_retry=2):
    if not text or len(text.strip()) < 3:
        return text
    payload = {"q": text, "source": src, "target": dest, "format": "text"}
    for attempt in range(max_retry + 1):
        for mirror in LIBRE_MIRRORS:
            try:
                r = requests.post(mirror, json=payload, timeout=20)
                if r.ok:
                    t = r.json().get("translatedText", text)
                    # re-apply any lost Unicode
                    return t
            except Exception:
                continue
        if attempt < max_retry:
            time.sleep(1.5)
    print("   ⚠️  Hết mirror, giữ nguyên bản gốc.")
    return text

def batch_translate(paragraphs, no_translate=False):
    if no_translate:
        return paragraphs
    out = []
    total = len(paragraphs)
    # merge short paras for efficiency
    merged = []
    buf = []
    for p in paragraphs:
        stripped = p.strip()
        if len(stripped) < 15:
            if buf:
                merged.append(' '.join(buf))
                buf = []
            merged.append(stripped)
        else:
            buf.append(stripped)
    if buf:
        merged.append(' '.join(buf))
    for i, para in enumerate(merged):
        if len(para) < 15:
            out.append(para)
            continue
        sys.stdout.write(f"\r   🌐 Đang dịch {i+1}/{len(merged)}...")
        sys.stdout.flush()
        out.append(translate(para))
        time.sleep(0.25)
    print()
    return out

# ---------- content generation ----------

def auto_detect_section(title, text):
    text_lower = (title + ' ' + text).lower()
    scores = {}
    for sec, hints in SECTION_HINTS.items():
        scores[sec] = sum(1 for h in hints if h in text_lower)
    if max(scores.values()) > 0:
        return max(scores, key=scores.get)
    return DEFAULT_SECTION

def extract_keywords(title, paragraphs, n=5):
    text = ' '.join(paragraphs).lower()
    # Vietnamese stop words
    stop = {'và', 'của', 'các', 'có', 'được', 'trong', 'với', 'cho',
            'một', 'những', 'không', 'là', 'đã', 'sẽ', 'đang', 'khi',
            'từ', 'này', 'nó', 'họ', 'tôi', 'bạn', 'về', 'đến', 'ở',
            'trên', 'dưới', 'tại', 'theo', 'sau', 'trước', 'cũng',
            'rất', 'nhiều', 'ít', 'hơn', 'vậy', 'nên', 'lên', 'xuống',
            'ra', 'vào', 'cả', 'người', 'điều', 'thể', 'qua', 'lại',
            'thì', 'mà', 'bị', 'đây', 'đó', 'ấy', 'như', 'hay', 'hoặc',
            'để', 'vì', 'nếu', 'tuy', 'song', 'do', 'vẫn', 'còn'}
    words = re.findall(r'\b[a-zà-ỹ]{4,}\b', text)
    freq = {}
    for w in words:
        if w not in stop:
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, c in sorted_words[:n]]

def generate_frontmatter(title, section, tags, summary, slug, cover, author, pub_date):
    d = pub_date if pub_date else datetime.now().strftime("%Y-%m-%d")
    tags_yaml = '\n'.join(f'  - "{t}"' for t in tags)
    fm = f'''---
title: "{title}"
description: "{summary}"
keywords: [{', '.join(f'"{t}"' for t in tags)}]
date: {d}
lastmod: {datetime.now().strftime("%Y-%m-%d")}
draft: false
author: "{author if author else "KoreaWiki Team"}"
tags:
{tags_yaml}
categories:
- "{SECTIONS.get(section, section.title())}"
showToc: true
readingTime: true
slug: {slug}
'''
    if cover:
        cap = title.replace('"', "'")
        fm += f'cover:\n  image: "{cover}"\n  alt: "{cap}"\n'
    return fm + '---\n'

def generate_body(title, section, paragraphs, image_refs, author, pub_date):
    sec = SECTIONS.get(section, section.title())
    lines = []

    # lead
    first_paras = [p for p in paragraphs if len(p.strip()) > 40]
    lead = first_paras[0] if first_paras else paragraphs[0] if paragraphs else ""
    lines += [
        f"## Tổng quan",
        f"",
        f"{textwrap.fill(lead, width=180, break_long_words=False) if len(lead) > 190 else lead}",
        f"",
        f"Bài viết này thuộc chuyên mục **{sec}** của KoreaWiki, được biên dịch và biên tập lại nhằm mang đến góc nhìn mới mẻ và hữu ích cho độc giả.",
        f"",
    ]

    if image_refs:
        lines += [
            f"{{{{< figure src=\"{image_refs[0]}\" alt=\"{title}\" caption=\"Ảnh minh họa: {title}\" >}}}}",
            f"",
        ]

    lines += [
        f"---",
        f"",
        f"## Nội dung chính",
        f"",
    ]

    # content_paras = ...
    content_paras = paragraphs[1:] if len(paragraphs) > 1 else paragraphs
    if not content_paras:
        content_paras = [lead]

    para_count = 0
    img_idx = 1
    for i, para in enumerate(content_paras):
        p = para.strip()
        if len(p) < 20:
            continue
        lines.append(textwrap.fill(p, width=180, break_long_words=False) if len(p) > 190 else p)
        lines.append("")
        para_count += 1
        # embed an image every 3 paragraphs if we have more
        if para_count % 3 == 0 and img_idx < len(image_refs):
            lines += [
                f"{{{{< figure src=\"{image_refs[img_idx]}\" alt=\"Hình ảnh\" caption=\"Hình ảnh minh họa\" >}}}}",
                f"",
            ]
            img_idx += 1

    # any leftover images
    while img_idx < len(image_refs):
        lines += [
            f"{{{{< figure src=\"{image_refs[img_idx]}\" alt=\"Hình ảnh\" caption=\"Hình ảnh minh họa\" >}}}}",
            f"",
        ]
        img_idx += 1

    lines += [
        f"---",
        f"",
        f"## Kết luận",
        f"",
        f"{lead[:200].rsplit(' ', 1)[0] if len(lead) > 200 else lead}",
        f"",
        f"Đón đọc thêm nhiều bài viết thú vị khác tại KoreaWiki.",
        f"",
    ]
    return '\n'.join(lines)

# ---------- main ----------

def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        return

    url = None
    raw_text = None
    section = None
    no_translate = False

    i = 0
    while i < len(args):
        a = args[i]
        if a in ('--section', '-s') and i + 1 < len(args):
            section = args[i + 1]; i += 2
        elif a == '--text' and i + 1 < len(args):
            raw_text = args[i + 1]; i += 2
        elif a == '--no-translate':
            no_translate = True; i += 1
        else:
            if not url and not a.startswith('--'):
                url = a
            i += 1

    if url:
        print(f"📰 Đang tải: {url}")
        html = fetch(url)
        title = extract_title(html)
        body_text = extract_body_text(html)
        img_urls = extract_images(html, url)
        author = extract_author(html)
        pub_date = extract_date(html)
    elif raw_text:
        title = re.split(r'[\n.]', raw_text.strip())[0][:120]
        body_text = raw_text
        img_urls = []
        author = None
        pub_date = None
    else:
        print("❌ Cần URL hoặc --text"); sys.exit(1)

    if not section:
        section = auto_detect_section(title, body_text)
    if section not in SECTIONS:
        section = DEFAULT_SECTION

    slug = vi_slug(title)
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = STATIC_IMG_DIR / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    # Download & convert images
    local_images = []
    if img_urls:
        print(f"🖼️  Đang tải {len(img_urls)} ảnh...")
        for img_url in img_urls:
            sys.stdout.write(f"   ↓ {Path(img_url).name[:40]:40s} ")
            sys.stdout.flush()
            path = download_webp(img_url, date_dir)
            if path:
                rel = path.relative_to(ROOT / "static")
                local_images.append(str(rel))
                kb = path.stat().st_size // 1024
                print(f"✅ {kb}KB")
            else:
                print("⚠️  Lỗi")

    cover_rel = local_images[0] if local_images else None

    # Translate
    print(f"🌐 {'Giữ nguyên ngôn ngữ gốc' if no_translate else 'Đang dịch sang tiếng Việt'}...")
    title_dest = title if no_translate else translate(title)
    paras = [p for p in body_text.split('\n\n') if p.strip()]
    translated_paras = batch_translate(paras, no_translate)

    # Keep only substantial paragraphs
    translated_paras = [p for p in translated_paras if vi_word_count(p) > 10]

    if not translated_paras:
        print("❌ Không đủ nội dung sau khi dịch.")
        sys.exit(1)

    # Auto keywords & summary
    keywords = extract_keywords(title_dest, translated_paras)
    all_tags = [SECTIONS.get(section, section.title())] + keywords[:3]
    if url:
        domain = urlparse(url).netloc.replace('www.', '').split('.')[0]
        all_tags.append(domain)
    # deduplicate
    seen_tags = set()
    tags = []
    for t in all_tags:
        if t and t not in seen_tags:
            seen_tags.add(t)
            tags.append(t)

    summary = f"Bài viết về {title_dest} — được KoreaWiki biên dịch và phân tích, mang đến cái nhìn toàn diện và sâu sắc về chủ đề này."
    if section in ("kdrama", "kpop", "culture", "news"):
        summary = f"{title_dest} — tin tức giải trí Hàn Quốc mới nhất trên KoreaWiki. Biên dịch sang tiếng Việt, chuẩn SEO và Google Adsense."

    frontmatter = generate_frontmatter(title_dest, section, tags, summary, slug, cover_rel, author, pub_date)
    body = generate_body(title_dest, section, translated_paras, local_images, author, pub_date)
    content = frontmatter + '\n' + body

    wc = vi_word_count(body)
    print(f"\n📝 Tiêu đề: {title_dest}")
    print(f"📂 Section: {section}")
    print(f"🖼️  Ảnh: {len(local_images)}")
    print(f"🔤 Từ: ~{wc}")
    print(f"🏷️  Tags: {', '.join(tags[:6])}")

    section_dir = CONTENT_DIR / section
    section_dir.mkdir(parents=True, exist_ok=True)
    filepath = section_dir / f"{slug}.md"
    counter = 1
    while filepath.exists():
        filepath = section_dir / f"{slug}-{counter}.md"
        counter += 1

    filepath.write_text(content, encoding='utf-8')
    print(f"✅ Đã lưu: {filepath}")

    if wc < MIN_WORDS:
        print(f"⚠️  Cảnh báo: ~{wc} từ (yêu cầu ≥{MIN_WORDS}). Cần bổ sung thêm nội dung.")

    print(f"\n⚡ Chạy: hugo server -D")

if __name__ == "__main__":
    main()
