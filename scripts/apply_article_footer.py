#!/usr/bin/env python3
"""Batch-apply article-footer + front-matter FAQ ("Bài này trả lời") to all posts.

Extracts real sources/links from each article when present; generates FAQ from
title, description, and body headings/paragraphs (no invented news events).

Usage:
  python3 scripts/apply_article_footer.py --dry-run
  python3 scripts/apply_article_footer.py --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SEP = "---"

SKIP_HOSTS = (
    "picsum.photos",
    "images.unsplash.com",
    "via.placeholder.com",
    "placehold.co",
)

NGUON_RE = re.compile(
    r"(?im)^(?:\*+|_+)?\s*(?:Nguồn|Source)\s*:\s*(.+?)\s*(?:\*+|_+)?\s*$"
)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
H2_RE = re.compile(r"(?m)^##\s+(.+)$")
SENTENCE_RE = re.compile(r"(?s)(.+?[.!?…])(?:\s+|$)")


def split_fm(text: str) -> tuple[dict | None, str, str]:
    if not text.startswith(SEP):
        return None, "", text
    parts = text.split(SEP, 2)
    if len(parts) < 3:
        return None, "", text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None, parts[1], parts[2]
    if not isinstance(meta, dict):
        meta = {}
    return meta, parts[1], parts[2]


def dump_fm(meta: dict) -> str:
    return yaml.dump(
        meta,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).strip()


def first_sentences(text: str, n: int = 2, max_len: int = 320) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    out = []
    for m in SENTENCE_RE.finditer(text):
        s = m.group(1).strip()
        if len(s) < 20:
            continue
        out.append(s)
        if len(out) >= n:
            break
    blob = " ".join(out) if out else text[:max_len]
    if len(blob) > max_len:
        blob = blob[: max_len - 1].rsplit(" ", 1)[0] + "…"
    return blob


def clean_quote(s: str) -> str:
    s = (s or "").strip()
    while len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s.strip(" \"'")


def extract_source(body: str) -> tuple[str, str]:
    """Return (source_name, source_url) from Nguồn: lines or existing shortcode."""
    name, url = "", ""
    m = NGUON_RE.search(body)
    if m:
        raw = m.group(1).strip()
        url_m = re.search(r"(https?://\S+)", raw)
        url = url_m.group(1).rstrip(").,;") if url_m else ""
        name = re.sub(r"https?://\S+", "", raw)
        name = re.sub(r"\s*[—–\-]\s*$", "", name).strip(" —–-\t")
    if not name:
        m2 = re.search(r'(?m)^source:\s*["\']?(.+?)["\']?\s*$', body)
        if m2:
            name = clean_quote(m2.group(1))
    if not url:
        m3 = re.search(r'(?m)^source_url:\s*["\']?(\S+?)["\']?\s*$', body)
        if m3:
            url = m3.group(1).strip().rstrip("\"'")
    name = clean_quote(name)
    if not name and url:
        name = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    return name, url

def extract_external_links(body: str, cover_url: str = "") -> list[dict]:
    found: list[dict] = []
    seen = set()
    for title, url in MD_LINK_RE.findall(body):
        url = url.strip()
        if not url.startswith("http"):
            continue
        if any(h in url for h in SKIP_HOSTS):
            continue
        if cover_url and url in cover_url:
            continue
        if url in seen:
            continue
        seen.add(url)
        found.append({"title": title.strip() or url, "url": url})
    # bare URLs in Nguồn lines
    for m in re.finditer(r"https?://[^\s)\]>]+", body):
        url = m.group(0).rstrip(").,;\"'")
        if any(h in url for h in SKIP_HOSTS):
            continue
        if url in seen:
            continue
        seen.add(url)
        host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        found.append({"title": host, "url": url})
    return found[:8]


def related_internal(fp: Path, meta: dict, all_posts: list[dict], limit: int = 2) -> list[dict]:
    section = fp.parent.name
    slug = meta.get("slug") or fp.stem
    title = str(meta.get("title") or fp.stem)
    cands = []
    for p in all_posts:
        if p["path"] == fp:
            continue
        if p["section"] != section:
            continue
        cands.append(p)
    # same section first, then fill from others
    if len(cands) < limit:
        for p in all_posts:
            if p["path"] == fp:
                continue
            if p in cands:
                continue
            cands.append(p)
            if len(cands) >= limit + 2:
                break
    out = []
    for p in cands[:limit]:
        rel = p["path"].relative_to(CONTENT).with_suffix("")
        # content/en/kpop/foo -> en/kpop/foo/
        url = str(rel).replace("\\", "/") + "/"
        out.append({"title": p["title"], "url": url})
    return out


def build_faq(meta: dict, body: str) -> list[dict]:
    """FAQ grounded in title/description/body only."""
    title = re.sub(r"\s+", " ", str(meta.get("title") or "")).strip()
    desc = re.sub(r"\s+", " ", str(meta.get("description") or "")).strip()
    # strip shortcodes / yaml footer noise for summary
    clean = re.sub(r"\{\{<[\s\S]*?>\}\}", " ", body)
    clean = re.sub(r"(?m)^(?:Nguồn|Source):.*$", " ", clean)
    clean = re.sub(r"#+\s*", " ", clean)
    clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
    clean = re.sub(r"[*_`>]", "", clean)
    summary = first_sentences(clean, 2, 360)
    if not summary and desc:
        summary = desc

    faq: list[dict] = []

    # 1 — what is this about
    if desc:
        faq.append(
            {
                "q": "Bài viết này nói về chủ đề gì?",
                "a": desc if desc.endswith((".", "!", "?", "…")) else desc + ".",
            }
        )
    elif title:
        faq.append(
            {
                "q": "Bài viết này nói về chủ đề gì?",
                "a": f"Bài viết đề cập đến **{title}**.",
            }
        )

    # 2 — from first H2 + following paragraph
    h2s = H2_RE.findall(body)
    if h2s:
        h = h2s[0].strip()
        # paragraph after first h2
        m = re.search(
            rf"(?ms)^##\s+{re.escape(h)}\s*\n+(.+?)(?=\n##\s|\Z)",
            body,
        )
        para = ""
        if m:
            para = first_sentences(
                re.sub(r"\{\{<[\s\S]*?>\}\}", " ", m.group(1)), 2, 300
            )
        faq.append(
            {
                "q": f"Nội dung chính về «{h}» là gì?",
                "a": para
                or (
                    f"Phần **{h}** được trình bày chi tiết trong bài."
                    if not summary
                    else summary
                ),
            }
        )

    # 3 — key takeaway from body summary
    if summary and (not faq or summary != faq[0].get("a")):
        faq.append(
            {
                "q": "Điểm thông tin chính độc giả nên nhớ là gì?",
                "a": summary,
            }
        )

    # ensure 2–4 items, unique questions
    seen_q = set()
    uniq = []
    for item in faq:
        q = item["q"].strip()
        a = str(item["a"]).strip()
        if not q or not a or q in seen_q:
            continue
        seen_q.add(q)
        uniq.append({"q": q, "a": a})
        if len(uniq) >= 4:
            break

    if len(uniq) < 2 and title:
        uniq.append(
            {
                "q": f"Vì sao bài «{title[:60]}{'…' if len(title) > 60 else ''}» đáng đọc?",
                "a": desc or summary or f"Bài cập nhật thông tin xoay quanh **{title}**.",
            }
        )

    return uniq[:4]


def wrap_text(text: str, width: int = 88) -> str:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = (" ".join(cur + [w])).strip()
        if cur and len(trial) > width:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines)


def build_copyright(source: str, source_url: str, author: str) -> str:
    if source:
        link = f" [{source}]({source_url})" if source_url else f" **{source}**"
        text = (
            f"Một phần thông tin trong bài được tham khảo từ{link}. "
            "Mọi thương hiệu, hình ảnh và tài liệu gốc thuộc quyền sở hữu của chủ sở hữu tương ứng. "
            "Bài viết trên KoreaWiki chỉ tổng hợp, biên tập và phân tích phục vụ độc giả — "
            "không thay thế thông cáo hay tài liệu chính thức."
        )
        return wrap_text(text)
    who = author or "KoreaWiki Newsroom"
    text = (
        f"Bài viết do **{who}** / KoreaWiki biên soạn. "
        "Hình ảnh (nếu có) thuộc quyền sở hữu của chủ sở hữu tương ứng và được dùng với mục đích thông tin. "
        "Vui lòng dẫn nguồn khi trích dẫn."
    )
    return wrap_text(text)


def render_footer_shortcode(
    *,
    source: str,
    source_url: str,
    copyright: str,
    external: list[dict],
    internal: list[dict],
) -> str:
    lines = ["", "{{< article-footer >}}"]
    if source:
        source = clean_quote(source).replace('"', "'")
        lines.append(f'source: "{source}"')
    if source_url:
        source_url = source_url.strip().strip("\"'")
        lines.append(f'source_url: "{source_url}"')
    # copyright as folded YAML
    lines.append("copyright: >")
    for para in copyright.strip().split("\n"):
        lines.append(f"  {para.strip()}")
    if external:
        lines.append("external:")
        for e in external:
            t = str(e["title"]).replace('"', "'")
            lines.append(f'  - title: "{t}"')
            lines.append(f'    url: "{e["url"]}"')
    if internal:
        lines.append("internal:")
        for e in internal:
            t = str(e["title"]).replace('"', "'")
            lines.append(f'  - title: "{t}"')
            lines.append(f'    url: "{e["url"]}"')
    # faq comes from front matter only (answers-toc)
    lines.append("{{< /article-footer >}}")
    lines.append("")
    return "\n".join(lines)


def process_file(
    fp: Path,
    all_posts: list[dict],
    *,
    apply: bool,
) -> str:
    text = fp.read_text("utf-8")
    meta, _raw_fm, body = split_fm(text)
    if meta is None:
        return "skip: no front matter"

    already_footer = "article-footer" in body
    already_faq = bool(meta.get("faq"))

    cover = meta.get("cover") or {}
    cover_url = ""
    if isinstance(cover, dict):
        cover_url = str(cover.get("image") or "")

    source, source_url = extract_source(body)
    external = extract_external_links(body, cover_url)
    if source_url and not any(e["url"] == source_url for e in external):
        external.insert(0, {"title": source or source_url, "url": source_url})

    internal = related_internal(fp, meta, all_posts, limit=2)
    faq = meta.get("faq") if already_faq else build_faq(meta, body)
    author = str(meta.get("author") or "KoreaWiki Newsroom")
    copyright = build_copyright(source, source_url, author)

    # strip existing article-footer block for clean rewrite
    body_clean = re.sub(
        r"\n*\{\{<\s*article-footer\s*>\}\}[\s\S]*?\{\{<\s*/article-footer\s*>\}\}\s*",
        "\n",
        body,
    ).rstrip() + "\n"

    meta = dict(meta)
    meta["faq"] = faq

    footer = render_footer_shortcode(
        source=source,
        source_url=source_url,
        copyright=copyright,
        external=external,
        internal=internal,
    )
    new_text = f"{SEP}\n{dump_fm(meta)}\n{SEP}\n{body_clean}{footer}"

    rel = fp.relative_to(ROOT)
    if not apply:
        return (
            f"dry-run {rel}: faq={len(faq)} ext={len(external)} "
            f"int={len(internal)} source={source or '-'} "
            f"rewrite_footer={already_footer}"
        )

    fp.write_text(new_text, "utf-8")
    return f"updated {rel}: faq={len(faq)} ext={len(external)} int={len(internal)}"


def collect_posts() -> list[dict]:
    posts = []
    for fp in sorted(CONTENT.rglob("*.md")):
        if fp.name == "_index.md":
            continue
        meta, _, _ = split_fm(fp.read_text("utf-8"))
        if not meta:
            continue
        posts.append(
            {
                "path": fp,
                "section": fp.parent.name,
                "title": str(meta.get("title") or fp.stem),
                "slug": str(meta.get("slug") or fp.stem),
            }
        )
    return posts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write changes to disk")
    ap.add_argument("--dry-run", action="store_true", help="Print plan only (default)")
    ap.add_argument(
        "--path",
        default="",
        help="Optional glob under content/, e.g. content/en/kpop/*.md",
    )
    args = ap.parse_args()
    apply = bool(args.apply)
    if not apply:
        args.dry_run = True

    posts = collect_posts()
    targets = [p["path"] for p in posts]
    if args.path:
        from glob import glob

        globs = [Path(p) for p in glob(args.path, recursive=True)]
        targets = [p for p in targets if p in globs or str(p) in {str(g) for g in globs}]

    print(f"{'APPLY' if apply else 'DRY-RUN'} — {len(targets)} articles\n")
    for fp in targets:
        msg = process_file(fp, posts, apply=apply)
        print(msg)

    if not apply:
        print("\nRe-run with --apply to write files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
