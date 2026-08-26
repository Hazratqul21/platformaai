#!/usr/bin/env python3
"""INNASOFT statik UI assetlari borligini tekshiradi.

Bu test faqat fayl tizimini o'qiydi: server, Docker, baza, tarmoq yoki
foydalanuvchi ma'lumotlariga murojaat qilmaydi. Yangi CSS/JS/screenshot
qo'shilganda broken asset havolalarni build yoki deploydan OLDIN ushlaydi.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
PAGES = (STATIC / "index.html", STATIC / "innasoft.html", STATIC / "platforma-karkas.html")
ASSET_RE = re.compile(r'''(?:href|src)=["']([^"'#?]+)''')


def main() -> int:
    missing: list[tuple[Path, str]] = []
    count = 0
    for page in PAGES:
        if not page.is_file():
            missing.append((page, "sahifa fayli yo'q"))
            continue
        for url in ASSET_RE.findall(page.read_text(encoding="utf-8")):
            # Tashqi manbalar bu lokal, tarmoqqa chiqmaydigan tekshiruvning
            # doirasiga kirmaydi. Faqat shu loyiha ichidagi static assetlar.
            if url.startswith(("http://", "https://", "data:")):
                continue
            # `/` kabi navigatsiya yo'llari asset emas. Bu checker faqat
            # CSS, JS, rasm va boshqa fayl havolalarini tekshiradi.
            if not Path(url).suffix:
                continue
            count += 1
            target = ROOT / url.lstrip("/") if url.startswith("/static/") else page.parent / url
            if not target.is_file():
                missing.append((page, url))

    if missing:
        print("UI STATIC CHECK: XATO", file=sys.stderr)
        for page, asset in missing:
            print(f"  {page.relative_to(ROOT)} -> {asset}", file=sys.stderr)
        return 1

    print(f"UI STATIC CHECK: OK ({len(PAGES)} sahifa, {count} asset havola)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
