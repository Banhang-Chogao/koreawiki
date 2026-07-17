"""Check for image cross-contamination: same image used in multiple articles
with different alt text/captions, indicating the mm script reused images.

Scans all content .md files for image references and flags images
that appear in multiple articles (likely recycled by the mm script).
"""
import re
from pathlib import Path
from collections import defaultdict

CONTENT = Path("content")
IMG_PATTERN = re.compile(r'(?:cover:\s*\n?\s*image:\s*"([^"]+)"|figure[^}]*src="([^"]+)")')

def run():
    files = list(CONTENT.rglob("*.md"))
    image_usage = defaultdict(list)

    for fp in sorted(files):
        if fp.name == "_index.md":
            continue
        text = fp.read_text("utf-8")
        seen_in_file = set()
        for m in IMG_PATTERN.finditer(text):
            img = m.group(1) or m.group(2)
            if img and img not in seen_in_file:
                seen_in_file.add(img)
                rel = fp.relative_to(CONTENT)
                image_usage[img].append(rel)

    issues = []
    for img, articles in sorted(image_usage.items()):
        unique_articles = list(dict.fromkeys(articles))
        if len(unique_articles) > 1:
            articles_str = ", ".join(str(a) for a in unique_articles)
            issues.append(f"  {img} shared across: {articles_str}")

    return issues
