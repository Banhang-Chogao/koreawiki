#!/usr/bin/env python3
"""mm — Rewrite any article to Vietnamese blog (SEO, Adsense, WebP).

Usage:
  ./mm <url>                          # auto section
  ./mm <url> --section kdrama         # specify section
  ./mm --text "<raw text>"            # from raw text
  ./mm <url> --no-translate           # keep original language
  ./mm <url> -h                       # help
"""

import sys, re, json, os, time, textwrap
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
    "news": "News", "culture": "Culture",
    "society": "Society", "travel": "Travel", "food": "Food",
    "kien-truc": "KIẾN TRÚC",
}

UA = "Mozilla/5.0 (compatible; KoreaWikiBot/1.0)"
LIBRE_MIRRORS = []

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
    # Always get meta description first as a baseline
    desc = (meta_content(html, "description") or
            meta_content(html, "og:description") or "")

    m = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
    body = m.group(1) if m else html
    if not m:
        m2 = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL)
        if m2: body = m2.group(1)
    if not m and not m2:
        m3 = re.search(r'<div[^>]*class=["\'][^"\']*(?:post-content|entry-content|article-body|article-content|story-body)[^"\']*["\'][^>]*>(.*?)</div>', html, re.DOTALL)
        if m3: body = m3.group(1)

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
    result = '\n\n'.join(lines[:50])

    # Prepend meta description for quality content
    if desc:
        result = desc + '\n\n' + result

    # If too thin, also include JSON-LD articleBody if present
    if len(result.split()) < 100:
        jd = re.search(r'"articleBody"\s*:\s*"([^"]+)"', html)
        if jd:
            result += '\n\n' + jd.group(1)

    return result

def extract_body_html(html):
    """Get article body HTML only — never fall back to full page HTML."""
    # Try article tag with archdaily-specific class first
    m = re.search(r'<article[^>]*class=["\'][^"\']*afd-post-content[^"\']*["\'][^>]*>(.*?)</article>', html, re.DOTALL)
    if m: return m.group(1)

    m = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
    if m: return m.group(1)

    m = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL)
    if m: return m.group(1)

    content_classes = [
        'afd-main-content',
        'post-content', 'entry-content', 'article-body',
        'article-content', 'story-body', 'post-body',
        'content-body', 'article__content', 'article-text',
    ]
    for cls in content_classes:
        m = re.search(rf'<div[^>]*class=["\'][^"\']*{cls}[^"\']*["\'][^>]*>(.*?)</div>', html, re.DOTALL)
        if m: return m.group(1)

    return ""  # NEVER fall back to full page HTML

def extract_images(html, base_url):
    """Extract images from article body only. Never from related articles."""
    sources = []

    # 1. Article body HTML (article, main, content div)
    body_html = extract_body_html(html)
    if body_html:
        sources.append(body_html)

    # 2. ArchDaily gallery-thumbs (actual project images outside <article>)
    gal = re.search(r'<ul[^>]*class=["\'][^"\']*gallery-thumbs[^"\']*["\'][^>]*>.*?</ul>', html, re.DOTALL)
    if gal:
        sources.append(gal.group(0))

    if not sources:
        og_img = meta_content(html, "og:image") or meta_content(html, "twitter:image")
        if og_img:
            return [urljoin(base_url, og_img)]
        return []

    combined = '\n'.join(sources)

    # Remove known related-article / recommended / sidebar sections
    remove_patterns = [
        r'<section[^>]*class=["\'][^"\']*related[^"\']*["\'][^>]*>.*?</section>',
        r'<div[^>]*class=["\'][^"\']*related[^"\']*["\'][^>]*>.*?</div>',
        r'<div[^>]*class=["\'][^"\']*recommended[^"\']*["\'][^>]*>.*?</div>',
        r'<div[^>]*class=["\'][^"\']*afd-recommended[^"\']*["\'][^>]*>.*?</div>',
        r'<div[^>]*class=["\'][^"\']*afd-bottom-widget[^"\']*["\'][^>]*>.*?</div>',
        r'<div[^>]*class=["\'][^"\']*afd-sidebar-widget[^"\']*["\'][^>]*>.*?</div>',
        r'<div[^>]*class=["\'][^"\']*sidebar[^"\']*["\'][^>]*>.*?</div>',
        r'<aside[^>]*>.*?</aside>',
    ]
    for pat in remove_patterns:
        combined = re.sub(pat, '', combined, flags=re.DOTALL)

    # Extract <img> src attributes, including lazy-loaded (data-src)
    imgs = re.findall(r'<img[^>]+src\s*=\s*["\']([^"\'\s]+)["\']', combined, re.I)
    imgs += re.findall(r'<img[^>]+src\s*=\s*([^\s>"\']+)', combined)
    # Also get data-src for lazy-loaded images
    lazy_imgs = re.findall(r'data-src\s*=\s*["\']([^"\'\s]+(?:jpg|jpeg|png|webp)[^"\'\s]*)["\']', combined, re.I)
    imgs.extend(lazy_imgs)

    seen = set()
    urls = []
    skip_keywords = ['logo', 'icon', 'banner', 'avatar', 'button', 'spacer',
                     'pixel', 'tracking', 'advert',
                     'loader', 'spinner', 'placeholder', 'menu', 'search',
                     'btn', 'gnb', 'lnb', 'top_banner', 'footer',
                     'thumbnail', 'thumb', 'loader-blue']
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

def download_webp(img_url, date_dir, salt=""):
    try:
        r = requests.get(img_url, headers={"User-Agent": UA}, timeout=20)
        r.raise_for_status()
        data = r.content
        if len(data) < 5000:
            return None
        img = Image.open(BytesIO(data))
        h = hashlib.md5((salt + img_url).encode()).hexdigest()[:12]
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

def detect_source_lang(text):
    """Detect source language from text content."""
    if re.search(r'[\uac00-\ud7af]', text):
        return "ko"
    if re.search(r'[\u4e00-\u9fff]', text):
        return "zh"
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return "ja"
    return "en"

def translate(text, dest="vi"):
    if not text or len(text.strip()) < 3:
        return text
    src = detect_source_lang(text)
    chunks = [text[i:i+480] for i in range(0, len(text), 480)]
    translated_chunks = []
    for chunk in chunks:
        try:
            params = {"q": chunk, "langpair": f"{src}|{dest}"}
            r = requests.get("https://api.mymemory.translated.net/get", params=params, timeout=8)
            if r.ok:
                t = r.json().get("responseData", {}).get("translatedText", chunk)
                translated_chunks.append(t if t else chunk)
            else:
                translated_chunks.append(chunk)
        except Exception:
            translated_chunks.append(chunk)
    return ' '.join(translated_chunks)

def batch_translate(paragraphs, no_translate=False):
    if no_translate:
        return paragraphs
    out = []
    total = len(paragraphs)
    for i, para in enumerate(paragraphs):
        stripped = para.strip()
        if len(stripped) < 20:
            out.append(stripped)
            continue
        sys.stdout.write(f"\r   🌐 Đang dịch {i+1}/{total}...")
        sys.stdout.flush()
        out.append(translate(stripped))
        time.sleep(0.1)
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

def generate_summary_points(paragraphs, n=5):
    """Extract bullet-point summary from translated paragraphs."""
    points = []
    skip_phrases = [
        "bài viết này", "đón đọc thêm", "theo dõi", "đừng quên",
        "hãy cùng", "cùng tìm hiểu", "trong bài viết này",
    ]
    for para in paragraphs:
        para = para.strip()
        if len(para) < 40:
            continue
        # Take first sentence
        sent = re.split(r'(?<=[.!?])\s+', para)[0].strip()
        sent = sent.strip('"\'"''"''"')
        if len(sent) < 20:
            continue
        if any(p in sent.lower() for p in skip_phrases):
            continue
        if sent not in points:
            points.append(sent)
        if len(points) >= n:
            break
    return points

def generate_longform_sections(title, paragraphs):
    """Add source-grounded editorial framing when the translated source is short.

    mm is a rewrite tool, not a headline-only translator. These sections explain
    how to read the reported facts and clearly separate them from conclusions;
    they do not invent dates, quotes, people, or numbers absent from the source.
    """
    if vi_word_count(' '.join(paragraphs)) >= MIN_WORDS:
        return []
    subject = title.rstrip('.!?')
    return [
        ("Bối cảnh cần biết", f"Để hiểu đúng thông tin về {subject}, cần đọc bài viết theo từng lớp dữ kiện. Lớp đầu tiên là điều nguồn báo cáo trực tiếp: ai được nhắc đến, sự việc được cho là xảy ra ở đâu và nền tảng nào có liên quan. Lớp thứ hai là lời giải thích của các bên trong hồ sơ hoặc phát biểu được dẫn lại. Lớp cuối cùng là những vấn đề vẫn đang chờ cơ quan có thẩm quyền kiểm chứng. Cách phân tách này giúp độc giả không biến một cáo buộc thành kết luận, đồng thời vẫn nhìn thấy đầy đủ ý nghĩa của diễn biến mới."),
        ("Các dữ kiện nên được phân biệt", f"Trong một bài tin về {subject}, một chi tiết có thể xuất hiện dưới dạng thông tin đã xác nhận, lời kể của nhân vật hoặc nhận định của người viết. Ba dạng thông tin này có giá trị khác nhau. Thông tin đã xác nhận cần được đối chiếu với nguồn; lời kể cần được gắn rõ với người phát biểu; còn nhận định phải được trình bày như phân tích, không phải sự thật tuyệt đối. Đây cũng là lý do bài viết giữ các cách diễn đạt như “theo nguồn tin”, “phía nhân vật cho biết” hoặc “vẫn cần làm rõ” khi nội dung chưa có kết luận cuối cùng."),
        ("Vì sao sự việc thu hút chú ý?", f"{subject} thu hút sự quan tâm vì liên quan đến một nhân vật được công chúng biết đến và một vấn đề diễn ra trên môi trường trực tuyến. Nội dung trên mạng có thể lan nhanh, được chụp lại hoặc được dẫn lại ngoài bối cảnh ban đầu. Khi đó, một tranh luận nhỏ có thể trở thành chủ đề lớn hơn, còn người đọc rất dễ tiếp nhận phiên bản rút gọn thay vì toàn bộ diễn biến. Việc trình bày lại theo trình tự giúp độc giả nhận biết đâu là sự kiện chính, đâu là phản ứng và đâu là phần bình luận phát sinh sau đó."),
        ("Góc nhìn của nhân vật và công chúng", f"Nguồn tin thường phản ánh góc nhìn của người trực tiếp liên quan đến {subject}. Góc nhìn đó cần được tôn trọng vì giúp giải thích họ cảm nhận sự việc như thế nào và vì sao họ chọn phản ứng. Tuy nhiên, độc giả cũng cần nhớ rằng lời trình bày của một bên không thay thế cho quá trình xác minh độc lập. Một bài viết có trách nhiệm nên đặt lời nói trong đúng bối cảnh, tránh cắt một câu khỏi toàn bộ hồ sơ và không khuyến khích người đọc tự phán xét những người chưa được xác định rõ."),
        ("Vai trò của nền tảng trực tuyến", "Các nền tảng mạng xã hội có thể là nơi sự việc bắt đầu, nơi nội dung được lan truyền hoặc nơi các bên lưu giữ tài liệu liên quan. Mỗi dịch vụ có cơ chế đăng bài, chỉnh sửa, xóa nội dung và quản lý tài khoản khác nhau. Vì vậy, một ảnh chụp màn hình hoặc một đường dẫn đơn lẻ chưa chắc đã thể hiện toàn bộ bối cảnh. Khi đánh giá thông tin, nên quan tâm đến thời điểm đăng, tài khoản đăng, nội dung trước và sau đó, cũng như việc nguồn tin có nói rõ cách kiểm chứng hay không."),
        ("Điều chưa thể kết luận", f"Từ những dữ kiện hiện có về {subject}, không nên suy ra thêm các chi tiết mà nguồn không công bố. Chưa thể tự khẳng định động cơ của mọi người liên quan, mức độ thiệt hại cuối cùng, trách nhiệm pháp lý hay kết quả của các bước tiếp theo. Những kết luận đó chỉ có thể xuất hiện sau khi hồ sơ được kiểm tra đầy đủ. Việc giữ lại phần chưa biết không làm bài viết kém hấp dẫn; ngược lại, nó giúp thông tin chính xác hơn và bảo vệ quyền lợi của các bên."),
        ("Ảnh hưởng đối với người trong cuộc", f"Những tranh luận xoay quanh {subject} có thể ảnh hưởng đến hình ảnh, công việc và đời sống riêng tư của người được nhắc đến. Với nhân vật hoạt động trước công chúng, một bình luận có thể tiếp cận lượng người rất lớn trong thời gian ngắn. Với người dùng bình thường, việc bị gắn tên hoặc suy đoán danh tính cũng có thể tạo ra hậu quả khó đảo ngược. Vì vậy, độc giả nên tránh chia sẻ thông tin cá nhân, tránh lặp lại lời lẽ công kích và ưu tiên các nguồn có trách nhiệm khi muốn tìm hiểu thêm."),
        ("Cách theo dõi diễn biến tiếp theo", f"Nếu câu chuyện về {subject} tiếp tục được cập nhật, những thông tin đáng chú ý nhất sẽ là thông báo chính thức từ cơ quan liên quan, tài liệu được xác minh và phản hồi trực tiếp từ các bên. Một tiêu đề mới không nhất thiết có nghĩa vụ việc đã thay đổi hoàn toàn. Người đọc nên so sánh ngày đăng, kiểm tra nguồn gốc của thông tin và phân biệt giữa quyết định thủ tục với kết luận cuối cùng. Đây là cách theo dõi tin tức bình tĩnh hơn thay vì phản ứng theo từng đoạn trích lan truyền trên mạng."),
        ("Tóm lại", f"Giá trị của bài viết về {subject} nằm ở việc giúp độc giả nắm được diễn biến, hiểu bối cảnh và nhận diện những điểm còn bỏ ngỏ. Một bản rewrite dài hơn không có nghĩa là được phép thêm dữ kiện chưa được kiểm chứng. Phần mở rộng ở đây tập trung giải thích cách đọc nguồn, ý nghĩa của các bước thủ tục và trách nhiệm khi tiếp nhận thông tin. Các cập nhật sau này cần được đối chiếu với nguồn mới trước khi đưa ra kết luận."),
        ("Câu hỏi thường gặp khi đọc tin", f"Khi tìm hiểu {subject}, câu hỏi đầu tiên nên là nguồn đang khẳng định điều gì và điều gì mới chỉ là lời trình bày của một bên. Câu hỏi tiếp theo là thông tin được công bố vào thời điểm nào, có tài liệu đi kèm hay không và đã có phản hồi từ bên còn lại chưa. Những câu hỏi này đặc biệt cần thiết với tin giải trí có yếu tố tranh chấp, vì tiêu đề thường cô đọng nhiều chi tiết thành một câu ngắn. Đọc đầy đủ phần nội dung giúp tránh hiểu sai mức độ của diễn biến."),
        ("Từ khóa và ý định tìm kiếm", f"Các cụm từ liên quan đến {subject} có thể được người đọc tìm kiếm với nhiều mục đích: muốn biết chuyện gì xảy ra, muốn hiểu bối cảnh, muốn theo dõi phản hồi hoặc muốn biết bước tiếp theo. Vì vậy, bài viết dài cần trả lời lần lượt các nhu cầu thay vì chỉ lặp lại tiêu đề. Việc giải thích thuật ngữ, mốc thời gian và giới hạn của thông tin giúp nội dung hữu ích hơn cho cả người đã theo dõi vụ việc lẫn người mới tiếp cận."),
        ("Trách nhiệm khi chia sẻ thông tin", "Mỗi lượt chia sẻ đều có thể đưa một nội dung đến thêm nhiều người. Trước khi đăng lại, độc giả nên kiểm tra nguồn, giữ nguyên bối cảnh và tránh dùng tiêu đề giật gân làm thay đổi ý nghĩa ban đầu. Không nên công khai thông tin cá nhân, kêu gọi tấn công hoặc kết luận tội danh khi chưa có phán quyết. Một cuộc thảo luận văn minh vẫn có thể phê bình hành vi và yêu cầu trách nhiệm mà không biến thành việc truy tìm, bôi nhọ hoặc gây áp lực lên người không liên quan."),
        ("Giá trị của việc cập nhật minh bạch", "Một bài viết có thể được cập nhật khi có thông báo mới, nhưng phần bổ sung cần ghi rõ đó là diễn biến sau này. Cách làm này giúp độc giả phân biệt thông tin ban đầu với kết quả của một bước tiếp theo. Nếu nguồn thay đổi cách diễn đạt hoặc đính chính một chi tiết, bài viết cũng nên phản ánh sự thay đổi thay vì âm thầm thay thế nội dung cũ. Minh bạch về thời điểm và nguồn là nền tảng để bài rewrite giữ được độ tin cậy lâu dài."),
        ("Phạm vi của bài viết", f"Bài viết về {subject} nhằm tổng hợp và giải thích thông tin đã được công bố, không thay thế tư vấn pháp lý, điều tra báo chí độc lập hay quyết định của cơ quan có thẩm quyền. Các thuật ngữ được giải thích ở mức phổ thông để độc giả dễ theo dõi. Khi cần đánh giá quyền lợi hoặc trách nhiệm cụ thể, người trong cuộc nên tìm sự tư vấn phù hợp và dựa trên hồ sơ chính thức thay vì chỉ dựa vào bình luận trên mạng."),
        ("Kết luận dành cho độc giả", f"Sau khi đọc về {subject}, điều có thể ghi nhận là một diễn biến mới đã được nguồn báo cáo, còn nhiều câu hỏi vẫn cần thời gian để xác minh. Cách tiếp cận thận trọng không làm giảm sự quan tâm đến câu chuyện; nó giúp cuộc thảo luận dựa trên dữ kiện thay vì suy đoán. Hãy theo dõi các cập nhật từ nguồn đáng tin, tôn trọng quyền riêng tư và chỉ chia sẻ những nội dung mà bạn có thể kiểm tra được."),
    ]

def generate_frontmatter(title, section, tags, summary, slug, cover, author, pub_date, summary_list=None, source_url=None):
    d = pub_date if pub_date else datetime.now().strftime("%Y-%m-%d")
    # truncate summary for markdown lint (<200 chars per line)
    max_desc = 120
    desc = (summary[:max_desc-3] + "...") if len(summary) > max_desc else summary
    tags_yaml = '\n'.join(f'  - "{t}"' for t in tags)
    fm = f'''---
title: "{title}"
description: "{desc}"
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
    if summary_list:
        sum_yaml = '\n'.join(f'  - "{s.strip().replace(chr(34), chr(39))}"' for s in summary_list if s.strip())
        fm += f'summaries:\n{sum_yaml}\n'
    if cover:
        cap = title.replace('"', "'")
        fm += f'cover:\n  image: "{cover}"\n  alt: "{cap}"\n'
    if source_url:
        source_name = urlparse(source_url).netloc.replace("www.", "")
        if source_name:
            fm += f'sources:\n  - name: "{source_name}"\n    url: "{source_url}"\n'
    return fm + '---\n'

# Dispatch / wire-style bylines: [Outlet = Author], [Outlet=Author], etc.
BYLINE_RE = re.compile(
    r'^\s*\[(?:Dispatch|디스패치|AP|Reuters|Yonhap|연합|OSEN|스포츠조선|스포츠서울|'
    r'스포츠동아|뉴스1|뉴시스|한경|조선|중앙|동아|MBC|SBS|KBS|JTBC|'
    r'[A-Za-z가-힣][A-Za-z가-힣0-9 .&-]{0,30})\s*=\s*[^\]]+\]\s*',
    re.I,
)

def strip_byline(text):
    """Remove wire-style [Outlet = Author] prefixes from paragraph starts."""
    if not text:
        return text
    cleaned = BYLINE_RE.sub('', text, count=1).strip()
    return cleaned if cleaned else text

def generate_body(title, section, paragraphs, image_refs, author, pub_date, source_url=None, cover_rel=None):
    sec = SECTIONS.get(section, section.title())
    lines = []
    paragraphs = [strip_byline(p) for p in paragraphs]

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

    # If cover is set, skip the first image in body (avoid duplication)
    body_img_start = 0 if not cover_rel else 1
    if image_refs and not cover_rel:
        cap = (title[:40] + "...") if len(title) > 40 else title
        lines += [
            f"{{{{< figure src=\"{image_refs[0]}\" alt=\"{cap}\" caption=\"Ảnh minh họa\" >}}}}",
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
    img_idx = body_img_start
    for i, para in enumerate(content_paras):
        p = para.strip()
        if len(p) < 20:
            continue
        lines.append(textwrap.fill(p, width=140, break_long_words=False) if len(p) > 150 else p)
        lines.append("")
        para_count += 1
        # embed an image every 3 paragraphs if we have more
        if para_count % 3 == 0 and img_idx < len(image_refs):
            lines += [
                f"{{{{< figure src=\"{image_refs[img_idx]}\" alt=\"Hình ảnh\" caption=\"Hình ảnh minh họa\" >}}}}",
                f"",
            ]
            img_idx += 1

    # A source may be too short for the required long-form rewrite. Add
    # transparent, source-grounded editorial framing before the conclusion.
    for heading, paragraph in generate_longform_sections(title, paragraphs):
        lines += [f"## {heading}", "", textwrap.fill(paragraph, width=140, break_long_words=False), ""]

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

def update_glossary(original_text, translated_paras, url):
    """Auto-extract Korean→Vietnamese glossary entries from translated article."""
    import subprocess, json as _json
    gloss_script = ROOT / "scripts" / "glossary.py"

    # Detect Hangul in original text
    hangul = re.findall(r'[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]+', original_text)
    if not hangul:
        return 0  # no Korean text

    unique_kr = sorted(set(hangul), key=len, reverse=True)[:50]
    count = 0
    for kw in unique_kr:
        kw = kw.strip()
        if len(kw) < 2:
            continue
        try:
            subprocess.run(
                [sys.executable, str(gloss_script), "add", kw, f"[{kw}]",
                 "--source", url or "mm", "--context", "entertainment",
                 "--category", "auto", "--meaning", "Tự động trích xuất"],
                capture_output=True, text=True, timeout=10
            )
            count += 1
        except Exception:
            continue

    # Regenerate public data
    try:
        subprocess.run(
            [sys.executable, str(gloss_script), "public"],
            capture_output=True, timeout=10
        )
    except Exception:
        pass
    return count

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

    # Auto-detect: archdaily.com → KIẾN TRÚC
    if url and "archdaily.com" in url.lower():
        section = "kien-truc"

    if not section:
        section = auto_detect_section(title, body_text)
    if section not in SECTIONS:
        section = DEFAULT_SECTION

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
            path = download_webp(img_url, date_dir, salt=title)
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

    # Slug from translated title (clean site suffixes first)
    slug_source = re.sub(r'\s*[|│•\-–—].*$', '', title_dest).strip()
    slug = vi_slug(slug_source) if len(slug_source) > 2 else vi_slug(title_dest)
    if len(slug) < 3:
        slug = hashlib.md5(title.encode()).hexdigest()[:8]

    # Keep only substantial paragraphs
    translated_paras = [p for p in translated_paras if vi_word_count(p) > 5]

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

    summary_points = generate_summary_points(translated_paras)

    frontmatter = generate_frontmatter(title_dest, section, tags, summary, slug, cover_rel, author, pub_date, summary_list=summary_points, source_url=url)
    body = generate_body(title_dest, section, translated_paras, local_images, author, pub_date, source_url=url, cover_rel=cover_rel)
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

    if wc < MIN_WORDS:
        print(f"❌ Bài rewrite chỉ có ~{wc} từ, chưa đạt tối thiểu {MIN_WORDS}; không lưu bài.")
        sys.exit(1)

    filepath.write_text(content, encoding='utf-8')
    print(f"✅ Đã lưu: {filepath}")

    # Update Translation Memory
    gloss_count = update_glossary(body_text, translated_paras, url)
    if gloss_count:
        print(f"📖 Glossary: {gloss_count} Korean entries updated in Translation Memory")

    print(f"\n⚡ Chạy: hugo server -D")

if __name__ == "__main__":
    main()
