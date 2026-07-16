#!/usr/bin/env python3
"""Fetch a cover image for a KoreaWiki mm article.

Primary use in `mm` workflow:
  1. Prefer --page (original Korean article URL) → extract og/twitter/body images
  2. Or --image (direct image URL) → download that file
  3. Save under static/images/YYYY/MM/<slug>-cover.<ext>
  4. Print the relative path for cover.image front matter

Usage:
  python3 scripts/fetch_cover.py --page https://example.com/article --slug my-post
  python3 scripts/fetch_cover.py --image https://cdn.example.com/a.jpg --slug my-post
  python3 scripts/fetch_cover.py --page URL --slug my-post --dry-run

Requires network. Never invent image credits — attribution stays in the article.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
UA = (
    "Mozilla/5.0 (compatible; KoreaWikiBot/1.0; +https://github.com/Banhang-Chogao/koreawiki)"
)

# Paths / hosts that are almost never useful article covers
SKIP_SUBSTR = (
    "logo",
    "icon",
    "favicon",
    "sprite",
    "avatar",
    "profile",
    "emoji",
    "button",
    "banner_ad",
    "ads/",
    "/ad/",
    "1x1",
    "pixel",
    "spacer",
    "tracking",
    "share_",
    "sns_",
    "loading",
)

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


class _ImgExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.metas: dict[str, str] = {}
        self.imgs: list[str] = []
        self.link_images: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            prop = (a.get("property") or a.get("name") or "").lower()
            content = a.get("content", "").strip()
            if prop and content:
                self.metas[prop] = content
        elif tag == "img":
            src = (a.get("src") or a.get("data-src") or a.get("data-original") or "").strip()
            if src:
                self.imgs.append(src)
            srcset = a.get("srcset") or a.get("data-srcset") or ""
            if srcset:
                # "url 1x, url2 2x" or "url 640w"
                first = srcset.split(",")[0].strip().split()[0]
                if first:
                    self.imgs.append(first)
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            href = (a.get("href") or "").strip()
            if href and ("image" in rel or rel == "thumbnail"):
                self.link_images[rel] = href


def fetch_bytes(url: str, timeout: int = 30) -> tuple[bytes, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,image/*,*/*;q=0.8",
            "Accept-Language": "ko,en;q=0.8,vi;q=0.7",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        return data, ctype


def looks_like_image(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    return None


def is_skipped_url(url: str) -> bool:
    low = url.lower()
    return any(s in low for s in SKIP_SUBSTR)


def score_candidate(url: str, source: str) -> int:
    """Higher is better."""
    if is_skipped_url(url):
        return -1000
    score = 0
    low = url.lower()
    if source.startswith("og:"):
        score += 100
    elif source.startswith("twitter:"):
        score += 90
    elif source == "link":
        score += 70
    else:
        score += 40
    if any(x in low for x in ("/news/", "photo", "image", "img", "upload", "media")):
        score += 15
    if any(x in low for x in ("thumb", "small", "icon", "list")):
        score -= 20
    # Prefer wider requested sizes if encoded in query
    m = re.search(r"[?&]w=(\d+)", low)
    if m:
        score += min(int(m.group(1)) // 100, 20)
    return score


def extract_candidates(page_url: str, html: str) -> list[tuple[int, str, str]]:
    parser = _ImgExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass

    raw: list[tuple[str, str]] = []
    for key in (
        "og:image",
        "og:image:secure_url",
        "twitter:image",
        "twitter:image:src",
    ):
        if key in parser.metas:
            raw.append((key, parser.metas[key]))
    for rel, href in parser.link_images.items():
        raw.append((f"link:{rel}", href))
    for src in parser.imgs[:40]:
        raw.append(("img", src))

    scored: list[tuple[int, str, str]] = []
    seen: set[str] = set()
    for source, u in raw:
        abs_u = urljoin(page_url, u.strip())
        if not abs_u.startswith("http"):
            continue
        # strip common tracking fragments only
        abs_u = abs_u.split("#")[0]
        if abs_u in seen:
            continue
        seen.add(abs_u)
        sc = score_candidate(abs_u, source)
        if sc < 0:
            continue
        scored.append((sc, abs_u, source))
    scored.sort(key=lambda x: -x[0])
    return scored


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80] or "cover"


def default_out_dir() -> Path:
    now = datetime.now(timezone.utc)
    return STATIC / "images" / f"{now:%Y}" / f"{now:%m}"


def download_image(url: str, dest_base: Path) -> Path:
    data, ctype = fetch_bytes(url)
    ext = looks_like_image(data)
    if not ext:
        # try content-type
        if "jpeg" in ctype or "jpg" in ctype:
            ext = ".jpg"
        elif "png" in ctype:
            ext = ".png"
        elif "webp" in ctype:
            ext = ".webp"
        elif "gif" in ctype:
            ext = ".gif"
        else:
            # path suffix fallback
            path_ext = Path(urlparse(url).path).suffix.lower()
            if path_ext in IMG_EXT:
                ext = path_ext
            else:
                raise ValueError(f"Not a recognized image ({ctype or 'unknown type'}): {url}")
    if len(data) < 2000:
        raise ValueError(f"Image too small ({len(data)} bytes): {url}")
    dest = dest_base.with_suffix(ext)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch cover image for mm articles")
    ap.add_argument("--page", help="Original article page URL (extract images)")
    ap.add_argument("--image", help="Direct image URL to download")
    ap.add_argument("--slug", required=True, help="Article slug (filename base)")
    ap.add_argument(
        "--out-dir",
        default="",
        help="Output dir under static/ (default: static/images/YYYY/MM)",
    )
    ap.add_argument("--dry-run", action="store_true", help="List candidates only")
    ap.add_argument("--max-try", type=int, default=8, help="Max image candidates to try")
    args = ap.parse_args()

    if not args.page and not args.image:
        print("error: need --page and/or --image", file=sys.stderr)
        return 2

    slug = slugify(args.slug)
    out_dir = Path(args.out_dir) if args.out_dir else default_out_dir()
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    dest_base = out_dir / f"{slug}-cover"

    candidates: list[tuple[int, str, str]] = []
    if args.image:
        candidates.append((1000, args.image.strip(), "cli:--image"))
    if args.page:
        page = args.page.strip()
        try:
            html_b, ctype = fetch_bytes(page)
        except urllib.error.HTTPError as e:
            print(f"error: fetch page HTTP {e.code}: {page}", file=sys.stderr)
            if not args.image:
                return 1
            html_b, ctype = b"", ""
        except Exception as e:
            print(f"error: fetch page failed: {e}", file=sys.stderr)
            if not args.image:
                return 1
            html_b, ctype = b"", ""
        if html_b:
            # charset best-effort
            try:
                html = html_b.decode("utf-8")
            except UnicodeDecodeError:
                html = html_b.decode("euc-kr", errors="replace")
            extracted = extract_candidates(page, html)
            print(f"found {len(extracted)} candidate(s) on page", file=sys.stderr)
            for sc, u, src in extracted:
                if not any(u == c[1] for c in candidates):
                    candidates.append((sc, u, src))

    candidates.sort(key=lambda x: -x[0])
    if not candidates:
        print("error: no image candidates found", file=sys.stderr)
        return 1

    if args.dry_run:
        for i, (sc, u, src) in enumerate(candidates[:20], 1):
            print(f"{i:2}. [{sc:4}] {src:20} {u}")
        return 0

    errors: list[str] = []
    for sc, url, src in candidates[: max(1, args.max_try)]:
        try:
            dest = download_image(url, dest_base)
            rel = dest.relative_to(STATIC).as_posix()
            print(f"ok: saved {rel}  (from {src})", file=sys.stderr)
            print(rel)  # stdout → use as cover.image
            print(f"source_image_url: {url}", file=sys.stderr)
            return 0
        except Exception as e:
            errors.append(f"{src} {url}: {e}")
            continue

    print("error: all download attempts failed:", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
