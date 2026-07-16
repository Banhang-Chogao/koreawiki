#!/usr/bin/env python3
"""Fetch cover + in-article images for a KoreaWiki mm article.

Primary use in `mm` workflow:
  1. Prefer --page (original Korean article URL) → extract ALL usable images
  2. Or --image (one or more direct image URLs, repeatable)
  3. Save under static/images/YYYY/MM/<slug>-cover.<ext> and <slug>-01, -02, …
  4. With --all (default for mm): download every unique content image, print JSON

Usage:
  # Recommended for mm — all images from the source page
  python3 scripts/fetch_cover.py --page https://example.com/article --slug my-post --all

  # Legacy: first good cover only
  python3 scripts/fetch_cover.py --page URL --slug my-post

  # Direct URL(s)
  python3 scripts/fetch_cover.py --image https://cdn/.../a.jpg --image https://cdn/.../b.jpg --slug my-post --all

  # Inspect only
  python3 scripts/fetch_cover.py --page URL --slug my-post --dry-run

Requires network. Never invent image credits — attribution stays in the article.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
# Browser-like UA: many Korean publishers (Dispatch, etc.) serve a thin shell
# to non-browser bots and omit og:image / cms-content from the HTML.
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 KoreaWikiBot/1.1"
)

# Paths / hosts that are almost never useful article photos
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
    "menu_bars",
    "search_nbtn",
    "icon-plus",
    "facebook.com/tr",
    "googletagmanager",
    "google-analytics",
    "doubleclick",
    "scorecardresearch",
    "hotphotos",
    "imgsnap",  # Dispatch related thumbs often via imgsnap resize
    "img.youtube.com",
    "ytimg.com",
    "placeholder",
    "blank.gif",
    "spacer.gif",
    "default_image",
    "www-renewal",
    "/asset/images/",
    "arrows-left",
    "arrows-right",
    "mobile-arrows",
    "en-dipe/asset",
)

# URL substrings that strongly suggest real article media
CONTENT_HINTS = (
    "/cms-content/",
    "/uploads/",
    "/admin/news/",
    "/photo/",
    "/image/",
    "/images/",
    "/media/",
    "/news/",
    "cdnser.be/cms",
    "kakaocdn.net/kakaocorp",
    "imgnews",
    "thumbnews",
    "postfiles",
    "blogfiles",
)

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Regex harvest for CDNs that may not appear as clean <img src> (lazy / JS / markdown)
URL_HARVEST = re.compile(
    r"""https?://[^\s"'<>\\]+?\.(?:jpe?g|png|webp|gif)(?:\?[^\s"'<>\\]*)?""",
    re.I,
)

SRCSET_SPLIT = re.compile(r"\s*,\s*")


class _ImgExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.metas: dict[str, str] = {}
        self.imgs: list[str] = []
        self.link_images: dict[str, str] = {}
        self.json_blobs: list[str] = []
        self._in_script = False
        self._script_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            prop = (a.get("property") or a.get("name") or "").lower()
            content = a.get("content", "").strip()
            if prop and content:
                self.metas[prop] = content
        elif tag == "img":
            for key in (
                "src",
                "data-src",
                "data-original",
                "data-lazy-src",
                "data-lazy",
                "data-url",
                "data-original-src",
                "data-image",
                "data-img",
                "data-photo",
            ):
                src = (a.get(key) or "").strip()
                if src and not src.startswith("data:"):
                    self.imgs.append(src)
            for key in ("srcset", "data-srcset"):
                srcset = a.get(key) or ""
                if srcset:
                    for part in SRCSET_SPLIT.split(srcset):
                        u = part.strip().split()[0] if part.strip() else ""
                        if u and not u.startswith("data:"):
                            self.imgs.append(u)
        elif tag == "source":
            srcset = a.get("srcset") or a.get("data-srcset") or ""
            if srcset:
                for part in SRCSET_SPLIT.split(srcset):
                    u = part.strip().split()[0] if part.strip() else ""
                    if u and not u.startswith("data:"):
                        self.imgs.append(u)
            src = (a.get("src") or "").strip()
            if src:
                self.imgs.append(src)
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            href = (a.get("href") or "").strip()
            if href and ("image" in rel or rel == "thumbnail"):
                self.link_images[rel] = href
        elif tag == "script":
            self._in_script = True
            self._script_chunks = []
            # JSON-LD sometimes in type application/ld+json
            if "ld+json" in (a.get("type") or "").lower():
                self._in_script = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_script:
            blob = "".join(self._script_chunks)
            if blob.strip():
                self.json_blobs.append(blob)
            self._in_script = False
            self._script_chunks = []

    def handle_data(self, data: str) -> None:
        if self._in_script:
            self._script_chunks.append(data)


def fetch_bytes(url: str, timeout: int = 30) -> tuple[bytes, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,image/*,*/*;q=0.8",
            "Accept-Language": "ko,en;q=0.8,vi;q=0.7",
            "Referer": url if "://" in url else "https://www.google.com/",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        final = resp.geturl() or url
        # Prefer final URL host for relative joins is handled by caller
        _ = final
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
    """Return True if URL is almost certainly not an article photo.

    Uses path-segment / bounded checks so short tokens like ``ads/`` do not
    false-positive inside ``uploads/`` (…uplo**ads/**…).
    """
    low = url.lower()
    if "facebook.com" in low and "/tr" in low:
        return True
    path = urlparse(low).path
    # path segments (empty bits from leading / ignored)
    segs = [s for s in path.split("/") if s]
    seg_set = set(segs)
    # exact junk filenames / dirs
    junk_names = {
        "logo",
        "icon",
        "favicon",
        "sprite",
        "avatar",
        "emoji",
        "pixel",
        "spacer",
        "loading",
        "menu_bars",
        "search_nbtn",
        "icon-plus",
        "arrows-left",
        "arrows-right",
        "mobile-arrows-left",
        "mobile-arrows-right",
        "blank.gif",
        "spacer.gif",
        "1x1",
        "1x1.gif",
        "1x1.png",
    }
    for s in segs:
        base = s.split("?")[0]
        stem = base.rsplit(".", 1)[0]
        if base in junk_names or stem in junk_names:
            return True
        if stem.endswith(("-logo", "_logo", "-icon", "_icon", "-avatar")):
            return True
    # path directory markers (whole segment)
    junk_dirs = {
        "ads",
        "ad",
        "advertising",
        "tracking",
        "sprite",
        "emoticons",
        "emoji",
        "favicon",
    }
    if seg_set & junk_dirs:
        return True
    # substring markers that are safe (won't hit uploads/)
    for s in (
        "banner_ad",
        "share_",
        "sns_",
        "hotphotos",
        "imgsnap",
        "img.youtube.com",
        "ytimg.com",
        "placeholder",
        "default_image",
        "www-renewal",
        "/asset/images/",
        "en-dipe/asset",
        "googletagmanager",
        "google-analytics",
        "doubleclick",
        "scorecardresearch",
        "profile_img",
        "user_profile",
    ):
        if s in low:
            return True
    # icon/logo in query-less basename
    base = segs[-1] if segs else ""
    if any(tok in base for tok in ("logo", "icon", "favicon", "sprite")) and not any(
        h in low for h in CONTENT_HINTS
    ):
        return True
    return False


def normalize_url(url: str) -> str:
    """Strip fragments and noise query params for dedup; keep path identity."""
    url = url.strip().split("#")[0]
    try:
        p = urlparse(url)
    except Exception:
        return url
    # Drop resize/cache-only params that create false unique URLs
    drop_keys = {
        "type",
        "opt",
        "w",
        "h",
        "width",
        "height",
        "quality",
        "q",
        "size",
        "resize",
        "fname",  # keep careful: kakaocdn thumb wrappers use fname=
    }
    qs = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in drop_keys]
    # Kakao thumb wrapper: prefer inner fname URL when present
    if "fname=" in p.query and "thumb" in p.path:
        for k, v in parse_qsl(p.query, keep_blank_values=True):
            if k == "fname" and v.startswith("http"):
                return normalize_url(v)
    return urlunparse((p.scheme, p.netloc, p.path, "", urlencode(qs), ""))


def canonical_image_key(url: str) -> str:
    """Dedup key: host + path without size suffixes in filename when possible."""
    n = normalize_url(url)
    p = urlparse(n)
    path = re.sub(r"_(?:small|thumb|medium|large|og)\b", "", p.path, flags=re.I)
    path = re.sub(r"/\d+x\d+/", "/", path)
    return f"{p.netloc.lower()}{path.lower()}"


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
    elif source == "harvest":
        score += 55
    elif source.startswith("ld+json"):
        score += 65
    elif source.startswith("cli:"):
        score += 1000
    else:
        score += 40
    if any(h in low for h in CONTENT_HINTS):
        score += 25
    if any(x in low for x in ("thumb", "small", "list", "icon", "resize/")):
        score -= 25
    # Prefer wider requested sizes if encoded in query
    m = re.search(r"[?&]w=(\d+)", low)
    if m:
        score += min(int(m.group(1)) // 100, 20)
    # Prefer non-gif for covers (often tracking leftovers already skipped)
    if low.endswith(".gif"):
        score -= 10
    return score


def _looks_like_image_url(url: str) -> bool:
    low = url.lower().split("?")[0]
    if any(low.endswith(ext) for ext in IMG_EXT):
        return True
    if any(h in low for h in CONTENT_HINTS):
        return True
    # reject bare site roots / html pages mis-parsed from JSON-LD
    path = urlparse(url).path
    if not path or path == "/":
        return False
    if path.endswith((".html", ".htm", ".php", ".asp")):
        return False
    return False


def _urls_from_json_blob(blob: str) -> list[str]:
    out: list[str] = []
    # image fields in JSON-LD / embedded state
    for m in re.finditer(
        r'"(?:image|thumbnailUrl|contentUrl|url)"\s*:\s*"([^"]+)"',
        blob,
        re.I,
    ):
        u = m.group(1).replace("\\/", "/")
        if u.startswith("//"):
            u = "https:" + u
        if u.startswith("http") and _looks_like_image_url(u):
            out.append(u)
    # bare image URLs inside scripts
    for m in URL_HARVEST.finditer(blob):
        u = m.group(0).rstrip("\\").rstrip(")")
        if _looks_like_image_url(u):
            out.append(u)
    return out


def extract_candidates(
    page_url: str, html: str, *, strict_story: bool = True
) -> list[tuple[int, str, str]]:
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
    for src in parser.imgs:
        raw.append(("img", src))
    for blob in parser.json_blobs:
        for u in _urls_from_json_blob(blob):
            raw.append(("ld+json", u))
    # Full-page URL harvest (catches markdown-ish / escaped CDN links)
    for m in URL_HARVEST.finditer(html):
        u = m.group(0).rstrip("\\").rstrip(")").rstrip(";")
        u = u.replace("&amp;", "&")
        if _looks_like_image_url(u):
            raw.append(("harvest", u))

    scored: list[tuple[int, str, str]] = []
    seen_keys: set[str] = set()
    for source, u in raw:
        u = (u or "").strip()
        if not u or u.startswith("data:"):
            continue
        if u.startswith("//"):
            u = "https:" + u
        abs_u = urljoin(page_url, u)
        if not abs_u.startswith("http"):
            continue
        abs_u = abs_u.split("#")[0]
        if source in ("harvest", "ld+json", "img") and not _looks_like_image_url(abs_u):
            continue
        key = canonical_image_key(abs_u)
        if key in seen_keys:
            continue
        sc = score_candidate(abs_u, source)
        if sc < 0:
            continue
        # Prefer article lead paths over sidebar/hot-photo rails when scoring ties
        if "/cms-content/uploads/" in abs_u.lower():
            sc += 30
        if "/admin/news/" in abs_u.lower():
            sc += 30
        seen_keys.add(key)
        scored.append((sc, abs_u, source))
    scored.sort(key=lambda x: -x[0])

    # When a lead og/twitter image exists, drop unrelated related-rail photos.
    # Dispatch pages embed many cms-content thumbs for "HOT PHOTOS" / side news;
    # keep meta/link/cli always, and only keep img/harvest that share the lead's
    # upload day folder (or exact admin/news asset stem for Kakao).
    if strict_story:
        lead = ""
        for sc, u, src in scored:
            if src.startswith("og:") or src.startswith("twitter:"):
                lead = u
                break
        if lead:
            day = re.search(r"/uploads/(\d{4}/\d{2}/\d{2})/", lead, re.I)
            admin = re.search(r"(/admin/news/)([^/?#]+)", lead, re.I)
            filtered: list[tuple[int, str, str]] = []
            for sc, u, src in scored:
                if src.startswith(("og:", "twitter:", "link:", "cli:")):
                    filtered.append((sc, u, src))
                    continue
                if day and f"/uploads/{day.group(1)}/" in u.lower():
                    filtered.append((sc, u, src))
                    continue
                if (
                    admin
                    and admin.group(1).lower() in u.lower()
                    and admin.group(2).lower() in u.lower()
                ):
                    filtered.append((sc, u, src))
                    continue
                continue
            if filtered:
                scored = filtered
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


def download_image(url: str, dest_base: Path, referer: str = "") -> Path:
    req_url = url
    # Prefer full-size Kakao asset without thumb opts
    if "kakaocdn.net" in url and "type=thumb" in url:
        req_url = url.split("?")[0]

    headers = {
        "User-Agent": UA,
        "Accept": "image/*,*/*;q=0.8",
        "Accept-Language": "ko,en;q=0.8,vi;q=0.7",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(req_url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read()
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()

    ext = looks_like_image(data)
    if not ext:
        if "jpeg" in ctype or "jpg" in ctype:
            ext = ".jpg"
        elif "png" in ctype:
            ext = ".png"
        elif "webp" in ctype:
            ext = ".webp"
        elif "gif" in ctype:
            ext = ".gif"
        else:
            path_ext = Path(urlparse(url).path).suffix.lower()
            if path_ext in IMG_EXT:
                ext = path_ext
            else:
                raise ValueError(f"Not a recognized image ({ctype or 'unknown type'}): {url}")
    if len(data) < 3000:
        raise ValueError(f"Image too small ({len(data)} bytes): {url}")
    dest = dest_base.with_suffix(ext)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def content_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fetch cover and/or all article images for mm posts"
    )
    ap.add_argument("--page", help="Original article page URL (extract images)")
    ap.add_argument(
        "--image",
        action="append",
        default=[],
        help="Direct image URL (repeatable)",
    )
    ap.add_argument("--slug", required=True, help="Article slug (filename base)")
    ap.add_argument(
        "--out-dir",
        default="",
        help="Output dir under static/ (default: static/images/YYYY/MM)",
    )
    ap.add_argument("--dry-run", action="store_true", help="List candidates only")
    ap.add_argument(
        "--all",
        action="store_true",
        help="Download ALL unique content images (cover + body gallery)",
    )
    ap.add_argument(
        "--max-try",
        type=int,
        default=8,
        help="Max candidates to try in single-cover mode (default 8)",
    )
    ap.add_argument(
        "--max-images",
        type=int,
        default=30,
        help="Max images to save in --all mode (default 30)",
    )
    ap.add_argument(
        "--min-score",
        type=int,
        default=40,
        help="Min score for --all body images (default 40; cover tries lower if needed)",
    )
    ap.add_argument(
        "--loose",
        action="store_true",
        help="Do not restrict harvest/img to the lead image's date folder "
        "(may include related-rail photos)",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Force JSON stdout (implied by --all)",
    )
    args = ap.parse_args()

    if not args.page and not args.image:
        print("error: need --page and/or --image", file=sys.stderr)
        return 2

    slug = slugify(args.slug)
    out_dir = Path(args.out_dir) if args.out_dir else default_out_dir()
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    candidates: list[tuple[int, str, str]] = []
    page = (args.page or "").strip()

    for i, img in enumerate(args.image or []):
        u = img.strip()
        if u:
            candidates.append((1000 - i, u, f"cli:--image"))

    if page:
        try:
            html_b, _ctype = fetch_bytes(page)
        except urllib.error.HTTPError as e:
            print(f"error: fetch page HTTP {e.code}: {page}", file=sys.stderr)
            if not args.image:
                return 1
            html_b = b""
        except Exception as e:
            print(f"error: fetch page failed: {e}", file=sys.stderr)
            if not args.image:
                return 1
            html_b = b""
        if html_b:
            try:
                html = html_b.decode("utf-8")
            except UnicodeDecodeError:
                html = html_b.decode("euc-kr", errors="replace")
            extracted = extract_candidates(
                page, html, strict_story=not args.loose
            )
            print(f"found {len(extracted)} candidate(s) on page", file=sys.stderr)
            for sc, u, src in extracted:
                if not any(canonical_image_key(u) == canonical_image_key(c[1]) for c in candidates):
                    candidates.append((sc, u, src))

    candidates.sort(key=lambda x: -x[0])
    if not candidates:
        print("error: no image candidates found", file=sys.stderr)
        return 1

    if args.dry_run:
        for i, (sc, u, src) in enumerate(candidates[:40], 1):
            print(f"{i:2}. [{sc:4}] {src:20} {u}")
        return 0

    # ── Single cover mode (legacy) ──────────────────────────────────────────
    if not args.all:
        dest_base = out_dir / f"{slug}-cover"
        errors: list[str] = []
        for sc, url, src in candidates[: max(1, args.max_try)]:
            try:
                dest = download_image(url, dest_base, referer=page or url)
                rel = dest.relative_to(STATIC).as_posix()
                print(f"ok: saved {rel}  (from {src})", file=sys.stderr)
                if args.json:
                    print(
                        json.dumps(
                            {
                                "cover": rel,
                                "images": [
                                    {
                                        "path": rel,
                                        "source_url": url,
                                        "role": "cover",
                                        "score": sc,
                                        "from": src,
                                    }
                                ],
                            },
                            ensure_ascii=False,
                        )
                    )
                else:
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

    # ── --all: download every unique viable image ───────────────────────────
    max_n = max(1, args.max_images)
    # Prefer content-scored images; still allow high meta images
    pool = [c for c in candidates if c[0] >= args.min_score]
    if not pool:
        pool = candidates[:max_n]

    saved: list[dict] = []
    seen_hash: set[str] = set()
    errors: list[str] = []
    body_index = 0

    for sc, url, src in pool:
        if len(saved) >= max_n:
            break
        # Filename: first success = cover; rest = 01, 02, …
        if not saved:
            dest_base = out_dir / f"{slug}-cover"
            role = "cover"
        else:
            body_index += 1
            dest_base = out_dir / f"{slug}-{body_index:02d}"
            role = "body"
        try:
            dest = download_image(url, dest_base, referer=page or url)
            h = content_hash(dest)
            if h in seen_hash:
                dest.unlink(missing_ok=True)
                # rollback body index if we skipped
                if role == "body":
                    body_index -= 1
                print(f"skip: duplicate content  {url}", file=sys.stderr)
                continue
            seen_hash.add(h)
            rel = dest.relative_to(STATIC).as_posix()
            entry = {
                "path": rel,
                "source_url": url,
                "role": role,
                "score": sc,
                "from": src,
            }
            saved.append(entry)
            print(f"ok: saved {rel}  (from {src}, role={role})", file=sys.stderr)
        except Exception as e:
            if role == "body":
                body_index -= 1
            errors.append(f"{src} {url}: {e}")
            continue

    # If first tries failed for cover, try remaining lower-score candidates
    if not saved:
        for sc, url, src in candidates:
            try:
                dest = download_image(url, out_dir / f"{slug}-cover", referer=page or url)
                rel = dest.relative_to(STATIC).as_posix()
                saved.append(
                    {
                        "path": rel,
                        "source_url": url,
                        "role": "cover",
                        "score": sc,
                        "from": src,
                    }
                )
                print(f"ok: saved {rel}  (from {src}, role=cover)", file=sys.stderr)
                break
            except Exception as e:
                errors.append(f"{src} {url}: {e}")

    if not saved:
        print("error: all download attempts failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if errors:
        print(f"note: {len(errors)} candidate(s) failed download", file=sys.stderr)

    cover_path = next((x["path"] for x in saved if x["role"] == "cover"), saved[0]["path"])
    result = {
        "cover": cover_path,
        "count": len(saved),
        "images": saved,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
