#!/usr/bin/env python3
"""Generate WebP from JPEG/PNG images in static/images/"""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "static" / "images"
WEBP_QUALITY = 80

def main():
    if not IMG_DIR.is_dir():
        print(f"Image directory not found: {IMG_DIR}")
        sys.exit(1)

    exts = ("*.jpg", "*.jpeg", "*.png")
    images = []
    for ext in exts:
        images.extend(IMG_DIR.rglob(ext))

    count = 0
    for src in sorted(images):
        webp = src.with_suffix(".webp")
        if webp.exists():
            continue
        img = Image.open(src)
        mode = img.mode
        if mode == "P":
            img = img.convert("RGBA")
        elif mode == "CMYK":
            img = img.convert("RGB")
        elif mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg
        elif mode != "RGB":
            img = img.convert("RGB")
        img.save(webp, "WEBP", quality=WEBP_QUALITY, method=6)
        kb = webp.stat().st_size // 1024
        pct = kb * 100 // max(src.stat().st_size // 1024, 1)
        print(f"  WebP {src.relative_to(ROOT)} → {kb}KB ({pct}% of orig)")
        count += 1

    print(f"\nDone. {count} WebP files generated.")
    if count == 0:
        print("All WebP files already exist.")

if __name__ == "__main__":
    main()
