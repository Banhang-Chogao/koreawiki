#!/usr/bin/env python3
"""Validate the universal article footer and its source/credit data."""

import html
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

CONTENT = Path("content")
PUBLIC = Path("public")
SEP = "---"
PLACEHOLDERS = {"", "null", "none", "unknown", "n/a", "na", "tbd", "todo"}
MANUAL_BLOCK = re.compile(
    r"^\s{0,3}#{1,6}\s+.*(?:bản quyền|ghi nguồn|nguồn tham khảo|tham khảo|sources?|credits?|references?)\b",
    re.IGNORECASE | re.MULTILINE,
)
SHORTCODE_BLOCK = re.compile(r"\{\{<\s*/?\s*article-footer\b", re.IGNORECASE)


def extract_front_matter(text):
    parts = text.split(SEP)
    if len(parts) < 3:
        return None, ""
    try:
        return yaml.safe_load(parts[1]) or {}, parts[2]
    except yaml.YAMLError:
        return None, ""


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def placeholder(value):
    return clean(value).casefold() in PLACEHOLDERS


def valid_http_url(value):
    url = clean(value)
    parsed = urlparse(url)
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and not any(char.isspace() for char in url)
        and not placeholder(url)
        and parsed.netloc.casefold() not in {"example.com", "example.org", "example.net"}
    )


def check_named_urls(items, label, rel):
    issues = []
    if items is None:
        return issues
    if not isinstance(items, list):
        return [f"{rel}: {label} must be a list"]
    seen = set()
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            issues.append(f"{rel}: {label}[{index}] must be an object")
            continue
        name = clean(item.get("name", item.get("title")))
        url = clean(item.get("url"))
        if placeholder(name):
            issues.append(f"{rel}: {label}[{index}] has empty/placeholder name")
        if not valid_http_url(url):
            issues.append(f"{rel}: {label}[{index}] has invalid URL: {url or '<empty>'}")
        key = url.casefold()
        if key in seen:
            issues.append(f"{rel}: duplicate {label} URL: {url}")
        seen.add(key)
    return issues


def check_legacy_source(meta, rel):
    issues = []
    legacy_keys = {key for key in ("source", "source_label", "source_url") if key in meta}
    if not legacy_keys:
        return issues
    issues.append(f"{rel}: migrate legacy source fields to sources[{name,url}]")
    return issues


def check_image_credits(meta, rel):
    issues = []
    credits = meta.get("image_credits", meta.get("image_credit"))
    if credits is None:
        return issues
    if isinstance(credits, dict):
        credits = [credits]
    if not isinstance(credits, list):
        return [f"{rel}: image_credits must be an object or list"]
    seen = set()
    for index, item in enumerate(credits, 1):
        if not isinstance(item, dict):
            issues.append(f"{rel}: image_credits[{index}] must be an object")
            continue
        platform = clean(item.get("platform", item.get("source")))
        photographer = clean(item.get("photographer", item.get("author", item.get("creator"))))
        author_url = clean(item.get("author_url", item.get("photographer_url", item.get("creator_url"))))
        license_name = clean(item.get("license"))
        if not any((platform, photographer, author_url, license_name)):
            issues.append(f"{rel}: image_credits[{index}] is empty")
        for field, value in (("platform", platform), ("photographer", photographer), ("license", license_name)):
            if value and placeholder(value):
                issues.append(f"{rel}: image_credits[{index}] has placeholder {field}")
        if author_url and not valid_http_url(author_url):
            issues.append(f"{rel}: image_credits[{index}] has invalid author URL: {author_url}")
        key = "|".join(value.casefold() for value in (platform, photographer, author_url, license_name))
        if key in seen:
            issues.append(f"{rel}: duplicate image credit at index {index}")
        seen.add(key)
    return issues


def content_checks():
    issues = []
    pages = []
    for path in sorted(CONTENT.rglob("*.md")):
        if path.name == "_index.md":
            continue
        rel = path.relative_to(CONTENT)
        text = path.read_text("utf-8")
        meta, body = extract_front_matter(text)
        if meta is None:
            issues.append(f"{rel}: invalid front matter")
            continue
        if MANUAL_BLOCK.search(body) or SHORTCODE_BLOCK.search(body):
            issues.append(f"{rel}: manual copyright/source/footer block found")
        if "sources" in meta:
            issues.extend(check_named_urls(meta.get("sources"), "sources", rel))
        issues.extend(check_legacy_source(meta, rel))
        issues.extend(check_named_urls(meta.get("external_links"), "external_links", rel))
        issues.extend(check_image_credits(meta, rel))
        pages.append((rel, meta))
    return issues, pages


def check_external_links(html_text, rel):
    issues = []
    footer_match = re.search(r'<aside\b[^>]*data-article-footer(?:\s|=|>)[^>]*>(.*?)</aside>', html_text, re.DOTALL)
    if not footer_match:
        return [f"{rel}: universal article footer was not rendered"]
    footer = footer_match.group(1)
    for tag in re.findall(r"<a\b[^>]*>", footer, re.IGNORECASE):
        href_match = re.search(r'href=(?:"(https?://[^"]+)"|(https?://[^\s>]+))', tag, re.IGNORECASE)
        if not href_match:
            continue
        anchor = href_match.group(1) or href_match.group(2)
        target_ok = bool(re.search(r'target=(?:"_blank"|_blank)', tag, re.IGNORECASE))
        rel_ok = bool(re.search(r'rel=(?:"noopener noreferrer"|noopener\s+noreferrer)', tag, re.IGNORECASE))
        if not target_ok or not rel_ok:
            issues.append(f"{rel}: external footer link missing target/rel: {html.unescape(anchor)}")
    if re.search(r"<ul\b[^>]*>\s*</ul>", footer, re.DOTALL):
        issues.append(f"{rel}: empty footer list rendered")
    return issues


def postbuild_checks(pages):
    issues = []
    if not PUBLIC.exists():
        return ["public/: production output is missing; run hugo before --postbuild"]
    built = list(PUBLIC.rglob("index.html"))
    for rel, meta in pages:
        slug = clean(meta.get("slug")) or rel.stem
        matches = [path for path in built if path.parent.name == slug]
        if not matches:
            issues.append(f"{rel}: no built page found for slug {slug}")
            continue
        for path in matches:
            text = path.read_text("utf-8")
            decoded = html.unescape(text)
            marker_count = len(re.findall(r'data-article-footer(?:\s|=|>)', text))
            if marker_count != 1:
                issues.append(f"{rel}: {path.relative_to(PUBLIC)} has {marker_count} article footer markers")
            if decoded.count("Bản quyền & Ghi nguồn") != 1:
                issues.append(f"{rel}: {path.relative_to(PUBLIC)} missing/duplicating fixed copyright heading")
            if "Nội dung trên KoreaWiki thuộc bản quyền của website" not in decoded:
                issues.append(f"{rel}: {path.relative_to(PUBLIC)} missing copyright notice")
            if not re.search(r"data-article-footer-copyright", text):
                issues.append(f"{rel}: {path.relative_to(PUBLIC)} missing copyright section marker")
            issues.extend(check_external_links(text, path.relative_to(PUBLIC)))
            footer = re.search(r'<aside\b[^>]*data-article-footer(?:\s|=|>)[^>]*>(.*?)</aside>', text, re.DOTALL)
            if footer and re.search(r"<h2[^>]*>FAQ - Câu hỏi thường gặp</h2>", footer.group(1)):
                footer_text = html.unescape(footer.group(1))
                if footer_text.find("Bản quyền & Ghi nguồn") < footer_text.find("FAQ - Câu hỏi thường gặp"):
                    issues.append(f"{rel}: copyright block must be after FAQ/links")
    return issues


def main():
    issues, pages = content_checks()
    if "--postbuild" in sys.argv:
        issues.extend(postbuild_checks(pages))
    if issues:
        print(f"Article footer QA failed ({len(issues)} issue(s)):")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    mode = " + production output" if "--postbuild" in sys.argv else ""
    print(f"Article footer QA passed{mode} ({len(pages)} articles).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
