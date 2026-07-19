#!/usr/bin/env python3
"""Fetch GSC safely and create compact, actionable SEO reports.

Secrets are read only from the environment. Raw API rows are never committed: workflow
artifacts retain generated reports and reports/seo is gitignored except its README.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

REPORTS = Path("reports/seo")


def credentials():
    values = {key: os.environ.get(key) for key in ("GSC_CLIENT_EMAIL", "GSC_PRIVATE_KEY", "GSC_SITE_URL")}
    return values if all(values.values()) else None


def get_service(config):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    info = {"type": "service_account", "client_email": config["GSC_CLIENT_EMAIL"], "private_key": config["GSC_PRIVATE_KEY"].replace("\\n", "\n"), "token_uri": "https://oauth2.googleapis.com/token"}
    creds = service_account.Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def query(service, site_url, start, end):
    response = service.searchanalytics().query(siteUrl=site_url, body={"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": ["query", "page"], "rowLimit": 25000}).execute()
    return [{"query": row["keys"][0], "page": row["keys"][1], "clicks": row.get("clicks", 0), "impressions": row.get("impressions", 0), "ctr": row.get("ctr", 0), "position": row.get("position", 0)} for row in response.get("rows", [])]


def aggregate(rows, key):
    groups = defaultdict(lambda: {"clicks": 0, "impressions": 0, "position_total": 0})
    for row in rows:
        group = groups[row[key]]
        group["clicks"] += row["clicks"]
        group["impressions"] += row["impressions"]
        group["position_total"] += row["position"] * row["impressions"]
    return {name: {"clicks": values["clicks"], "impressions": values["impressions"], "ctr": round(values["clicks"] / values["impressions"], 4) if values["impressions"] else 0, "position": round(values["position_total"] / values["impressions"], 2) if values["impressions"] else 0} for name, values in groups.items()}


def directory(url):
    parts = [part for part in urlparse(url).path.split("/") if part]
    return parts[1] if len(parts) > 1 and parts[0] == "koreawiki" else (parts[0] if parts else "/")


def build_report(current, previous, period):
    current_queries, current_pages = aggregate(current, "query"), aggregate(current, "page")
    previous_queries, previous_pages = aggregate(previous, "query"), aggregate(previous, "page")
    directory_rows = [{"directory": name, **values} for name, values in aggregate([{**row, "directory": directory(row["page"])} for row in current], "directory").items()]
    high_ctr = sorted(({"query": name, **values} for name, values in current_queries.items() if values["impressions"] >= 100 and values["ctr"] < 0.02), key=lambda row: row["impressions"], reverse=True)[:25]
    opportunities = sorted(({"query": name, **values} for name, values in current_queries.items() if values["impressions"] >= 50 and 4 <= values["position"] <= 15), key=lambda row: row["impressions"], reverse=True)[:25]
    declines = []
    for name, values in current_pages.items():
        previous_values = previous_pages.get(name)
        if previous_values and previous_values["clicks"] >= 10 and values["clicks"] < previous_values["clicks"] * 0.7:
            declines.append({"page": name, "clicks": values["clicks"], "previous_clicks": previous_values["clicks"], "change": round((values["clicks"] / previous_values["clicks"] - 1), 3)})
    query_pages = defaultdict(set)
    for row in current:
        if row["impressions"] >= 20:
            query_pages[row["query"]].add(row["page"])
    cannibalization = [{"query": query, "pages": sorted(pages)} for query, pages in query_pages.items() if len(pages) > 1][:25]
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "period": period, "by_directory": sorted(directory_rows, key=lambda row: row["impressions"], reverse=True), "by_category": "Category aggregation requires explicit GSC landing-page mapping; directories are reported without inference.", "by_entity": [{"entity": name, **values} for name, values in current_pages.items() if "/entities/" in name], "high_impression_low_ctr": high_ctr, "position_4_15": opportunities, "queries_without_landing_page": "GSC only returns queries with landing pages; use the content-gap candidate list for unmet intents.", "traffic_declines": sorted(declines, key=lambda row: row["change"])[:25], "keyword_cannibalization": cannibalization, "duplicate_intent": "Run scripts/seo_audit.py; it blocks duplicate normalized titles at publish time.", "totals": {"clicks": sum(row["clicks"] for row in current), "impressions": sum(row["impressions"] for row in current)}}


def main():
    config = credentials()
    if not config:
        print("[GSC] credentials unavailable; skipped safely without network access")
        return 0
    try:
        service = get_service(config)
    except ImportError:
        print("[GSC] google-api-python-client is not installed; skipped safely")
        return 0
    today = datetime.now(timezone.utc).date() - timedelta(days=2)
    start = today - timedelta(days=27)
    previous_end, previous_start = start - timedelta(days=1), start - timedelta(days=28)
    try:
        current = query(service, config["GSC_SITE_URL"], start, today)
        previous = query(service, config["GSC_SITE_URL"], previous_start, previous_end)
    except Exception as exc:
        print(f"[GSC] API request failed safely: {exc}", file=sys.stderr)
        return 0
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = build_report(current, previous, {"current": [start.isoformat(), today.isoformat()], "previous": [previous_start.isoformat(), previous_end.isoformat()]})
    target = REPORTS / f"summary-{today.isoformat()}.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    print(f"[GSC] compact report saved to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
