#!/usr/bin/env python3
"""KoreaWiki Translation Memory (TM) & Glossary manager.

Private linguistic asset stored under data/glossary/.
Public site renders a browsable Glossary page; raw JSON/CSV/SQLite
are never copied into the Hugo public/ output.

Usage examples:
  python scripts/glossary.py init
  python scripts/glossary.py consult
  python scripts/glossary.py lookup 배우
  python scripts/glossary.py add --korean 배우 --vietnamese "diễn viên" --category noun
  python scripts/glossary.py upsert --file entries.json
  python scripts/glossary.py merge
  python scripts/glossary.py edit --id abc123 --vietnamese "diễn viên/nữ diễn viên"
  python scripts/glossary.py delete --id abc123
  python scripts/glossary.py export --format csv
  python scripts/glossary.py import --format json --file import.json
  python scripts/glossary.py quality
  python scripts/glossary.py sync
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY_DIR = ROOT / "data" / "glossary"
JSON_PATH = GLOSSARY_DIR / "glossary.json"
MD_PATH = GLOSSARY_DIR / "glossary.md"
CSV_PATH = GLOSSARY_DIR / "glossary.csv"
SQLITE_PATH = GLOSSARY_DIR / "glossary.sqlite"
META_PATH = GLOSSARY_DIR / "meta.json"

# Public-facing content (safe fields only; no raw DB download)
PUBLIC_INDEX = ROOT / "content" / "en" / "glossary" / "_index.md"

SCHEMA_VERSION = 1
PAGE_SIZE_DEFAULT = 25

CATEGORIES = {
    "noun",
    "verb",
    "adjective",
    "adverb",
    "proper_noun",
    "organization",
    "celebrity",
    "movie",
    "drama",
    "location",
    "slang",
    "idiom",
    "grammar",
    "phrase",
    "pattern",
    "title",
    "other",
}

PUBLIC_FIELDS = (
    "korean",
    "vietnamese",
    "romanization",
    "pos",
    "meaning",
    "context",
    "example",
    "category",
    "tags",
)


def today_iso() -> str:
    return date.today().isoformat()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_key(korean: str, vietnamese: str = "") -> str:
    """Stable identity for merge/dedup: normalized Korean (+ VI when conflict tracking)."""
    k = re.sub(r"\s+", " ", (korean or "").strip())
    return k.casefold()


def entry_id(korean: str, vietnamese: str) -> str:
    vi = re.sub(r"\s+", " ", (vietnamese or "").strip()).casefold()
    raw = f"{normalize_key(korean)}|{vi}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def empty_store() -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "language_pair": "ko-vi",
        "updated": utc_now_iso(),
        "entries": [],
    }


def load_store() -> dict[str, Any]:
    if not JSON_PATH.exists():
        return empty_store()
    data = json.loads(JSON_PATH.read_text("utf-8"))
    if "entries" not in data:
        data = empty_store() | {"entries": data if isinstance(data, list) else []}
    return data


def save_store(store: dict[str, Any]) -> None:
    GLOSSARY_DIR.mkdir(parents=True, exist_ok=True)
    store["version"] = SCHEMA_VERSION
    store["updated"] = utc_now_iso()
    # Stable sort: frequency desc, korean asc
    store["entries"].sort(
        key=lambda e: (-int(e.get("frequency") or 0), e.get("korean") or "")
    )
    JSON_PATH.write_text(
        json.dumps(store, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    write_markdown(store)
    write_csv(store)
    write_sqlite(store)
    write_meta(store)
    write_public_index(store)


def write_meta(store: dict[str, Any]) -> None:
    entries = store.get("entries", [])
    cats: dict[str, int] = {}
    for e in entries:
        c = e.get("category") or "other"
        cats[c] = cats.get(c, 0) + 1
    meta = {
        "version": SCHEMA_VERSION,
        "language_pair": store.get("language_pair", "ko-vi"),
        "updated": store.get("updated"),
        "count": len(entries),
        "categories": dict(sorted(cats.items())),
        "files": {
            "json": "glossary.json",
            "markdown": "glossary.md",
            "csv": "glossary.csv",
            "sqlite": "glossary.sqlite",
        },
        "public": False,
        "note": "Raw TM files are private repository assets; not deployed as downloadable files.",
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", "utf-8")


def write_markdown(store: dict[str, Any]) -> None:
    lines = [
        "# KoreaWiki Translation Memory (Korean → Vietnamese)",
        "",
        f"> Private linguistic asset. Updated: {store.get('updated', '')}",
        f"> Entries: {len(store.get('entries', []))}",
        "",
        "| Korean | Vietnamese | Context | Category | Source | Updated |",
        "|--------|------------|---------|----------|--------|---------|",
    ]
    for e in store.get("entries", []):
        src = e.get("source_url") or e.get("source") or ""
        updated = e.get("last_seen") or e.get("updated") or ""
        lines.append(
            "| {korean} | {vietnamese} | {context} | {category} | {source} | {updated} |".format(
                korean=_md_cell(e.get("korean", "")),
                vietnamese=_md_cell(e.get("vietnamese", "")),
                context=_md_cell(e.get("context", "")),
                category=_md_cell(e.get("category", "")),
                source=_md_cell(src),
                updated=_md_cell(updated),
            )
        )
    lines.append("")
    MD_PATH.write_text("\n".join(lines), "utf-8")


def _md_cell(value: Any) -> str:
    s = str(value or "").replace("\n", " ").replace("|", "\\|").strip()
    return s


def write_csv(store: dict[str, Any]) -> None:
    fields = [
        "id",
        "korean",
        "vietnamese",
        "romanization",
        "pos",
        "meaning",
        "context",
        "example",
        "source_url",
        "first_seen",
        "last_seen",
        "frequency",
        "tags",
        "category",
    ]
    with CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for e in store.get("entries", []):
            row = {k: e.get(k, "") for k in fields}
            tags = e.get("tags") or []
            row["tags"] = ",".join(tags) if isinstance(tags, list) else tags
            w.writerow(row)


def write_sqlite(store: dict[str, Any]) -> None:
    if SQLITE_PATH.exists():
        SQLITE_PATH.unlink()
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE glossary (
                id TEXT PRIMARY KEY,
                korean TEXT NOT NULL,
                vietnamese TEXT NOT NULL,
                romanization TEXT,
                pos TEXT,
                meaning TEXT,
                context TEXT,
                example TEXT,
                source_url TEXT,
                first_seen TEXT,
                last_seen TEXT,
                frequency INTEGER DEFAULT 1,
                tags TEXT,
                category TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX idx_glossary_korean ON glossary(korean)"
        )
        conn.execute(
            "CREATE INDEX idx_glossary_category ON glossary(category)"
        )
        rows = []
        for e in store.get("entries", []):
            tags = e.get("tags") or []
            tags_s = ",".join(tags) if isinstance(tags, list) else str(tags)
            rows.append(
                (
                    e.get("id") or entry_id(e.get("korean", ""), e.get("vietnamese", "")),
                    e.get("korean", ""),
                    e.get("vietnamese", ""),
                    e.get("romanization", ""),
                    e.get("pos", ""),
                    e.get("meaning", ""),
                    e.get("context", ""),
                    e.get("example", ""),
                    e.get("source_url") or e.get("source") or "",
                    e.get("first_seen", ""),
                    e.get("last_seen", ""),
                    int(e.get("frequency") or 1),
                    tags_s,
                    e.get("category", ""),
                )
            )
        conn.executemany(
            """
            INSERT INTO glossary (
                id, korean, vietnamese, romanization, pos, meaning, context,
                example, source_url, first_seen, last_seen, frequency, tags, category
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def public_entries(store: dict[str, Any]) -> list[dict[str, Any]]:
    """Fields safe to embed in the public glossary page (no raw dump files)."""
    out = []
    for e in store.get("entries", []):
        tags = e.get("tags") or []
        if not isinstance(tags, list):
            tags = [t.strip() for t in str(tags).split(",") if t.strip()]
        out.append(
            {
                "korean": e.get("korean") or "",
                "vietnamese": e.get("vietnamese") or "",
                "romanization": e.get("romanization") or "",
                "pos": e.get("pos") or "",
                "meaning": e.get("meaning") or "",
                "context": e.get("context") or "",
                "example": e.get("example") or "",
                "category": e.get("category") or "other",
                "tags": tags,
            }
        )
    return out


def write_public_index(store: dict[str, Any]) -> None:
    """Regenerate content/en/glossary/_index.md with front matter + notes.

    Entry data is rendered by the glossary layout from data/glossary/glossary.json
    at build time (Hugo data). No JSON/CSV/SQLite is emitted into public/.
    """
    PUBLIC_INDEX.parent.mkdir(parents=True, exist_ok=True)
    count = len(store.get("entries", []))
    updated = store.get("updated", today_iso())[:10]
    body = f"""---
title: "Glossary"
description: "Korean–Vietnamese translation glossary for Korean entertainment and culture terms used across KoreaWiki. Search Hangul, Vietnamese, and romanization."
slug: "glossary"
draft: false
robots: "index, follow"
keywords:
  - glossary
  - korean vietnamese
  - translation memory
  - hangeul
  - k-pop terminology
type: "glossary"
---

KoreaWiki's public glossary of Korean → Vietnamese terms accumulated while
translating and publishing entertainment news. Prefer these established
renderings for consistency across the site.

**Entries:** {count} · **Updated:** {updated}

Use the search box and filters below. The underlying Translation Memory
database remains a private repository asset and is not available for download.
"""
    PUBLIC_INDEX.write_text(body, "utf-8")


def normalize_entry(raw: dict[str, Any], *, bump: bool = False) -> dict[str, Any]:
    korean = str(raw.get("korean") or raw.get("ko") or "").strip()
    vietnamese = str(raw.get("vietnamese") or raw.get("vi") or "").strip()
    if not korean or not vietnamese:
        raise ValueError("Entry requires korean and vietnamese")

    tags = raw.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    tags = [str(t).strip() for t in tags if str(t).strip()]

    category = str(raw.get("category") or "other").strip().lower() or "other"
    if category not in CATEGORIES:
        category = "other"

    today = today_iso()
    eid = raw.get("id") or entry_id(korean, vietnamese)

    entry = {
        "id": eid,
        "korean": korean,
        "vietnamese": vietnamese,
        "romanization": str(raw.get("romanization") or raw.get("romaja") or "").strip(),
        "pos": str(raw.get("pos") or raw.get("part_of_speech") or "").strip(),
        "meaning": str(raw.get("meaning") or "").strip(),
        "context": str(raw.get("context") or "").strip(),
        "example": str(raw.get("example") or raw.get("example_sentence") or "").strip(),
        "source_url": str(
            raw.get("source_url") or raw.get("source") or raw.get("url") or ""
        ).strip(),
        "first_seen": str(raw.get("first_seen") or today),
        "last_seen": str(raw.get("last_seen") or today),
        "frequency": int(raw.get("frequency") or 1),
        "tags": tags,
        "category": category,
    }
    if bump:
        entry["frequency"] = max(1, entry["frequency"])
        entry["last_seen"] = today
    return entry


def find_by_korean(store: dict[str, Any], korean: str) -> list[dict[str, Any]]:
    key = normalize_key(korean)
    return [e for e in store["entries"] if normalize_key(e.get("korean", "")) == key]


def find_by_id(store: dict[str, Any], eid: str) -> dict[str, Any] | None:
    for e in store["entries"]:
        if e.get("id") == eid:
            return e
    return None


def upsert_entry(store: dict[str, Any], raw: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Insert or merge. Same korean+vietnamese → bump frequency. Same korean different vi → keep both (conflict)."""
    new = normalize_entry(raw, bump=True)
    # Exact match on korean+vietnamese
    for i, e in enumerate(store["entries"]):
        if normalize_key(e.get("korean", "")) == normalize_key(new["korean"]) and re.sub(
            r"\s+", " ", (e.get("vietnamese") or "").strip()
        ).casefold() == re.sub(
            r"\s+", " ", new["vietnamese"]
        ).casefold():
            # Merge identical
            e["frequency"] = int(e.get("frequency") or 1) + 1
            e["last_seen"] = today_iso()
            for field in (
                "romanization",
                "pos",
                "meaning",
                "context",
                "example",
                "source_url",
                "category",
            ):
                if not e.get(field) and new.get(field):
                    e[field] = new[field]
            # Union tags
            old_tags = e.get("tags") or []
            if not isinstance(old_tags, list):
                old_tags = [old_tags]
            e["tags"] = sorted(set(old_tags) | set(new.get("tags") or []))
            store["entries"][i] = e
            return e, "merged"

    store["entries"].append(new)
    return new, "added"


def merge_duplicates(store: dict[str, Any]) -> int:
    """Merge entries with identical korean+vietnamese (case/space-insensitive)."""
    buckets: dict[str, dict[str, Any]] = {}
    merged = 0
    for e in store["entries"]:
        key = (
            normalize_key(e.get("korean", "")),
            re.sub(r"\s+", " ", (e.get("vietnamese") or "").strip()).casefold(),
        )
        if key not in buckets:
            buckets[key] = dict(e)
            continue
        base = buckets[key]
        base["frequency"] = int(base.get("frequency") or 1) + int(e.get("frequency") or 1)
        # Prefer newer last_seen
        if (e.get("last_seen") or "") > (base.get("last_seen") or ""):
            base["last_seen"] = e.get("last_seen")
        if (e.get("first_seen") or "9999") < (base.get("first_seen") or "9999"):
            base["first_seen"] = e.get("first_seen")
        for field in (
            "romanization",
            "pos",
            "meaning",
            "context",
            "example",
            "source_url",
            "category",
        ):
            if not base.get(field) and e.get(field):
                base[field] = e[field]
        bt = set(base.get("tags") or [])
        et = set(e.get("tags") or [])
        base["tags"] = sorted(bt | et)
        merged += 1
    store["entries"] = list(buckets.values())
    return merged


def quality_report(store: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    by_ko: dict[str, list[dict[str, Any]]] = {}
    seen_pair: set[tuple[str, str]] = set()

    for e in store["entries"]:
        eid = e.get("id", "?")
        ko = (e.get("korean") or "").strip()
        vi = (e.get("vietnamese") or "").strip()
        if not ko or not vi:
            issues.append({"id": eid, "type": "invalid", "msg": "Missing korean or vietnamese"})
            continue
        pair = (normalize_key(ko), re.sub(r"\s+", " ", vi).casefold())
        if pair in seen_pair:
            issues.append(
                {
                    "id": eid,
                    "type": "duplicate",
                    "msg": f"Duplicate pair: {ko} → {vi}",
                }
            )
        seen_pair.add(pair)
        by_ko.setdefault(normalize_key(ko), []).append(e)

        if not (e.get("context") or "").strip():
            issues.append({"id": eid, "type": "missing_context", "msg": f"Missing context: {ko}"})
        if not (e.get("category") or "").strip():
            issues.append(
                {"id": eid, "type": "missing_category", "msg": f"Missing category: {ko}"}
            )
        cat = (e.get("category") or "").strip().lower()
        if cat and cat not in CATEGORIES:
            issues.append(
                {
                    "id": eid,
                    "type": "invalid_category",
                    "msg": f"Invalid category '{cat}' for {ko}",
                }
            )
        # Invalid formatting: pipe in table-sensitive fields, control chars
        for field in ("korean", "vietnamese", "context", "example"):
            val = str(e.get(field) or "")
            if "\x00" in val or re.search(r"[\x01-\x08\x0b\x0c\x0e-\x1f]", val):
                issues.append(
                    {
                        "id": eid,
                        "type": "invalid_format",
                        "msg": f"Control characters in {field}: {ko}",
                    }
                )

    for key, group in by_ko.items():
        vis = {
            re.sub(r"\s+", " ", (g.get("vietnamese") or "").strip()).casefold()
            for g in group
        }
        if len(vis) > 1:
            samples = ", ".join(
                f"{g.get('vietnamese')}" for g in group[:4]
            )
            issues.append(
                {
                    "id": group[0].get("id"),
                    "type": "conflict",
                    "msg": f"Conflicting translations for '{group[0].get('korean')}': {samples}",
                }
            )
    return issues


def seed_entries() -> list[dict[str, Any]]:
    """Bootstrap Korean–Vietnamese entertainment TM."""
    today = today_iso()
    raw = [
        # Core entertainment nouns
        ("배우", "diễn viên", "bae-u", "noun", "người biểu diễn trên màn ảnh", "ngành giải trí", "그 배우는 유명하다.", "noun", ["entertainment"]),
        ("여배우", "nữ diễn viên", "yeo-bae-u", "noun", "diễn viên nữ", "ngành giải trí", "", "noun", ["entertainment"]),
        ("남배우", "nam diễn viên", "nam-bae-u", "noun", "diễn viên nam", "ngành giải trí", "", "noun", ["entertainment"]),
        ("가수", "ca sĩ", "ga-su", "noun", "nghệ sĩ hát", "âm nhạc", "", "noun", ["music"]),
        ("아이돌", "idol", "a-i-dol", "noun", "thần tượng K-pop", "K-pop", "아이돌 그룹이 데뷔했다.", "noun", ["kpop"]),
        ("그룹", "nhóm nhạc", "geu-rup", "noun", "ban nhạc / nhóm idol", "K-pop", "", "noun", ["kpop"]),
        ("솔로", "solo", "sol-lo", "noun", "hoạt động đơn ca", "âm nhạc", "", "noun", ["music"]),
        ("데뷔", "ra mắt / debut", "de-byu", "noun", "lần xuất hiện đầu", "sự nghiệp", "올해 데뷔했다.", "noun", ["career"]),
        ("컴백", "comeback", "keom-baek", "noun", "trở lại với sản phẩm mới", "K-pop", "컴백 일정이 공개됐다.", "noun", ["kpop"]),
        ("앨범", "album", "ael-beom", "noun", "đĩa nhạc", "âm nhạc", "", "noun", ["music"]),
        ("싱글", "single", "sing-geul", "noun", "đĩa đơn", "âm nhạc", "", "noun", ["music"]),
        ("타이틀곡", "bài chủ đề / title track", "ta-i-teul-gok", "noun", "ca khúc chủ đạo của album", "âm nhạc", "", "noun", ["music"]),
        ("뮤직비디오", "MV / video ca nhạc", "myu-jik-bi-di-o", "noun", "music video", "âm nhạc", "", "noun", ["music"]),
        ("팬", "fan", "paen", "noun", "người hâm mộ", "fandom", "", "noun", ["fandom"]),
        ("팬미팅", "fan meeting", "paen-mi-ting", "noun", "gặp gỡ fan", "sự kiện", "", "noun", ["event"]),
        ("콘서트", "buổi hòa nhạc / concert", "kon-seo-teu", "noun", "biểu diễn trực tiếp", "sự kiện", "", "noun", ["event"]),
        ("투어", "tour / chuyến lưu diễn", "tu-eo", "noun", "chuỗi concert nhiều thành phố", "sự kiện", "", "noun", ["event"]),
        ("드라마", "phim truyền hình / drama", "deu-ra-ma", "noun", "K-drama", "truyền hình", "", "drama", ["kdrama"]),
        ("영화", "phim điện ảnh", "yeong-hwa", "noun", "movie", "điện ảnh", "", "movie", ["film"]),
        ("감독", "đạo diễn", "gam-dok", "noun", "người chỉ đạo phim", "điện ảnh", "", "noun", ["film"]),
        ("제작", "sản xuất", "je-jak", "noun", "production", "truyền thông", "", "noun", ["media"]),
        ("방송", "phát sóng / chương trình", "bang-song", "noun", "broadcast", "truyền hình", "", "noun", ["tv"]),
        ("예능", "chương trình giải trí / variety", "ye-neung", "noun", "variety show", "truyền hình", "", "noun", ["tv"]),
        ("출연", "tham gia / đóng vai", "chul-yeon", "noun", "xuất hiện trên show/phim", "giải trí", "", "noun", ["entertainment"]),
        ("캐스팅", "casting", "kae-seu-ting", "noun", "tuyển vai", "phim/drama", "", "noun", ["film"]),
        ("개봉", "công chiếu / ra rạp", "gae-bong", "noun", "phát hành phim", "điện ảnh", "영화가 개봉했다.", "noun", ["film"]),
        ("흥행", "doanh thu / thành công phòng vé", "heung-haeng", "noun", "box office performance", "điện ảnh", "", "noun", ["film"]),
        ("시사회", "buổi công chiếu thử / premiere", "si-sa-hoe", "noun", "chiếu ra mắt", "điện ảnh", "", "noun", ["film"]),
        ("수상", "nhận giải", "su-sang", "noun", "đoạt giải thưởng", "giải thưởng", "", "noun", ["awards"]),
        ("시상식", "lễ trao giải", "si-sang-sik", "noun", "award ceremony", "giải thưởng", "", "noun", ["awards"]),
        # Organizations
        ("하이브", "HYBE", "ha-i-beu", "proper_noun", "công ty giải trí HYBE", "công ty", "", "organization", ["company"]),
        ("에스엠", "SM Entertainment", "e-seu-em", "proper_noun", "công ty SM", "công ty", "", "organization", ["company"]),
        ("제이와이드", "JYP Entertainment", "je-i-wa-i-deu", "proper_noun", "công ty JYP", "công ty", "", "organization", ["company"]),
        ("와이쥐", "YG Entertainment", "wa-i-ji", "proper_noun", "công ty YG", "công ty", "", "organization", ["company"]),
        ("넷플릭스", "Netflix", "net-peul-lik-seu", "proper_noun", "nền tảng streaming", "streaming", "", "organization", ["streaming"]),
        ("디스패치", "Dispatch", "di-seu-pae-chi", "proper_noun", "tờ tin giải trí Hàn", "báo chí", "", "organization", ["media"]),
        # Locations
        ("서울", "Seoul", "seo-ul", "proper_noun", "thủ đô Hàn Quốc", "địa danh", "", "location", ["place"]),
        ("부산", "Busan", "bu-san", "proper_noun", "thành phố cảng", "địa danh", "", "location", ["place"]),
        ("제주", "Jeju", "je-ju", "proper_noun", "đảo Jeju", "địa danh", "", "location", ["place"]),
        ("강남", "Gangnam", "gang-nam", "proper_noun", "khu Gangnam, Seoul", "địa danh", "", "location", ["place"]),
        ("홍대", "Hongdae", "hong-dae", "proper_noun", "khu Hongdae", "địa danh", "", "location", ["place"]),
        # Culture / general
        ("한류", "Hallyu / làn sóng Hàn", "hal-lyu", "noun", "Korean Wave", "văn hóa", "한류가 확산되고 있다.", "noun", ["culture"]),
        ("한복", "hanbok", "han-bok", "noun", "trang phục truyền thống Hàn", "văn hóa", "", "noun", ["culture"]),
        ("케이팝", "K-pop", "ke-i-pap", "noun", "nhạc pop Hàn Quốc", "âm nhạc", "", "noun", ["kpop"]),
        ("케이드라마", "K-drama", "ke-i-deu-ra-ma", "noun", "phim truyền hình Hàn", "truyền hình", "", "noun", ["kdrama"]),
        ("소속사", "công ty quản lý / agency", "so-sok-sa", "noun", "công ty giải trí của nghệ sĩ", "ngành", "", "noun", ["industry"]),
        ("연습생", "thực tập sinh", "yeon-seup-saeng", "noun", "trainee idol", "K-pop", "", "noun", ["kpop"]),
        ("안무", "biên đạo / vũ đạo", "an-mu", "noun", "choreography", "biểu diễn", "", "noun", ["performance"]),
        ("가사", "lời bài hát", "ga-sa", "noun", "lyrics", "âm nhạc", "", "noun", ["music"]),
        ("음원", "nhạc số / digital track", "eum-won", "noun", "digital music release", "âm nhạc", "", "noun", ["music"]),
        ("차트", "bảng xếp hạng", "cha-teu", "noun", "music chart", "âm nhạc", "", "noun", ["music"]),
        ("화제", "chủ đề nóng / viral", "hwa-je", "noun", "đang được bàn tán", "truyền thông", "화제가 된 배우", "noun", ["media"]),
        ("논란", "tranh cãi / scandal", "non-lan", "noun", "controversy", "truyền thông", "", "noun", ["media"]),
        ("열애", "yêu đương / hẹn hò", "yeol-ae", "noun", "dating news", "showbiz", "", "noun", ["showbiz"]),
        ("결별", "chia tay", "gyeol-byeol", "noun", "breakup", "showbiz", "", "noun", ["showbiz"]),
        ("결혼", "kết hôn", "gyeol-hon", "noun", "marriage", "đời tư", "", "noun", ["life"]),
        ("공개", "công bố / công khai", "gong-gae", "verb", "announce / release publicly", "truyền thông", "일정을 공개했다.", "verb", ["media"]),
        ("발표", "công bố / announcement", "bal-pyo", "noun", "official announcement", "truyền thông", "", "noun", ["media"]),
        ("공식", "chính thức", "gong-sik", "adjective", "official", "thông cáo", "공식 입장", "adjective", ["media"]),
        ("입장", "lập trường / tuyên bố", "ip-jang", "noun", "official position statement", "truyền thông", "소속사 입장", "noun", ["media"]),
        ("관계자", "người liên quan / nguồn tin", "gwan-gye-ja", "noun", "insider / related official", "báo chí", "관계자에 따르면", "noun", ["media"]),
        ("보도", "đưa tin / báo cáo", "bo-do", "noun", "news report", "báo chí", "", "noun", ["media"]),
        ("인터뷰", "phỏng vấn", "in-teo-byu", "noun", "interview", "báo chí", "", "noun", ["media"]),
        ("화보", "bộ ảnh / pictorial", "hwa-bo", "noun", "magazine pictorial", "thời trang", "", "noun", ["fashion"]),
        ("패션", "thời trang", "pae-syeon", "noun", "fashion", "thời trang", "", "noun", ["fashion"]),
        ("뷰티", "làm đẹp / beauty", "byu-ti", "noun", "beauty industry", "K-beauty", "", "noun", ["beauty"]),
        # Grammar / patterns common in news
        ("~에 따르면", "theo…", "e tta-reu-myeon", "pattern", "dẫn nguồn", "báo chí", "보도에 따르면", "grammar", ["news"]),
        ("~을/를 통해", "thông qua…", "eul/reul tong-hae", "pattern", "by means of", "báo chí", "", "grammar", ["news"]),
        ("화제를 모으다", "gây chú ý / thu hút bàn tán", "hwa-je-reul mo-eu-da", "idiom", "attract attention", "truyền thông", "화제를 모으고 있다", "idiom", ["media"]),
        ("관심을 받다", "nhận được sự quan tâm", "gwan-sim-eul bat-da", "phrase", "receive attention", "truyền thông", "", "phrase", ["media"]),
        ("주목받다", "được chú ý", "ju-mok-bat-da", "verb", "draw attention", "truyền thông", "", "verb", ["media"]),
        # Celebrities / titles seed (stable romanization)
        ("방탄소년단", "BTS", "bang-tan-so-nyeon-dan", "proper_noun", "nhóm nhạc BTS", "K-pop", "", "celebrity", ["kpop", "bts"]),
        ("아이유", "IU", "a-i-yu", "proper_noun", "ca sĩ / diễn viên IU", "nghệ sĩ", "", "celebrity", ["artist"]),
        ("블랙핑크", "BLACKPINK", "beul-laek-ping-keu", "proper_noun", "nhóm nữ BLACKPINK", "K-pop", "", "celebrity", ["kpop"]),
    ]
    entries = []
    for ko, vi, rom, pos, meaning, ctx, ex, cat, tags in raw:
        entries.append(
            {
                "id": entry_id(ko, vi),
                "korean": ko,
                "vietnamese": vi,
                "romanization": rom,
                "pos": pos,
                "meaning": meaning,
                "context": ctx,
                "example": ex,
                "source_url": "",
                "first_seen": today,
                "last_seen": today,
                "frequency": 1,
                "tags": tags,
                "category": cat,
            }
        )
    return entries


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    GLOSSARY_DIR.mkdir(parents=True, exist_ok=True)
    if JSON_PATH.exists() and not args.force:
        store = load_store()
        if store.get("entries"):
            print(f"Already initialized ({len(store['entries'])} entries). Use --force to reseed.")
            save_store(store)  # refresh exports
            return 0
    store = empty_store()
    if not args.empty:
        store["entries"] = seed_entries()
    save_store(store)
    print(f"Initialized TM with {len(store['entries'])} entries → {GLOSSARY_DIR}")
    return 0


def cmd_consult(args: argparse.Namespace) -> int:
    """Print TM for AI to prefer before translating."""
    store = load_store()
    entries = store.get("entries", [])
    limit = args.limit or 200
    # Highest frequency first already sorted
    print("# Translation Memory (Korean → Vietnamese)")
    print(f"# {len(entries)} entries · prefer these renderings for consistency\n")
    for e in entries[:limit]:
        line = f"- {e.get('korean')} → {e.get('vietnamese')}"
        if e.get("category"):
            line += f" [{e.get('category')}]"
        if e.get("context"):
            line += f" · {e.get('context')}"
        if e.get("romanization"):
            line += f" ({e.get('romanization')})"
        print(line)
    if len(entries) > limit:
        print(f"\n# … {len(entries) - limit} more (run without --limit or raise it)")
    return 0


def cmd_lookup(args: argparse.Namespace) -> int:
    store = load_store()
    q = (args.query or "").strip()
    if not q:
        print("Provide a query.", file=sys.stderr)
        return 1
    q_cf = q.casefold()
    hits = []
    for e in store["entries"]:
        blob = " ".join(
            str(e.get(f) or "")
            for f in (
                "korean",
                "vietnamese",
                "romanization",
                "meaning",
                "context",
                "example",
                "category",
            )
        ).casefold()
        tags = " ".join(e.get("tags") or []).casefold()
        if q_cf in blob or q_cf in tags or q in (e.get("korean") or ""):
            hits.append(e)
    if not hits:
        print("No matches.")
        return 0
    print(json.dumps(hits, ensure_ascii=False, indent=2))
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    store = load_store()
    raw = {
        "korean": args.korean,
        "vietnamese": args.vietnamese,
        "romanization": args.romanization or "",
        "pos": args.pos or "",
        "meaning": args.meaning or "",
        "context": args.context or "",
        "example": args.example or "",
        "source_url": args.source or "",
        "category": args.category or "other",
        "tags": args.tags or "",
    }
    entry, action = upsert_entry(store, raw)
    save_store(store)
    print(f"{action}: {entry['korean']} → {entry['vietnamese']} (freq={entry['frequency']})")
    return 0


def cmd_upsert(args: argparse.Namespace) -> int:
    """Bulk upsert from JSON file (list of entries) or stdin."""
    store = load_store()
    if args.file and args.file != "-":
        payload = json.loads(Path(args.file).read_text("utf-8"))
    else:
        payload = json.load(sys.stdin)
    if isinstance(payload, dict) and "entries" in payload:
        items = payload["entries"]
    elif isinstance(payload, list):
        items = payload
    else:
        print("Expected list or {entries: [...]}", file=sys.stderr)
        return 1
    added = merged = 0
    for item in items:
        try:
            _, action = upsert_entry(store, item)
        except ValueError as exc:
            print(f"skip: {exc}", file=sys.stderr)
            continue
        if action == "added":
            added += 1
        else:
            merged += 1
    save_store(store)
    print(f"Upserted: {added} added, {merged} merged, total={len(store['entries'])}")
    return 0


def cmd_edit(args: argparse.Namespace) -> int:
    store = load_store()
    e = find_by_id(store, args.id)
    if not e:
        print(f"Not found: {args.id}", file=sys.stderr)
        return 1
    for field in (
        "korean",
        "vietnamese",
        "romanization",
        "pos",
        "meaning",
        "context",
        "example",
        "source",
        "category",
        "tags",
    ):
        val = getattr(args, field if field != "source" else "source", None)
        if val is None:
            continue
        if field == "source":
            e["source_url"] = val
        elif field == "tags":
            e["tags"] = [t.strip() for t in val.split(",") if t.strip()]
        else:
            e[field] = val
    e["last_seen"] = today_iso()
    # Recompute id if ko/vi changed
    e["id"] = entry_id(e.get("korean", ""), e.get("vietnamese", ""))
    save_store(store)
    print(f"Updated {e['id']}: {e['korean']} → {e['vietnamese']}")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    store = load_store()
    before = len(store["entries"])
    store["entries"] = [e for e in store["entries"] if e.get("id") != args.id]
    if len(store["entries"]) == before:
        print(f"Not found: {args.id}", file=sys.stderr)
        return 1
    save_store(store)
    print(f"Deleted {args.id}. Remaining: {len(store['entries'])}")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    store = load_store()
    n = merge_duplicates(store)
    save_store(store)
    print(f"Merged {n} duplicate(s). Total: {len(store['entries'])}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    store = load_store()
    fmt = (args.format or "json").lower()
    out = Path(args.output) if args.output else None
    if fmt == "json":
        text = json.dumps(store, ensure_ascii=False, indent=2) + "\n"
        if out:
            out.write_text(text, "utf-8")
            print(f"Exported JSON → {out}")
        else:
            sys.stdout.write(text)
    elif fmt == "csv":
        target = out or CSV_PATH
        if out:
            # write to custom path
            fields = [
                "id",
                "korean",
                "vietnamese",
                "romanization",
                "pos",
                "meaning",
                "context",
                "example",
                "source_url",
                "first_seen",
                "last_seen",
                "frequency",
                "tags",
                "category",
            ]
            with out.open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
                w.writeheader()
                for e in store["entries"]:
                    row = {k: e.get(k, "") for k in fields}
                    tags = e.get("tags") or []
                    row["tags"] = ",".join(tags) if isinstance(tags, list) else tags
                    w.writerow(row)
        else:
            write_csv(store)
        print(f"Exported CSV → {target}")
    elif fmt in ("md", "markdown"):
        target = out or MD_PATH
        if out:
            # temporary write via helper path swap
            old = MD_PATH
            # reuse write_markdown logic inline
            lines = [
                "# KoreaWiki Translation Memory (Korean → Vietnamese)",
                "",
                "| Korean | Vietnamese | Context | Category | Source | Updated |",
                "|--------|------------|---------|----------|--------|---------|",
            ]
            for e in store["entries"]:
                lines.append(
                    f"| {_md_cell(e.get('korean'))} | {_md_cell(e.get('vietnamese'))} | "
                    f"{_md_cell(e.get('context'))} | {_md_cell(e.get('category'))} | "
                    f"{_md_cell(e.get('source_url'))} | {_md_cell(e.get('last_seen'))} |"
                )
            out.write_text("\n".join(lines) + "\n", "utf-8")
        else:
            write_markdown(store)
        print(f"Exported Markdown → {target}")
    else:
        print(f"Unknown format: {fmt}", file=sys.stderr)
        return 1
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    store = load_store() if not args.replace else empty_store()
    fmt = (args.format or "json").lower()
    path = Path(args.file)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1
    items: list[dict[str, Any]] = []
    if fmt == "json":
        payload = json.loads(path.read_text("utf-8"))
        if isinstance(payload, dict) and "entries" in payload:
            items = payload["entries"]
        elif isinstance(payload, list):
            items = payload
        else:
            print("Invalid JSON shape", file=sys.stderr)
            return 1
    elif fmt == "csv":
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            items = list(reader)
    elif fmt in ("md", "markdown"):
        items = _parse_markdown_table(path.read_text("utf-8"))
    else:
        print(f"Unknown format: {fmt}", file=sys.stderr)
        return 1

    added = merged = 0
    for item in items:
        try:
            _, action = upsert_entry(store, item)
        except ValueError as exc:
            print(f"skip: {exc}", file=sys.stderr)
            continue
        if action == "added":
            added += 1
        else:
            merged += 1
    save_store(store)
    print(f"Imported: {added} added, {merged} merged, total={len(store['entries'])}")
    return 0


def _parse_markdown_table(text: str) -> list[dict[str, Any]]:
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|\s*-+", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        # header skip
        if cells[0].lower() in ("korean", "한국어", "hangul"):
            continue
        item: dict[str, Any] = {
            "korean": cells[0],
            "vietnamese": cells[1],
        }
        if len(cells) > 2:
            item["context"] = cells[2]
        if len(cells) > 3:
            item["category"] = cells[3]
        if len(cells) > 4:
            item["source_url"] = cells[4]
        items.append(item)
    return items


def cmd_quality(args: argparse.Namespace) -> int:
    store = load_store()
    issues = quality_report(store)
    if not issues:
        print(f"Quality OK — {len(store['entries'])} entries, no issues.")
        return 0
    by_type: dict[str, int] = {}
    for iss in issues:
        by_type[iss["type"]] = by_type.get(iss["type"], 0) + 1
    print(f"{len(issues)} issue(s) across {len(store['entries'])} entries:\n")
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")
    print()
    for iss in issues[: args.limit or 50]:
        print(f"  [{iss['type']}] {iss['msg']} (id={iss.get('id')})")
    if len(issues) > (args.limit or 50):
        print(f"  … {len(issues) - (args.limit or 50)} more")
    return 1 if args.strict else 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Rewrite all formats + public index from glossary.json."""
    store = load_store()
    save_store(store)
    print(
        f"Synced {len(store['entries'])} entries → "
        f"json/md/csv/sqlite + {PUBLIC_INDEX.relative_to(ROOT)}"
    )
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    store = load_store()
    entries = store.get("entries", [])
    cats: dict[str, int] = {}
    for e in entries:
        c = e.get("category") or "other"
        cats[c] = cats.get(c, 0) + 1
    print(f"Entries: {len(entries)}")
    print(f"Updated: {store.get('updated')}")
    print("Categories:")
    for c, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="KoreaWiki Translation Memory & Glossary manager"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="Initialize TM store (with seed data)")
    s.add_argument("--force", action="store_true", help="Reseed even if data exists")
    s.add_argument("--empty", action="store_true", help="Create empty store")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("consult", help="Print TM for AI before translating")
    s.add_argument("--limit", type=int, default=200)
    s.set_defaults(func=cmd_consult)

    s = sub.add_parser("lookup", help="Search TM entries")
    s.add_argument("query")
    s.set_defaults(func=cmd_lookup)

    s = sub.add_parser("add", help="Add or merge one entry")
    s.add_argument("--korean", required=True)
    s.add_argument("--vietnamese", required=True)
    s.add_argument("--romanization", default="")
    s.add_argument("--pos", default="")
    s.add_argument("--meaning", default="")
    s.add_argument("--context", default="")
    s.add_argument("--example", default="")
    s.add_argument("--source", default="")
    s.add_argument("--category", default="other")
    s.add_argument("--tags", default="")
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("upsert", help="Bulk upsert from JSON file or stdin")
    s.add_argument("--file", "-f", default="-", help="JSON path or - for stdin")
    s.set_defaults(func=cmd_upsert)

    s = sub.add_parser("edit", help="Edit entry by id")
    s.add_argument("--id", required=True)
    s.add_argument("--korean")
    s.add_argument("--vietnamese")
    s.add_argument("--romanization")
    s.add_argument("--pos")
    s.add_argument("--meaning")
    s.add_argument("--context")
    s.add_argument("--example")
    s.add_argument("--source")
    s.add_argument("--category")
    s.add_argument("--tags")
    s.set_defaults(func=cmd_edit)

    s = sub.add_parser("delete", help="Delete entry by id")
    s.add_argument("--id", required=True)
    s.set_defaults(func=cmd_delete)

    s = sub.add_parser("merge", help="Merge duplicate korean+vietnamese pairs")
    s.set_defaults(func=cmd_merge)

    s = sub.add_parser("export", help="Export TM")
    s.add_argument("--format", choices=["json", "csv", "md", "markdown"], default="json")
    s.add_argument("--output", "-o", default=None)
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("import", help="Import TM")
    s.add_argument("--format", choices=["json", "csv", "md", "markdown"], required=True)
    s.add_argument("--file", "-f", required=True)
    s.add_argument("--replace", action="store_true", help="Replace store instead of merge")
    s.set_defaults(func=cmd_import)

    s = sub.add_parser("quality", help="Detect duplicates, conflicts, missing fields")
    s.add_argument("--strict", action="store_true", help="Exit 1 if any issues")
    s.add_argument("--limit", type=int, default=50)
    s.set_defaults(func=cmd_quality)

    s = sub.add_parser("sync", help="Rewrite all formats and public glossary page")
    s.set_defaults(func=cmd_sync)

    s = sub.add_parser("stats", help="Show TM statistics")
    s.set_defaults(func=cmd_stats)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        code = args.func(args)
    except BrokenPipeError:
        sys.exit(0)
    sys.exit(code if isinstance(code, int) else 0)


if __name__ == "__main__":
    main()
