#!/usr/bin/env python3
"""Localize scaffold/sample English posts → Vietnamese + host covers under static/.

Context
-------
When the blog was first scaffolded, ~40 demo posts were written in English with
remote picsum.photos covers. Those are *not* real newsroom translations of Korean
sources (unlike `mm` posts). Images look good, so we keep them as first-class
content: download covers locally and translate EN → VI.

Usage
-----
  # Preview which files would be touched
  python3 scripts/localize_sample_posts.py --dry-run

  # Download picsum covers only (no text translation)
  python3 scripts/localize_sample_posts.py --images-only

  # Full: download covers + translate title/desc/body/faq/alt/caption
  python3 scripts/localize_sample_posts.py --apply

  # One file
  python3 scripts/localize_sample_posts.py --apply --only content/en/kpop/aespa-comeback-armageddon.md

Translation backend (first available):
  1. OPENAI_API_KEY / XAI_API_KEY  → Chat Completions style HTTP
  2. deep-translator (Google free)   → pip install deep-translator
  3. --skip-translate if neither works (images still saved)

Notes
-----
- Does NOT change file path / slug (URL stable).
- Marks front matter: sample_origin: scaffold  (so you can filter later)
- Skips posts that already look Vietnamese (title has diacritics) unless --force
- Skips posts whose cover is already under static/images/ unless --force
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "en"
STATIC = ROOT / "static"
SEP = "---"
UA = "Mozilla/5.0 (compatible; KoreaWikiLocalize/1.0)"

VI_DIAC = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
    re.I,
)


def load_post(fp: Path) -> tuple[dict, str] | None:
    text = fp.read_text("utf-8")
    if not text.startswith(SEP):
        return None
    parts = text.split(SEP, 2)
    if len(parts) < 3:
        return None
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except Exception:
        return None
    body = parts[2]
    if body.startswith("\n"):
        body = body[1:]
    return meta, body


def dump_post(meta: dict, body: str) -> str:
    y = yaml.dump(
        meta,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=88,
    )
    body = body.lstrip("\n")
    if not body.endswith("\n"):
        body += "\n"
    return f"{SEP}\n{y}{SEP}\n\n{body}"


def is_vietnamese(text: str) -> bool:
    return bool(VI_DIAC.search(text or ""))


def cover_image(meta: dict) -> str:
    cover = meta.get("cover") or {}
    if isinstance(cover, dict):
        return str(cover.get("image") or "").strip()
    if isinstance(cover, str):
        return cover.strip()
    return ""


def is_sample_post(meta: dict, body: str) -> bool:
    img = cover_image(meta)
    if "picsum.photos" in img:
        return True
    if meta.get("sample_origin") == "scaffold":
        return True
    title = str(meta.get("title") or "")
    # English scaffold: no VI diacritics in title+lead, has English function words
    head = title + "\n" + body[:600]
    if is_vietnamese(head):
        return False
    if re.search(r"\b(the|and|with|from|that|this|their)\b", head, re.I):
        return True
    return False


def fetch_bytes(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def looks_like_image(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def download_cover(meta: dict, fp: Path) -> str | None:
    """Download remote cover → static/images/sample/<stem>.ext ; return rel path."""
    img = cover_image(meta)
    if not img:
        return None
    if img.startswith("images/") and not img.startswith("http"):
        # already local
        return img if (STATIC / img).exists() else None
    if not img.startswith("http"):
        return None

    # picsum redirects; follow
    slug = fp.stem
    out_dir = STATIC / "images" / "sample"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        data = fetch_bytes(img)
    except Exception as e:
        print(f"  ! download fail {img}: {e}", file=sys.stderr)
        return None
    ext = looks_like_image(data) or ".jpg"
    if len(data) < 1500:
        print(f"  ! image too small {img}", file=sys.stderr)
        return None
    dest = out_dir / f"{slug}{ext}"
    dest.write_bytes(data)
    rel = dest.relative_to(STATIC).as_posix()
    print(f"  ✓ cover → {rel} ({len(data)} bytes)")
    return rel


# ---------------------------------------------------------------------------
# Translation backends
# ---------------------------------------------------------------------------

def chunk_text(text: str, max_len: int = 4500) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    paras = re.split(r"(\n\n+)", text)
    buf = ""
    for p in paras:
        if len(buf) + len(p) > max_len and buf:
            chunks.append(buf)
            buf = p
        else:
            buf += p
    if buf:
        chunks.append(buf)
    # hard split remaining giants
    out: list[str] = []
    for c in chunks:
        if len(c) <= max_len:
            out.append(c)
            continue
        for i in range(0, len(c), max_len):
            out.append(c[i : i + max_len])
    return out


def translate_openai_compatible(text: str, api_key: str, base: str, model: str) -> str:
    """Minimal Chat Completions HTTP (OpenAI-compatible / xAI)."""
    url = base.rstrip("/") + "/chat/completions"
    system = (
        "You are a professional Vietnamese news editor for KoreaWiki. "
        "Translate the user text from English into natural Vietnamese journalistic prose. "
        "Keep Markdown structure (headings, lists, links, bold, blockquotes). "
        "Keep proper nouns (artist/group/film titles) in original form when standard; "
        "use common Vietnamese renderings where established (e.g. Hàn Quốc). "
        "Do NOT add facts. Do NOT wrap in code fences. Output only the translation."
    )
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": UA,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def translate_deep(text: str) -> str:
    from deep_translator import GoogleTranslator  # type: ignore

    tr = GoogleTranslator(source="en", target="vi")
    parts = []
    for chunk in chunk_text(text, 4500):
        if not chunk.strip():
            parts.append(chunk)
            continue
        parts.append(tr.translate(chunk))
        time.sleep(0.35)
    return "".join(parts)


class Translator:
    def __init__(self) -> None:
        self.mode = "none"
        self.api_key = ""
        self.base = ""
        self.model = ""
        xai = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
        oai = os.environ.get("OPENAI_API_KEY")
        if xai:
            self.mode = "xai"
            self.api_key = xai
            self.base = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1")
            self.model = os.environ.get("XAI_MODEL", "grok-3-mini")
        elif oai:
            self.mode = "openai"
            self.api_key = oai
            self.base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        else:
            try:
                import deep_translator  # noqa: F401

                self.mode = "deep"
            except ImportError:
                self.mode = "none"

    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return text
        if self.mode in ("xai", "openai"):
            # chunk long bodies for API
            if len(text) < 12000:
                return translate_openai_compatible(
                    text, self.api_key, self.base, self.model
                )
            out = []
            for ch in chunk_text(text, 10000):
                out.append(
                    translate_openai_compatible(
                        ch, self.api_key, self.base, self.model
                    )
                )
                time.sleep(0.5)
            return "\n\n".join(out)
        if self.mode == "deep":
            return translate_deep(text)
        raise RuntimeError(
            "No translation backend. Set XAI_API_KEY or OPENAI_API_KEY, "
            "or: pip install deep-translator"
        )


def _clean_field(s: str) -> str:
    """Drop accidental multi-line label bleed from MT."""
    s = (s or "").strip()
    # if MT echoed labels, keep first line only for short fields
    if "\n" in s and re.search(r"(?i)^(title|description|mô tả|alt|caption|faq)\s*:", s):
        s = s.split("\n", 1)[0].strip()
    # strip leading Label:
    s = re.sub(
        r"(?i)^(title|description|mô tả|alt|caption|faq)\s*:\s*",
        "",
        s,
    ).strip()
    return s


def translate_meta_and_body(meta: dict, body: str, tr: Translator) -> tuple[dict, str]:
    """Translate field-by-field (reliable for free MT that rewrites labels)."""
    meta = dict(meta)

    # body may contain article-footer shortcode — protect it
    footer_pat = re.compile(
        r"\{\{<\s*article-footer\s*>\}\}.*?\{\{<\s*/article-footer\s*>\}\}",
        re.S,
    )
    footers = footer_pat.findall(body)
    body_work = body
    for i, f in enumerate(footers):
        body_work = body_work.replace(f, f"\n\n@@FOOTER_{i}@@\n\n")

    # --- short fields one-by-one ---
    title_src = str(meta.get("title") or "")
    # If a previous broken run stuffed DESCRIPTION into title, keep first line only
    if "\n" in title_src:
        title_src = title_src.split("\n")[0].strip()
    # Re-translate only if still mostly English, else polish path: always re-translate EN-looking
    meta["title"] = _clean_field(tr.translate(title_src))

    desc_src = str(meta.get("description") or "")
    if desc_src:
        meta["description"] = _clean_field(tr.translate(desc_src))

    cover = meta.get("cover")
    if isinstance(cover, dict):
        alt = str(cover.get("alt") or "")
        cap = str(cover.get("caption") or "")
        # strip bleed from prior bad runs
        if "\n" in alt:
            alt = alt.split("\n")[0]
        if alt and not is_vietnamese(alt):
            cover["alt"] = _clean_field(tr.translate(alt))
        elif alt:
            cover["alt"] = _clean_field(alt.split("\n")[0])
        if cap and not is_vietnamese(cap):
            cover["caption"] = _clean_field(tr.translate(cap))
        elif cap:
            cover["caption"] = _clean_field(cap.split("\n")[0])
        meta["cover"] = cover

    faq = meta.get("faq")
    if isinstance(faq, list) and faq:
        new_faq = []
        for item in faq:
            if not isinstance(item, dict):
                new_faq.append(item)
                continue
            q = str(item.get("q") or "")
            a = str(item.get("a") or "")
            if q and not is_vietnamese(q):
                q = _clean_field(tr.translate(q))
            if a and not is_vietnamese(a):
                # answers can be longer — allow multiline
                a = tr.translate(a).strip()
            new_faq.append({"q": q, "a": a})
        meta["faq"] = new_faq

    # --- body ---
    # If already Vietnamese (re-run), skip re-MT to avoid double-translation mush
    if is_vietnamese(body_work[:800]) and meta.get("lang_note") == "vi-localized-from-en-scaffold":
        body_vi = body_work
    else:
        body_vi = tr.translate(body_work)

    for i, f in enumerate(footers):
        body_vi = body_vi.replace(f"@@FOOTER_{i}@@", f)
        body_vi = re.sub(rf"@@\s*FOOTER_{i}\s*@@", f, body_vi)

    if "article-footer" not in body_vi:
        body_vi = body_vi.rstrip() + (
            "\n\n{{< article-footer >}}\n"
            "copyright: >\n"
            "  Bài viết scaffold KoreaWiki (bản Việt hoá). Hình ảnh minh hoạ "
            "được host cục bộ; dùng với mục đích thông tin.\n"
            "{{< /article-footer >}}\n"
        )

    meta["sample_origin"] = "scaffold"
    meta["lang_note"] = "vi-localized-from-en-scaffold"
    return meta, body_vi


def iter_targets(only: str | None, force: bool) -> list[Path]:
    files = sorted(CONTENT.rglob("*.md"))
    out: list[Path] = []
    for fp in files:
        if fp.name == "_index.md":
            continue
        if only:
            only_p = Path(only)
            if fp.resolve() != (ROOT / only).resolve() and fp != only_p:
                if only not in fp.as_posix():
                    continue
        loaded = load_post(fp)
        if not loaded:
            continue
        meta, body = loaded
        if not force and is_vietnamese(str(meta.get("title") or "")):
            # already VI (mm posts)
            if "picsum" not in cover_image(meta):
                continue
        if not force and not is_sample_post(meta, body):
            continue
        out.append(fp)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Localize EN scaffold posts → VI + local covers")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--images-only", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--skip-translate", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0, help="Max posts to process")
    args = ap.parse_args()

    if not (args.dry_run or args.images_only or args.apply):
        ap.print_help()
        print("\nSpecify --dry-run, --images-only, or --apply", file=sys.stderr)
        return 2

    targets = iter_targets(args.only or None, args.force)
    if args.limit:
        targets = targets[: args.limit]
    print(f"Targets: {len(targets)} posts")

    tr: Translator | None = None
    if args.apply and not args.skip_translate and not args.images_only:
        tr = Translator()
        print(f"Translation backend: {tr.mode}")
        if tr.mode == "none":
            print(
                "error: no backend. Install: pip install deep-translator\n"
                "  or set XAI_API_KEY / OPENAI_API_KEY",
                file=sys.stderr,
            )
            return 1

    ok = 0
    for fp in targets:
        rel = fp.relative_to(ROOT).as_posix()
        loaded = load_post(fp)
        if not loaded:
            continue
        meta, body = loaded
        print(f"\n→ {rel}")
        print(f"  title: {str(meta.get('title') or '')[:70]}")

        if args.dry_run and not args.apply and not args.images_only:
            ok += 1
            continue

        # images
        new_cover = download_cover(meta, fp)
        if new_cover:
            cover = meta.get("cover") if isinstance(meta.get("cover"), dict) else {}
            if not isinstance(cover, dict):
                cover = {}
            cover["image"] = new_cover
            meta["cover"] = cover

        if args.images_only or args.skip_translate:
            meta["sample_origin"] = meta.get("sample_origin") or "scaffold"
            if args.apply or args.images_only:
                fp.write_text(dump_post(meta, body), encoding="utf-8")
                ok += 1
            continue

        if args.apply and tr:
            try:
                meta2, body2 = translate_meta_and_body(meta, body, tr)
            except Exception as e:
                print(f"  ! translate failed: {e}", file=sys.stderr)
                # still save cover update
                fp.write_text(dump_post(meta, body), encoding="utf-8")
                continue
            fp.write_text(dump_post(meta2, body2), encoding="utf-8")
            print("  ✓ translated + saved")
            ok += 1
            time.sleep(0.4)

    print(f"\nDone. Processed {ok}/{len(targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
