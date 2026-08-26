#!/usr/bin/env python3
"""SOLISHTIRISH — ko'chirilgan ma'lumot manba bilan bir xilmi.

`butunlik.py` bazaning O'Z ICHIDA ziddiyat yo'qligini tekshiradi
(qarz ikki yo'lda bir xilmi, partiyalar qoldiqqa mosmi). Lekin u
MANBANI ko'rmaydi: yarim ko'chirilgan baza ham «butun» chiqishi
mumkin — 61 mijozdan 40 tasi ko'chsa, o'sha 40 tasi o'zaro mos
bo'ladi va tekshiruv yashil beradi.

Bu vosita boshqa savolga javob beradi: **manbada nima bor edi va
platformaga nima yetib bordi.** Har jadval sanaladi, pul jamlari
qo'shiladi va farq ko'rsatiladi.

    .venv/bin/python tools/solishtir.py /yo'l/eski.db

Manba `mode=ro` bilan ochiladi — unga yozish SQLite darajasida
imkonsiz.

UCH XIL NATIJA:
  ✅ teng          — manbadagi hamma narsa yetib bordi
  ⚠️  ko'proq       — platformada ortiq (kutilgan holat: kataloglar
                     seed bilan to'lgan, audit ga ko'chirish yozuvi
                     qo'shilgan)
  ❌ kam           — MA'LUMOT YO'QOLGAN, o'tish qilinmaydi

Chiqish kodi: yo'qotish bo'lsa 1 — cutover skripti shu yerda to'xtaydi.
"""
import sqlite3
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text                          # noqa: E402
from app.db import SessionLocal                      # noqa: E402

KOK, SARIQ, QIZIL, TUGA = "\033[92m", "\033[93m", "\033[91m", "\033[0m"

# Manba jadvali -> platforma jadvali. Soni AYNAN teng bo'lishi kutiladi.
AYNAN = [
    ("clients", "clients"),
    ("suppliers", "suppliers"),
    ("materials", "materials"),
    ("raw_lots", "raw_lots"),
    ("orders", "orders"),
    ("payments", "payments"),
    ("kassa_entries", "kassa_entries"),
    ("employees", "employees"),
    ("purchases", "purchases"),
    ("purchase_payments", "purchase_payments"),
    ("cash_entries", "cash_entries"),
    ("work_entries", "work_entries"),
    ("stock_moves", "stock_moves"),
    ("material_moves", "material_moves"),
    ("payment_schedules", "payment_schedules"),
    ("order_photos", "order_photos"),
]

# Platformada KO'PROQ bo'lishi normal: katalog seed bilan to'lgan,
# audit jurnaliga ko'chirish yozuvi qo'shilgan, `settings` upsert.
KAMAYMASIN = [
    ("units", "units", "seed kataloglari qo'shilgan"),
    ("positions", "positions", "seed kataloglari qo'shilgan"),
    ("categories", "categories", "seed kataloglari qo'shilgan"),
    ("services", "services", "seed xizmatlari qo'shilgan"),
    ("formulas", "formulas", "seed formulalari qo'shilgan"),
    ("settings", "settings", "platforma sozlamalari qo'shilgan"),
    ("audit_logs", "audit_logs", "ko'chirish yozuvi qo'shilgan"),
    ("users", "users", "akkaunt tayyorlangandagi foydalanuvchi"),
]

# Pul jamlari — bittasi ham og'masin. (manba jadvali, ustun, izoh)
PUL = [
    ("orders", "total", "buyurtmalar summasi"),
    ("payments", "amount", "mijoz to'lovlari"),
    ("purchases", "total", "xaridlar"),
    ("purchase_payments", "amount", "xarid to'lovlari"),
    ("cash_entries", "amount", "sex xarajat / avans"),
    ("kassa_entries", "amount", "kassa jurnali"),
]


def _bor(conn, nom: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (nom,)).fetchone())


def _manba_soni(conn, jadval: str) -> int:
    if not _bor(conn, jadval):
        return 0
    return conn.execute(f'SELECT COUNT(*) FROM "{jadval}"').fetchone()[0]


def _manba_jami(conn, jadval: str, ustun: str) -> Decimal:
    if not _bor(conn, jadval):
        return Decimal("0")
    ustunlar = {r[1] for r in conn.execute(f"PRAGMA table_info({jadval})")}
    if ustun not in ustunlar:
        return Decimal("0")
    q = conn.execute(
        f'SELECT COALESCE(SUM("{ustun}"), 0) FROM "{jadval}"').fetchone()[0]
    return Decimal(str(q or 0)).quantize(Decimal("0.01"))


def _platforma_soni(db, jadval: str) -> int:
    return db.execute(text(f'SELECT COUNT(*) FROM "{jadval}"')).scalar() or 0


def _platforma_jami(db, jadval: str, ustun: str) -> Decimal:
    q = db.execute(
        text(f'SELECT COALESCE(SUM("{ustun}"), 0) FROM "{jadval}"')).scalar()
    return Decimal(str(q or 0)).quantize(Decimal("0.01"))


def solishtir(manba_yol: str) -> int:
    fayl = Path(manba_yol).resolve()
    if not fayl.exists():
        sys.exit(f"❌ Manba topilmadi: {fayl}")
    conn = sqlite3.connect(f"file:{fayl}?mode=ro", uri=True)
    db = SessionLocal()
    yoqotish = 0

    try:
        print(f"\nManba (faqat o'qish): {fayl}")
        print("=" * 68)
        print(f"{'JADVAL':<22}{'MANBA':>10}{'PLATFORMA':>12}{'FARQ':>10}  ")
        print("-" * 68)

        for manba_j, dest_j in AYNAN:
            a, b = _manba_soni(conn, manba_j), _platforma_soni(db, dest_j)
            farq = b - a
            if farq == 0:
                belgi, rang = "✅", KOK
            elif farq > 0:
                belgi, rang = "⚠️ ", SARIQ
            else:
                belgi, rang = "❌", QIZIL
                yoqotish += 1
            print(f"{rang}{belgi} {manba_j:<20}{a:>10}{b:>12}{farq:>+10}{TUGA}")

        print("-" * 68)
        for manba_j, dest_j, izoh in KAMAYMASIN:
            a, b = _manba_soni(conn, manba_j), _platforma_soni(db, dest_j)
            if b >= a:
                belgi, rang, qosh = "✅", KOK, ("" if b == a else f"  ({izoh})")
            else:
                belgi, rang, qosh = "❌", QIZIL, "  KAM!"
                yoqotish += 1
            print(f"{rang}{belgi} {manba_j:<20}{a:>10}{b:>12}"
                  f"{b - a:>+10}{TUGA}{qosh}")

        print("\n" + "=" * 68)
        print("PUL JAMLARI — bittasi ham og'masin")
        print("-" * 68)
        for jadval, ustun, izoh in PUL:
            a = _manba_jami(conn, jadval, ustun)
            b = _platforma_jami(db, jadval, ustun)
            farq = b - a
            if farq == 0:
                belgi, rang = "✅", KOK
            else:
                belgi, rang = "❌", QIZIL
                yoqotish += 1
            print(f"{rang}{belgi} {izoh:<26}{a:>16,.2f}{b:>18,.2f}"
                  f"{TUGA}{'' if farq == 0 else f'  farq {farq:+,.2f}'}")

        # Ochiq sessiyalar alohida: muddati o'tganlari ko'chirilmaydi,
        # shuning uchun teng bo'lishi SHART emas — lekin nol bo'lsa
        # odamlar qayta kirishga majbur bo'ladi, buni ko'rsatib qo'yamiz.
        print("\n" + "=" * 68)
        if _bor(conn, "auth_tokens"):
            tirik = conn.execute(
                "SELECT COUNT(*) FROM auth_tokens WHERE expires > datetime('now')"
            ).fetchone()[0]
            bor = _platforma_soni(db, "auth_tokens")
            holat = KOK + "✅" if bor >= tirik else SARIQ + "⚠️ "
            print(f"{holat} ochiq sessiyalar: manbada {tirik} tirik, "
                  f"platformada {bor}{TUGA}")
            if bor < tirik:
                print("   (kam bo'lsa — o'sha odamlar qayta kirishga majbur; "
                      "`kochir.py --kirish` berilganmi?)")

        print("=" * 68)
        if yoqotish:
            print(f"{QIZIL}❌ {yoqotish} ta nomuvofiqlik — O'TISH QILINMASIN{TUGA}")
            return 1
        print(f"{KOK}✅ MANBA BILAN BIR XIL — hech narsa yo'qolmadi{TUGA}")
        return 0
    finally:
        db.close()
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Ishlatish: solishtir.py <eski.db>")
    sys.exit(solishtir(sys.argv[1]))
