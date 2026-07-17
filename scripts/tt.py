#!/usr/bin/env python3
"""tt — research, select and publish at most one high-demand topic.

The command is deliberately conservative.  It can research without an AI key,
but it will not publish unless it has multiple attributable sources, a clean
topic/intent check, valid generated front matter and a green site gate.

Usage:
  python3 scripts/tt.py
  python3 scripts/tt.py "chủ đề"
  python3 scripts/tt.py https://example.com/article
  python3 scripts/tt.py --dry-run
  python3 scripts/tt.py --research-only
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import textwrap
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
REPORTS = ROOT / "reports" / "tt"
SCIENTIST = ROOT / "docs" / "ai" / "scientist.md"
VN_TZ = timezone(timedelta(hours=7))
UA = "KoreaWiki-tt/1.0"
MAX_FETCH = 180_000
MIN_WORDS = int(os.getenv("TT_MIN_WORDS", "900"))
TRENDS_GEO = os.getenv("TT_TRENDS_GEO", "VN")
ALLOWED_SECTIONS = {
    "blog": "Blog",
    "news": "News",
    "culture": "Culture",
    "travel": "Travel",
    "food": "Food",
    "kdrama": "K-Drama",
    "kpop": "K-Pop",
    "society": "Society",
}
AGGREGATOR_DOMAINS = {
    "news.google.com", "trends.google.com", "google.com", "search.naver.com",
}
INTENT_WORDS = {
    "guide": {"cách", "hướng dẫn", "kinh nghiệm", "guide", "how"},
    "explain": {"là gì", "vì sao", "giải thích", "what", "why"},
    "news": {"mới nhất", "cập nhật", "xác nhận", "tin", "reported", "update"},
    "review": {"đánh giá", "review", "nhận xét", "xếp hạng"},
    "list": {"top", "danh sách", "gợi ý", "best", "địa điểm"},
}


@dataclass
class Source:
    title: str
    url: str
    publisher: str
    published: str = ""
    description: str = ""
    text: str = ""
    trusted: bool = False


@dataclass
class Candidate:
    topic: str
    query: str
    sources: list[Source]
    gsc: dict[str, Any]
    trend: dict[str, Any] | None = None
    score: float = 0.0
    duplicate: str = ""
    evidence: list[str] | None = None


def now_vn() -> datetime:
    return datetime.now(VN_TZ)


def run(cmd: list[str], *, check: bool = True, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)


def git(cmd: list[str], *, check: bool = True) -> str:
    return run(["git", *cmd], check=check).stdout.strip()


def clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", value).strip()


def fetch(url: str, timeout: int = 20) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "vi,en;q=0.8,ko;q=0.6"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read(MAX_FETCH)
        charset = response.headers.get_content_charset() or "utf-8"
        return data.decode(charset, errors="replace"), response.geturl()


def domain(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host


def usable_source(url: str) -> bool:
    host = domain(url)
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and host not in AGGREGATOR_DOMAINS


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")[:100]


def tokens(value: str) -> set[str]:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]{3,}", value)
    stop = {"the", "and", "for", "with", "from", "this", "that", "korea", "han", "quoc", "viet"}
    return {w for w in words if w not in stop}


def similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def intent(value: str) -> str:
    lowered = value.lower()
    scores = {key: sum(1 for word in words if word in lowered) for key, words in INTENT_WORDS.items()}
    return max(scores, key=scores.get) if max(scores.values()) else "news"


def html_metadata(raw: str) -> tuple[str, str, str, str]:
    def meta(*names: str) -> str:
        for name in names:
            pattern = rf"<meta[^>]+(?:name|property)=[\"']{re.escape(name)}[\"'][^>]+content=[\"']([^\"']+)"
            m = re.search(pattern, raw, re.I)
            if m:
                return clean_text(m.group(1))
            pattern = rf"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+(?:name|property)=[\"']{re.escape(name)}[\"']"
            m = re.search(pattern, raw, re.I)
            if m:
                return clean_text(m.group(1))
        return ""

    title = meta("og:title", "twitter:title")
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
        title = clean_text(m.group(1)) if m else ""
    description = meta("description", "og:description", "twitter:description")
    published = meta("article:published_time", "datePublished", "date")
    author = meta("author", "article:author")
    body_match = re.search(r"<(?:article|main)[^>]*>(.*?)</(?:article|main)>", raw, re.I | re.S)
    body = clean_text(body_match.group(1) if body_match else raw)
    return title, description, published, author + " " + body[:8000]


def source_from_url(url: str) -> Source | None:
    try:
        raw, final_url = fetch(url)
        title, description, published, body = html_metadata(raw)
        if not title:
            return None
        return Source(title, final_url, domain(final_url), published, description, body, usable_source(final_url))
    except Exception as exc:
        print(f"TT source fetch skipped: {url} ({exc})", file=sys.stderr)
        return None


def rss_sources(url: str, limit: int = 12) -> list[Source]:
    try:
        raw, _ = fetch(url)
        root = ET.fromstring(raw)
    except Exception as exc:
        print(f"TT RSS skipped: {url} ({exc})", file=sys.stderr)
        return []
    results: list[Source] = []
    for item in root.findall(".//item")[:limit]:
        title = clean_text(item.findtext("title", ""))
        link = clean_text(item.findtext("link", ""))
        description = clean_text(item.findtext("description", ""))
        published = clean_text(item.findtext("pubDate", ""))
        source_node = item.find("source")
        publisher = clean_text(source_node.text if source_node is not None else domain(link))
        source_url = source_node.get("url", link) if source_node is not None else link
        if title and link:
            results.append(Source(title, source_url or link, publisher, published, description, description, usable_source(source_url or link)))
    return results


def search_sources(query: str, limit: int = 10) -> list[Source]:
    encoded = urllib.parse.quote_plus(query)
    feeds = [
        f"https://news.google.com/rss/search?q={encoded}&hl=vi&gl=VN&ceid=VN:vi",
        f"https://news.google.com/rss/search?q={encoded}&hl=en&gl=US&ceid=US:en",
    ]
    found: list[Source] = []
    seen: set[str] = set()
    for feed in feeds:
        for item in rss_sources(feed, limit):
            key = re.sub(r"\W", "", item.title.lower())
            if key not in seen:
                seen.add(key)
                found.append(item)
    # Naver remains a supplemental source discovery endpoint.  It is not used
    # as a trend score and facts still come only from the linked publisher.
    try:
        naver_url = "https://search.naver.com/search.naver?where=news&query=" + encoded
        raw, final_url = fetch(naver_url, timeout=12)
        for title, link in re.findall(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', raw, re.I | re.S):
            title = clean_text(title)
            if len(title) > 15 and usable_source(link):
                key = re.sub(r"\W", "", title.lower())
                if key not in seen:
                    seen.add(key)
                    found.append(Source(title, link, domain(link), "", "Naver news result", "Naver news result", usable_source(link)))
    except Exception as exc:
        print(f"TT Naver signal skipped: {exc}", file=sys.stderr)
    return found[:limit]


def google_trends_topics(geo: str = "VN", limit: int = 20) -> list[dict[str, Any]]:
    """Return current Google Trends topics as demand signals, not fact sources."""
    url = f"https://trends.google.com/trending/rss?geo={urllib.parse.quote(geo)}"
    try:
        raw, _ = fetch(url, timeout=20)
        root = ET.fromstring(raw)
    except Exception as exc:
        print(f"TT Google Trends skipped: {exc}", file=sys.stderr)
        return []
    topics: list[dict[str, Any]] = []
    for item in root.findall(".//item")[:limit]:
        title = clean_text(item.findtext("title", ""))
        traffic = clean_text(item.findtext("{https://trends.google.com/trending/rss}approx_traffic", ""))
        published = clean_text(item.findtext("pubDate", ""))
        if title:
            topics.append({"title": title, "traffic": traffic, "published": published, "geo": geo})
    return topics


def load_gsc() -> list[dict[str, Any]]:
    raw = os.getenv("TT_GSC_QUERIES_JSON", "")
    path = os.getenv("TT_GSC_QUERIES_FILE", "")
    if not raw and path:
        try:
            raw = Path(path).read_text("utf-8")
        except OSError:
            return []
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            data = data.get("rows", data.get("queries", []))
        return [row for row in data if isinstance(row, dict)]
    except json.JSONDecodeError:
        print("TT: invalid TT_GSC_QUERIES_JSON; continuing without GSC", file=sys.stderr)
        return []


def gsc_match(topic: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    best: dict[str, Any] = {}
    topic_tokens = tokens(topic)
    for row in rows:
        query = str(row.get("query", row.get("keys", [""])[0] if isinstance(row.get("keys"), list) else ""))
        if similarity(topic_tokens, tokens(query)) > similarity(topic_tokens, tokens(str(best.get("query", "")))):
            best = {"query": query, "clicks": row.get("clicks", 0), "impressions": row.get("impressions", 0), "position": row.get("position", "")}
    return best


def read_frontmatter(fp: Path) -> tuple[dict[str, Any], str]:
    parts = fp.read_text("utf-8").split("---", 2)
    if len(parts) != 3:
        return {}, ""
    try:
        return yaml.safe_load(parts[1]) or {}, parts[2]
    except yaml.YAMLError:
        return {}, parts[2]


def history_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md":
            continue
        meta, body = read_frontmatter(fp)
        if meta:
            records.append({"kind": "content", "path": str(fp.relative_to(ROOT)), "title": meta.get("title", ""), "description": meta.get("description", ""), "slug": meta.get("slug", fp.stem), "keywords": meta.get("keywords", []), "tags": meta.get("tags", []), "text": body})
    for fp in REPORTS.rglob("*.md") if REPORTS.exists() else []:
        meta, body = read_frontmatter(fp)
        if meta.get("kind") == "tt-report":
            records.append({"kind": "tt", "path": str(fp.relative_to(ROOT)), "title": meta.get("topic", ""), "slug": meta.get("topic_key", ""), "keywords": meta.get("keywords", []), "tags": [], "text": body})
    return records


def duplicate_reason(topic: str, records: list[dict[str, Any]], keywords: list[str] | None = None) -> str:
    topic_terms = tokens(" ".join([topic, *(keywords or [])]))
    topic_intent = intent(topic)
    for record in records:
        other = tokens(" ".join([str(record.get("title", "")), str(record.get("description", "")), *[str(x) for x in record.get("keywords", [])], *[str(x) for x in record.get("tags", [])], str(record.get("text", ""))[:2400]]))
        score = similarity(topic_terms, other)
        title_score = similarity(tokens(topic), tokens(str(record.get("title", ""))))
        if title_score >= 0.7 or score >= 0.62:
            return f"high overlap {score:.2f} with {record['path']}"
        if intent(topic) == topic_intent and score >= 0.42:
            return f"same {topic_intent} intent; overlap {score:.2f} with {record['path']}"
    return ""


def candidate_score(candidate: Candidate) -> float:
    unique_publishers = {domain(source.url) for source in candidate.sources if source.trusted}
    score = min(len(unique_publishers), 4) * 20
    score += min(len(candidate.sources), 6) * 4
    if candidate.trend:
        traffic = str(candidate.trend.get("traffic", "")).lower().replace(",", "").replace("+", "")
        multiplier = 1
        if traffic.endswith("k"):
            multiplier, traffic = 1_000, traffic[:-1]
        elif traffic.endswith("m"):
            multiplier, traffic = 1_000_000, traffic[:-1]
        try:
            score += min(float(traffic) * multiplier / 10_000, 40)
        except ValueError:
            score += 5
    if candidate.gsc:
        try:
            score += min(float(candidate.gsc.get("impressions", 0)) / 100, 25)
            score += min(float(candidate.gsc.get("clicks", 0)) / 10, 10)
        except (TypeError, ValueError):
            pass
    candidate.score = round(score, 2)
    return candidate.score


def research(input_text: str, records: list[dict[str, Any]]) -> tuple[list[Candidate], list[str]]:
    gsc_rows = load_gsc()
    notes: list[str] = []
    candidates: list[Candidate] = []
    if input_text.startswith(("http://", "https://")):
        primary = source_from_url(input_text)
        if not primary:
            return [], [f"Không đọc được URL: {input_text}"]
        related = search_sources(primary.title, 10)
        sources = [primary] + [s for s in related if domain(s.url) != domain(primary.url)][:7]
        candidates.append(Candidate(primary.title, primary.title, sources, gsc_match(primary.title, gsc_rows)))
    else:
        trend_topics = [] if input_text else google_trends_topics(TRENDS_GEO, 20)
        queries = [input_text] if input_text else [
            "xu hướng đang được quan tâm tại Việt Nam",
            "tin tức nổi bật hôm nay Việt Nam",
            "trending latest news worldwide",
        ]
        all_sources: list[Source] = []
        if trend_topics:
            for trend in trend_topics:
                sources = search_sources(str(trend["title"]), 10)
                if sources:
                    candidates.append(Candidate(str(trend["title"]), str(trend["title"]), sources, gsc_match(str(trend["title"]), gsc_rows), trend=trend))
        else:
            for query in queries:
                all_sources.extend(search_sources(query, 10))
        seen: set[str] = set()
        for source in all_sources:
            key = re.sub(r"\W", "", source.title.lower())
            if key in seen:
                continue
            seen.add(key)
            related = [s for s in all_sources if s is not source and similarity(tokens(source.title), tokens(s.title)) >= 0.18]
            sources = [source] + related[:7]
            candidates.append(Candidate(source.title, input_text or source.title, sources, gsc_match(source.title, gsc_rows)))
    for candidate in candidates:
        candidate.duplicate = duplicate_reason(candidate.topic, records)
        candidate.evidence = [f"{len({domain(s.url) for s in candidate.sources if s.trusted})} independent source domain(s)", f"{len(candidate.sources)} fetched source(s)"]
        if candidate.trend:
            candidate.evidence.append(f"Google Trends {candidate.trend.get('geo', 'VN')}: {candidate.trend.get('traffic') or 'current topic'}")
        if candidate.gsc:
            candidate.evidence.append(f"GSC query {candidate.gsc.get('query')} — {candidate.gsc.get('impressions', 0)} impressions")
        candidate_score(candidate)
    candidates.sort(key=lambda c: c.score, reverse=True)
    if not gsc_rows:
        notes.append("Không có dữ liệu GSC; ưu tiên Google Trends Việt Nam, sau đó đối chiếu Google News/Naver với nguồn publisher ở bất kỳ domain nào.")
    else:
        notes.append(f"Đã dùng {len(gsc_rows)} dòng dữ liệu GSC được cấp qua GitHub Secret.")
    return candidates, notes


def pick(candidates: list[Candidate]) -> Candidate | None:
    for candidate in candidates:
        source_domains = {domain(s.url) for s in candidate.sources if s.trusted}
        if len(source_domains) < 2:
            continue
        if candidate.duplicate:
            continue
        return candidate
    return None


def scientist_gate() -> str:
    if not SCIENTIST.exists():
        return "scientist.md absent — không có checklist scientist để chạy"
    text = SCIENTIST.read_text("utf-8").lower()
    required = ["nguồn", "trùng", "qa", "hugo", "ảnh"]
    missing = [word for word in required if word not in text]
    return "scientist checklist passed" if not missing else "scientist checklist missing: " + ", ".join(missing)


def prompt_for(candidate: Candidate, section: str | None) -> str:
    source_context = []
    for source in candidate.sources[:6]:
        source_context.append(json.dumps({"title": source.title, "publisher": source.publisher, "url": source.url, "published": source.published, "description": source.description[:900], "extract": source.text[:1800]}, ensure_ascii=False))
    allowed = ", ".join(ALLOWED_SECTIONS.values())
    return f"""Bạn là biên tập viên KoreaWiki. Viết một bài tiếng Việt nguyên bản, khách quan về bất kỳ chủ đề đang có nhu cầu tìm kiếm cao.

Chủ đề: {candidate.topic}
Chuyên mục được ưu tiên: {section or 'tự chọn trong danh sách'}
Các chuyên mục được phép: {allowed}
Nguồn nghiên cứu (chỉ được dùng dữ kiện có trong các nguồn này):
{chr(10).join(source_context)}

Trả về duy nhất JSON hợp lệ với các khóa:
title (10-120 ký tự), description (50-160 ký tự), summary (mảng 3 câu), category (một giá trị trong danh sách), tags (3-8 chuỗi), keywords (3-8 chuỗi), body (Markdown tiếng Việt tối thiểu {MIN_WORDS} từ), faq (mảng 2-4 object q/a).

Quy tắc: không bịa ngày, số liệu, tên, trích dẫn, diễn biến hoặc nguồn; nếu nguồn không nói thì bỏ qua. Không dịch sát, không sao chép cấu trúc nguồn. Body không được có front matter, shortcode article-footer, khối nguồn cuối bài, URL nguồn, wire byline hoặc ảnh. Dùng heading Markdown rõ ràng; phần mở đầu trả lời đúng intent tìm kiếm. Không dùng markdown HTML nguy hiểm."""


def call_ai(prompt: str) -> dict[str, Any]:
    provider = os.getenv("TT_PROVIDER", "").lower()
    openai_key = os.getenv("TT_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("TT_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    gemini_key = os.getenv("TT_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if provider in ("anthropic", "claude") or (not provider and anthropic_key and not openai_key):
        if not anthropic_key:
            raise RuntimeError("Thiếu TT_ANTHROPIC_API_KEY")
        body = json.dumps({"model": os.getenv("TT_ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"), "max_tokens": 6000, "temperature": 0.2, "system": "Chỉ trả về JSON hợp lệ.", "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={"content-type": "application/json", "x-api-key": anthropic_key, "anthropic-version": "2023-06-01"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read())
        text = data["content"][0]["text"]
    elif provider in ("gemini", "google") or (not provider and gemini_key and not openai_key):
        if not gemini_key:
            raise RuntimeError("Thiếu TT_GEMINI_API_KEY")
        model = os.getenv("TT_GEMINI_MODEL", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model)}:generateContent?key={urllib.parse.quote(gemini_key)}"
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}).encode()
        req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read())
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    else:
        if not openai_key:
            raise RuntimeError("Thiếu AI secret: TT_OPENAI_API_KEY, TT_ANTHROPIC_API_KEY hoặc TT_GEMINI_API_KEY")
        endpoint = os.getenv("TT_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        body = json.dumps({"model": os.getenv("TT_OPENAI_MODEL", "gpt-4o-mini"), "temperature": 0.2, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": "Chỉ trả về JSON hợp lệ."}, {"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(endpoint, data=body, headers={"content-type": "application/json", "authorization": f"Bearer {openai_key}"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read())
        text = data["choices"][0]["message"]["content"]
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("AI response không phải object JSON")
    return result


def validate_article(article: dict[str, Any], candidate: Candidate, records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    required = ["title", "description", "summary", "category", "tags", "keywords", "body", "faq"]
    errors.extend(f"missing {key}" for key in required if not article.get(key))
    title = str(article.get("title", ""))
    description = str(article.get("description", ""))
    body = str(article.get("body", ""))
    if not 10 <= len(title) <= 120:
        errors.append("title length invalid")
    if not 50 <= len(description) <= 320:
        errors.append("description length invalid")
    if len(body.split()) < MIN_WORDS:
        errors.append(f"body has fewer than {MIN_WORDS} words")
    if re.search(r"article-footer|^---$|https?://|wire|dispatch\s*=", body, re.I | re.M):
        errors.append("body contains forbidden footer/source/front matter pattern")
    category = str(article.get("category", ""))
    if category not in ALLOWED_SECTIONS.values():
        errors.append("invalid category")
    if not isinstance(article.get("tags"), list) or not isinstance(article.get("keywords"), list):
        errors.append("tags/keywords must be arrays")
    if duplicate_reason(title, records, [str(x) for x in article.get("keywords", [])]):
        errors.append("title/keywords collide with existing topic or intent")
    for source in candidate.sources[:2]:
        if source.url not in " ".join(str(article.get("body", ""))):
            continue
    return errors


def internal_links(candidate: Candidate, category: str) -> list[dict[str, str]]:
    scored: list[tuple[float, Path, dict[str, Any]]] = []
    for fp in CONTENT.rglob("*.md"):
        if fp.name == "_index.md":
            continue
        meta, _ = read_frontmatter(fp)
        if not meta:
            continue
        terms = tokens(" ".join([str(meta.get("title", "")), *[str(x) for x in meta.get("tags", [])], *[str(x) for x in meta.get("keywords", [])]]))
        score = similarity(tokens(candidate.topic), terms) + (0.2 if category in [str(x) for x in meta.get("categories", [])] else 0)
        scored.append((score, fp, meta))
    links: list[dict[str, str]] = []
    for _, fp, meta in sorted(scored, key=lambda item: item[0], reverse=True)[:3]:
        rel = fp.relative_to(CONTENT).with_suffix("")
        links.append({"title": str(meta.get("title", fp.stem)), "url": "/" + str(rel).replace(os.sep, "/") + "/"})
    return links[:2]


def yaml_scalar(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def make_article(article: dict[str, Any], candidate: Candidate, section: str | None, accessed: datetime) -> tuple[Path, str]:
    category = str(article["category"])
    section_key = section or next((key for key, label in ALLOWED_SECTIONS.items() if label == category), "news")
    slug = slugify(str(article["title"]))
    path = CONTENT / section_key / f"{slug}.md"
    if path.exists():
        raise RuntimeError(f"slug đã tồn tại: {path}")
    summaries = [str(x) for x in article["summary"]][:5]
    tags = [str(x) for x in article["tags"]][:8]
    keywords = [str(x) for x in article["keywords"]][:8]
    faq = article.get("faq", [])[:4]
    primary = candidate.sources[0]
    lines = [
        "---",
        f"title: {yaml_scalar(article['title'])}",
        f"description: {yaml_scalar(article['description'])}",
        "keywords:", *[f"  - {yaml_scalar(x)}" for x in keywords],
        f"date: {accessed.isoformat()}",
        f"lastmod: {accessed.date().isoformat()}",
        "draft: false",
        'author: "KoreaWiki Team"',
        "tags:", *[f"  - {yaml_scalar(x)}" for x in tags],
        "categories:", f"  - {yaml_scalar(category)}",
        "showToc: true",
        "readingTime: true",
        f"slug: {yaml_scalar(slug)}",
        "summaries:", *[f"  - {yaml_scalar(x)}" for x in summaries],
        f"source_url: {yaml_scalar(primary.url)}",
        f"source_label: {yaml_scalar(primary.publisher or domain(primary.url))}",
        "internal_links:",
    ]
    for link in internal_links(candidate, category):
        lines.extend([f"  - title: {yaml_scalar(link['title'])}", f"    url: {yaml_scalar(link['url'])}"])
    lines.extend(["external_links:"])
    for source in candidate.sources[:6]:
        lines.extend([f"  - title: {yaml_scalar(source.title)}", f"    url: {yaml_scalar(source.url)}"])
    lines.extend(["faq:"])
    for item in faq:
        if isinstance(item, dict) and item.get("q") and item.get("a"):
            lines.extend([f"  - q: {yaml_scalar(item['q'])}", f"    a: {yaml_scalar(item['a'])}"])
    lines.extend(["image:", '  status: "not-used"', '  reason: "Không có ảnh có license rõ ràng được xác minh trong nguồn nghiên cứu."', "---", "", article["body"].strip(), ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), "utf-8")
    return path, slug


def run_qa() -> list[str]:
    commands = [
        [sys.executable, "scripts/pre_deploy.py"],
        [sys.executable, "scripts/qa.py"],
        [sys.executable, "scripts/seo.py"],
        [sys.executable, "scripts/frontmatter_check.py"],
        [sys.executable, "scripts/markdown_lint.py"],
        [sys.executable, "scripts/slug.py", "--check"],
        [sys.executable, "scripts/check_links.py"],
        [sys.executable, "scripts/optimize_images.py"],
    ]
    failures: list[str] = []
    for command in commands:
        result = run(command, check=False)
        if result.returncode:
            failures.append(f"{' '.join(command)}\n{result.stdout[-1800:]}\n{result.stderr[-1800:]}")
    return failures


def run_build_gate() -> list[str]:
    """Build the real site and validate generated post-build/search artifacts."""
    failures: list[str] = []
    commands = [
        ["hugo", "--minify", "--gc"],
        [sys.executable, "scripts/pre_deploy.py", "--postbuild"],
        ["npx", "pagefind", "--site", "public"],
        [sys.executable, "scripts/generate_schema.py"],
    ]
    for command in commands:
        result = run(command, check=False)
        if result.returncode:
            failures.append(f"{' '.join(command)}\n{result.stdout[-1800:]}\n{result.stderr[-1800:]}")
            break
    for artifact in (ROOT / "public" / "sitemap.xml", ROOT / "public" / "index.xml"):
        if not artifact.exists():
            failures.append(f"missing generated artifact: {artifact.relative_to(ROOT)}")
    return failures


def write_report(path: Path, *, status: str, trigger: str, candidates: list[Candidate], selected: Candidate | None, notes: list[str], duplicate: str, article_path: str = "", qa: list[str] | None = None, build: str = "not-run", commit: str = "not-run", push: str = "not-run", image: str = "not-used") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selected_topic = selected.topic if selected else ""
    topic_key = slugify(selected_topic) if selected_topic else ""
    keywords = selected.gsc.get("query", "") if selected else ""
    lines = [
        "---", "kind: tt-report", f"status: {yaml_scalar(status)}", f"generated_at: {yaml_scalar(now_vn().isoformat())}", f"trigger: {yaml_scalar(trigger)}", f"topic: {yaml_scalar(selected_topic)}", f"topic_key: {yaml_scalar(topic_key)}", f"keywords: {yaml_scalar(keywords)}", "---", "",
        f"# TT report — {status}", "", f"- Thời gian GMT+7: `{now_vn().isoformat()}`", f"- Trigger: `{trigger}`", f"- Topic đã chọn: {selected_topic or 'Không có'}", f"- Đường dẫn bài: `{article_path or 'Không xuất bản'}`", f"- Trạng thái ảnh: `{image}`", f"- Scientist: `{scientist_gate()}`", "", "## Topic candidates", "",
    ]
    if candidates:
        lines.extend(["| Chủ đề | Điểm organic | Nguồn độc lập | Trùng/cannibalization |", "|---|---:|---:|---|"])
        for item in candidates[:20]:
            lines.append(f"| {item.topic.replace('|', ' ')} | {item.score} | {len({domain(s.url) for s in item.sources if s.trusted})} | {item.duplicate or 'Không phát hiện'} |")
    else:
        lines.append("Không thu được candidate từ nguồn nghiên cứu.")
    lines.extend(["", "## Organic evidence", "", *[f"- {note}" for note in notes], "- Thứ tự tín hiệu: GSC nếu có, Google Trends Việt Nam, rồi đối chiếu Google News/Naver và publisher domain độc lập.", "", "## Sources", ""])
    if selected:
        for source in selected.sources[:8]:
            lines.append(f"- [{source.title}]({source.url}) — {source.publisher}; published: {source.published or 'không xác định'}; usable publisher source: `{source.trusted}`")
    else:
        lines.append("Không có nguồn được chọn.")
    lines.extend(["", "## Duplicate/intent check", "", f"- Kết quả: `{duplicate or 'passed / no collision'}`", "", "## QA / build / delivery", "", f"- QA: `{('passed' if qa == [] else 'failed' if qa else 'not-run')}`"])
    if qa:
        lines.extend(["```text", "\n".join(qa), "```"])
    lines.extend([f"- Hugo build: `{build}`", f"- Commit: `{commit}`", f"- Push/deploy: `{push}`", ""])
    path.write_text("\n".join(lines), "utf-8")


def preflight(dry_run: bool) -> tuple[str, list[str]]:
    branch = git(["branch", "--show-current"])
    default_ref = git(["symbolic-ref", "refs/remotes/origin/HEAD"], check=False)
    default = default_ref.rsplit("/", 1)[-1] if default_ref else "main"
    status = git(["status", "--porcelain"])
    if not dry_run and (branch != default or status):
        raise RuntimeError(f"publish requires clean default branch; branch={branch}, default={default}, dirty={bool(status)}")
    return branch, status.splitlines() if status else []


def main() -> int:
    parser = argparse.ArgumentParser(prog="tt", description="Research and publish one high-demand topic.")
    parser.add_argument("topic", nargs="*", help="any topic or source URL")
    parser.add_argument("--dry-run", action="store_true", help="research and report only")
    parser.add_argument("--research-only", action="store_true", help="research and report only, without article generation")
    parser.add_argument("--section", choices=sorted(ALLOWED_SECTIONS), help="force Hugo section")
    args = parser.parse_args()
    trigger = " ".join(args.topic).strip() or ("--dry-run" if args.dry_run else "schedule/manual")
    if args.topic and len(args.topic) == 1 and args.topic[0] in ("--dry-run", "--research-only"):
        args.dry_run = args.topic[0] == "--dry-run"
        args.research_only = args.topic[0] == "--research-only"
        trigger = args.topic[0]
    timestamp = now_vn().strftime("%Y%m%d-%H%M%S")
    report_path = REPORTS / now_vn().strftime("%Y/%m") / f"tt-{timestamp}.md"
    candidates: list[Candidate] = []
    selected: Candidate | None = None
    notes: list[str] = []
    qa_failures: list[str] = []
    try:
        preflight(args.dry_run or args.research_only)
        records = history_records()
        candidates, notes = research(" ".join(args.topic).strip(), records)
        selected = pick(candidates)
        if not selected:
            write_report(report_path, status="skipped", trigger=trigger, candidates=candidates, selected=None, notes=notes, duplicate="Không có candidate vừa đủ nguồn tin cậy và không trùng intent.")
            print(f"TT_STATUS=skipped\nTT_REPORT={report_path.relative_to(ROOT)}")
            return 0
        if args.dry_run or args.research_only:
            write_report(report_path, status="researched", trigger=trigger, candidates=candidates, selected=selected, notes=notes, duplicate=selected.duplicate)
            print(f"TT_STATUS=researched\nTT_TOPIC={selected.topic}\nTT_REPORT={report_path.relative_to(ROOT)}")
            return 0
        if scientist_gate() != "scientist checklist passed":
            raise RuntimeError(scientist_gate())
        article = call_ai(prompt_for(selected, args.section))
        errors = validate_article(article, selected, records)
        if errors:
            raise RuntimeError("AI article validation failed: " + "; ".join(errors))
        article_path, slug = make_article(article, selected, args.section, now_vn())
        qa_failures: list[str] = []
        for attempt in range(1, 4):
            qa_failures = run_qa()
            if not qa_failures:
                qa_failures = run_build_gate()
                if not qa_failures:
                    break
            print(f"TT QA attempt {attempt}/3 failed", file=sys.stderr)
            if attempt < 3:
                run([sys.executable, "scripts/markdown_lint.py", "--fix"], check=False)
                run([sys.executable, "scripts/slug.py"], check=False)
        if qa_failures:
            raise RuntimeError("QA failed after 3 safe rounds")
        write_report(report_path, status="published-ready", trigger=trigger, candidates=candidates, selected=selected, notes=notes, duplicate="passed", article_path=str(article_path.relative_to(ROOT)), qa=[], build="pending workflow pre_deploy/Hugo", image="not-used")
        print(f"TT_STATUS=published\nTT_SLUG={slug}\nTT_ARTICLE={article_path.relative_to(ROOT)}\nTT_REPORT={report_path.relative_to(ROOT)}")
        return 0
    except Exception as exc:
        write_report(report_path, status="failed", trigger=trigger, candidates=candidates, selected=selected, notes=notes, duplicate=str(exc), qa=qa_failures or None, build="failed")
        print(f"TT_STATUS=failed\nTT_REPORT={report_path.relative_to(ROOT)}\nTT_ERROR={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
