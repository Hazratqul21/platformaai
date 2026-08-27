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
PAGES = (STATIC / "index.html", STATIC / "innasoft.html")
ASSET_RE = re.compile(r'''(?:href|src)=["']([^"'#?]+)''')

REQUIRED_UI_CONTRACTS = {
    STATIC / "index.html": (
        'role="dialog"',
        'aria-modal="true"',
        'id="overlay" aria-hidden="true"',
        'id="toasts" aria-live="polite"',
    ),
    STATIC / "js/core/ui.js": (
        "function modal(html,wide,qulf)",
        "modalFocusables()",
        "modalFoniniQulfla()",
        "_modalOpener.focus",
    ),
    STATIC / "js/pages/agent.js": (
        "agentSemantika()",
        "aria-labelledby','agentNom'",
        'role="log" aria-live="polite"',
    ),
}

FORBIDDEN_UI_CONTRACTS = {
    STATIC / "js/core/ui.js": (
        "modal = function(html,wide)",  # `qulf` parametrini yo'qotgan eski wrapper
    ),
}


def main() -> int:
    missing: list[tuple[Path, str]] = []
    contract_errors: list[tuple[Path, str]] = []
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

    for path, snippets in REQUIRED_UI_CONTRACTS.items():
        if not path.is_file():
            contract_errors.append((path, "contract fayli yo'q"))
            continue
        source = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in source:
                contract_errors.append((path, f"majburiy UI contract yo'q: {snippet}"))

    for path, snippets in FORBIDDEN_UI_CONTRACTS.items():
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet in source:
                contract_errors.append((path, f"xavfli eski pattern qaytdi: {snippet}"))

    if missing or contract_errors:
        print("UI STATIC CHECK: XATO", file=sys.stderr)
        for page, asset in missing:
            print(f"  {page.relative_to(ROOT)} -> {asset}", file=sys.stderr)
        for path, detail in contract_errors:
            print(f"  {path.relative_to(ROOT)} -> {detail}", file=sys.stderr)
        return 1

    contract_count = sum(len(v) for v in REQUIRED_UI_CONTRACTS.values())
    print(f"UI STATIC CHECK: OK ({len(PAGES)} sahifa, {count} asset havola, "
          f"{contract_count} UI contract)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
