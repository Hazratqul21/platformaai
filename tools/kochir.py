"""ESKI TIZIMDAN KO'CHIRISH — SQLite → platforma bazasi.

Nima uchun kerak: mijozning yillar davomida yig'ilgan ma'lumoti bor va
platformaga o'tishda u yo'qolmasligi kerak. Bu vosita eski TIZIM ERP
bazasidan (SQLite) mijozlar, ombor, buyurtma, to'lov va kassani o'qib,
platformaga yozadi.

╔══════════════════════════════════════════════════════════════════╗
║  MANBA FAQAT O'QILADI. Vosita manba faylni `mode=ro` (read-only) ║
║  URI bilan ochadi — SQLite darajasida yozish IMKONSIZ. Jonli     ║
║  bazaga emas, ZAXIRA nusxasiga qarating.                          ║
╚══════════════════════════════════════════════════════════════════╝

Asosiy o'girish: eski `orders` jadvalidagi karton ustunlari
(length_mm, grade, layers...) platformada ALOHIDA USTUN EMAS — ular
`attributes` JSON iga tushadi. Shuning uchun ko'chirishda faol profil
`karton` bo'lishi shart, aks holda maydonlar tanilmaydi.

Ishlatish:
    .venv/bin/python tools/kochir.py <eski.db> [--tekshir]

    --tekshir  — hech narsa yozmaydi, faqat nima ko'chishini ko'rsatadi
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal                    # noqa: E402
from app import models as m, domain                # noqa: E402

# Eski `orders` ustuni -> soha maydoni kaliti. Ikkalasi bir xil nomda,
# lekin ro'yxat ATAYLAB aniq yozilgan: eski bazada ortiqcha ustun paydo
# bo'lsa u jimgina `attributes` ga tushib ketmasin.
KARTON_MAYDONLARI = ("length_mm", "width_mm", "height_mm", "layers",
                     "grade", "colors", "is_offset", "tur", "m2_per_box")


def ochish_ro(yol: str) -> sqlite3.Connection:
    """Manbani FAQAT O'QISH uchun ochadi.

    `mode=ro` — SQLite ning o'zi yozishni rad etadi. Xatolik yoki
    e'tiborsizlik tufayli mijozning bazasiga bir harf ham yozilmasin.
    """
    fayl = Path(yol).resolve()
    if not fayl.exists():
        sys.exit(f"❌ Fayl topilmadi: {fayl}")
    conn = sqlite3.connect(f"file:{fayl}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _q(satr, kalit, standart=None):
    """Ustun bo'lmasa yiqilmaydi — eski bazalar turlicha bo'ladi."""
    try:
        qiymat = satr[kalit]
    except (IndexError, KeyError):
        return standart
    return standart if qiymat is None else qiymat


def _d(qiymat, standart="0") -> Decimal:
    try:
        return Decimal(str(qiymat if qiymat is not None else standart))
    except Exception:                                     # noqa: BLE001
        return Decimal(standart)


def _sana(qiymat):
    if not qiymat:
        return None
    matn = str(qiymat)
    for shakl in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(matn[:26], shakl)
        except ValueError:
            continue
    return None


def jadval_bormi(conn, nom: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (nom,)).fetchone())


def kochir(manba: str, tekshir_faqat: bool = False) -> dict:
    conn = ochish_ro(manba)
    db = SessionLocal()
    hisob = {}

    try:
        if domain.profil().kalit != "karton":
            print("⚠️  Faol profil «karton» emas — buyurtma maydonlari "
                  "tanilmasligi mumkin. Avval karton profilini faollashtiring.")

        # ---- 1. Mijozlar --------------------------------------------
        # `eski_id -> yangi obyekt` xaritasi: buyurtma va to'lovlar eski
        # id ga bog'langan, yangi bazada id boshqacha bo'ladi.
        mijoz_xarita = {}
        if jadval_bormi(conn, "clients"):
            for r in conn.execute("SELECT * FROM clients"):
                c = m.Client(
                    company=_q(r, "company", "Nomsiz"),
                    contact=_q(r, "contact", ""), phone=_q(r, "phone", ""),
                    inn=_q(r, "inn", ""), pay_type=_q(r, "pay_type", "Naqd"),
                    category=_q(r, "category", "Standart"),
                    credit_limit=_d(_q(r, "credit_limit")),
                    blacklisted=bool(_q(r, "blacklisted", 0)),
                    opening_balance=_d(_q(r, "opening_balance")),
                )
                db.add(c)
                mijoz_xarita[r["id"]] = c
            db.flush()
        hisob["mijozlar"] = len(mijoz_xarita)

        # ---- 2. Yetkazib beruvchilar ---------------------------------
        yb_xarita = {}
        if jadval_bormi(conn, "suppliers"):
            for r in conn.execute("SELECT * FROM suppliers"):
                sp = m.Supplier(name=_q(r, "name", "Nomsiz"),
                                phone=_q(r, "phone", ""),
                                kind=_q(r, "kind", "xomashyo"))
                db.add(sp)
                yb_xarita[r["id"]] = sp
            db.flush()
        hisob["yetkazib_beruvchilar"] = len(yb_xarita)

        # ---- 3. Materiallar ------------------------------------------
        mat_xarita = {}
        if jadval_bormi(conn, "materials"):
            for r in conn.execute("SELECT * FROM materials"):
                mt = m.Material(
                    name=_q(r, "name", "Nomsiz"),
                    category=_q(r, "category", ""), marka=_q(r, "marka", ""),
                    manufacturer=_q(r, "manufacturer", ""),
                    grammaj=_q(r, "grammaj", ""), unit=_q(r, "unit", "kg"),
                    last_price=_d(_q(r, "last_price")),
                    stock_qty=_d(_q(r, "stock_qty")),
                    min_stock=_d(_q(r, "min_stock")),
                    active=bool(_q(r, "active", 1)),
                )
                db.add(mt)
                mat_xarita[r["id"]] = mt
            db.flush()
        hisob["materiallar"] = len(mat_xarita)

        # ---- 4. Qog'oz partiyalari (karton yo'li) --------------------
        lot_soni = 0
        if jadval_bormi(conn, "raw_lots"):
            for r in conn.execute("SELECT * FROM raw_lots"):
                yb = yb_xarita.get(_q(r, "supplier_id"))
                db.add(m.RawLot(
                    lot_no=_q(r, "lot_no", ""),
                    supplier_id=yb.id if yb else None,
                    grade=_q(r, "grade", ""), grammage=int(_q(r, "grammage", 0) or 0),
                    qty_kg=_d(_q(r, "qty_kg")),
                    remaining_kg=_d(_q(r, "remaining_kg")),
                    price_per_kg=_d(_q(r, "price_per_kg")),
                    received_at=(_sana(_q(r, "received_at")) or datetime.utcnow()).date(),
                ))
                lot_soni += 1
        hisob["qogoz_partiyalari"] = lot_soni

        # ---- 5. Buyurtmalar ------------------------------------------
        # ENG MUHIM QADAM: karton ustunlari `attributes` ga o'tadi.
        buyurtma_xarita = {}
        if jadval_bormi(conn, "orders"):
            for r in conn.execute("SELECT * FROM orders"):
                c = mijoz_xarita.get(_q(r, "client_id"))
                if c is None:
                    continue          # mijozsiz buyurtma — tashlab ketiladi
                atr = {}
                for kalit in KARTON_MAYDONLARI:
                    qiymat = _q(r, kalit)
                    if qiymat is None:
                        continue
                    # Decimal JSON da SATR bo'lib saqlanadi — float aniqlikni
                    # yo'qotadi va tannarx tiyinlarda chalkashadi.
                    atr[kalit] = (str(qiymat) if kalit == "m2_per_box"
                                  else (bool(qiymat) if kalit == "is_offset"
                                        else qiymat))
                yaratilgan = _sana(_q(r, "created_at")) or datetime.utcnow()
                o = m.Order(
                    client_id=c.id, attributes=atr,
                    product_name=_q(r, "product_name", ""),
                    qty=_d(_q(r, "qty"), "1"),
                    delivered_qty=_d(_q(r, "delivered_qty")),
                    unit_cost=_d(_q(r, "unit_cost")),
                    unit_price=_d(_q(r, "unit_price")),
                    total=_d(_q(r, "total")),
                    prepaid_percent=int(_q(r, "prepaid_percent", 0) or 0),
                    status=_q(r, "status", "Kutishda"),
                    note=_q(r, "note", ""), photo=_q(r, "photo", ""),
                    created_at=yaratilgan,
                    due_date=(_sana(_q(r, "due_date")) or yaratilgan).date(),
                    payment_due_date=(_sana(_q(r, "payment_due_date")) or yaratilgan).date(),
                    delivered_at=(_sana(_q(r, "delivered_at")).date()
                                  if _sana(_q(r, "delivered_at")) else None),
                    accepted_stamp=bool(_q(r, "accepted_stamp", 0)),
                )
                db.add(o)
                buyurtma_xarita[r["id"]] = o
            db.flush()
        hisob["buyurtmalar"] = len(buyurtma_xarita)

        # ---- 6. To'lovlar --------------------------------------------
        tolov_soni = 0
        if jadval_bormi(conn, "payments"):
            for r in conn.execute("SELECT * FROM payments"):
                c = mijoz_xarita.get(_q(r, "client_id"))
                if c is None:
                    continue
                o = buyurtma_xarita.get(_q(r, "order_id"))
                db.add(m.Payment(
                    client_id=c.id, order_id=o.id if o else None,
                    amount=_d(_q(r, "amount")), method=_q(r, "method", "Naqd"),
                    paid_at=(_sana(_q(r, "paid_at")) or datetime.utcnow()).date(),
                    note=_q(r, "note", ""),
                ))
                tolov_soni += 1
        hisob["tolovlar"] = tolov_soni

        # ---- 7. Kassa jurnali ----------------------------------------
        # Bog'lanishlar (linked_*) ATAYLAB ko'chirilmaydi: ular eski
        # id larga ishora qiladi va yangi bazada boshqa yozuvga tushib
        # ketishi mumkin edi. Pul summasi va izohi saqlanadi.
        kassa_soni = 0
        if jadval_bormi(conn, "kassa_entries"):
            for r in conn.execute("SELECT * FROM kassa_entries"):
                db.add(m.KassaEntry(
                    direction=_q(r, "direction", "Kirim"),
                    who=_q(r, "who", ""), note=_q(r, "note", ""),
                    amount=_d(_q(r, "amount")),
                    firm=_q(r, "firm", "Asosiy"),
                    currency=_q(r, "currency", "so'm"),
                    entry_at=(_sana(_q(r, "entry_at")) or datetime.utcnow()).date(),
                    created_by=_q(r, "created_by", "ko'chirildi"),
                ))
                kassa_soni += 1
        hisob["kassa_yozuvlari"] = kassa_soni

        # ---- 8. Xodimlar ---------------------------------------------
        xodim_soni = 0
        if jadval_bormi(conn, "employees"):
            for r in conn.execute("SELECT * FROM employees"):
                db.add(m.Employee(
                    name=_q(r, "name", "Nomsiz"),
                    position=_q(r, "position", "Stanokchi"),
                    phone=_q(r, "phone", ""),
                    rate_per_box=_d(_q(r, "rate_per_box"), "150"),
                    brigade=_q(r, "brigade", ""), firm=_q(r, "firm", ""),
                    active=bool(_q(r, "active", 1)),
                ))
                xodim_soni += 1
        hisob["xodimlar"] = xodim_soni

        if tekshir_faqat:
            db.rollback()
            print("🔍 TEKSHIRUV REJIMI — hech narsa yozilmadi")
        else:
            db.add(m.AuditLog(
                who="Ko'chirish vositasi", action="Eski tizimdan ko'chirildi",
                detail=", ".join(f"{k}: {v}" for k, v in hisob.items())))
            db.commit()
    finally:
        db.close()
        conn.close()

    return hisob


def main():
    p = argparse.ArgumentParser(description="Eski TIZIM bazasidan ko'chirish")
    p.add_argument("manba", help="Eski SQLite fayl (ZAXIRA nusxasi!)")
    p.add_argument("--tekshir", action="store_true",
                   help="Hech narsa yozmaydi, faqat sanaydi")
    a = p.parse_args()

    print(f"Manba (faqat o'qish): {a.manba}")
    hisob = kochir(a.manba, a.tekshir)
    print()
    for kalit, son in hisob.items():
        print(f"  {kalit:<24} {son}")
    print(f"\n{'🔍 Tekshirildi' if a.tekshir else '✅ Ko`chirildi'}")


if __name__ == "__main__":
    main()
