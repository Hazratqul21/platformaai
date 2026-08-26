#!/usr/bin/env python3
"""KASSA JURNALINI BOSH KITOBGA O'TKAZISH (o'tmishdagi yozuvlar).

    .venv/bin/python tools/kassa_gl.py --tekshir
    .venv/bin/python tools/kassa_gl.py

NEGA KERAK. Yangi kassa yozuvi endi darhol provodkaga tushadi
(`routers/kassa.py`), lekin BUNDAN OLDIN kiritilganlar tushmagan —
masalan Excel dan ko'chirilgan ma'lumot. Ular ko'chirilmasa
«Бухгалтерия» bo'limi bo'sh turaveradi va foyda-zarar 0 ko'rsatadi.

TAKROR YOZMAYDI. Har provodka `hujjat_turi="kassa"` va `hujjat_id`
bilan yoziladi — allaqachon provodkasi bor yozuv o'tkazib yuboriladi.
Shuning uchun vositani necha marta yurgizsangiz ham summa oshmaydi.

BOG'LANGAN YOZUVGA TEGILMAYDI: mijoz to'lovi va xarid to'lovi kassaga
NUSXA bo'lib tushadi, ularning provodkasi o'z hodisasidan yozilgan.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal                      # noqa: E402
from app import models as m                          # noqa: E402
from app.hisob import ulash as gl_ulash              # noqa: E402

KOK, SARIQ, QIZIL, TUGA = "\033[92m", "\033[93m", "\033[91m", "\033[0m"


def otkaz(tekshir: bool = False) -> dict:
    """`tekshir=True` — HECH NARSA yozilmaydi, faqat sanaladi.

    DIQQAT — bu yerda `rollback` YETMAYDI. `hisob/xizmat.py` dagi
    `provodka_yoz()` o'z ichida `db.commit()` qiladi (provodka yarim
    yozilib qolmasin degan qoida). Ya'ni «yozib ko'rib, keyin
    qaytaramiz» ishlamaydi: yozuv allaqachon saqlangan bo'ladi.
    Birinchi variantda aynan shunday bo'ldi — vosita «hech narsa
    yozilmadi» deb yozdi va o'sha payt 177 provodka yozib qo'ydi.

    Shuning uchun tekshiruv rejimida yozuvchi funksiya UMUMAN
    chaqirilmaydi — faqat nima yozilishi SANALADI.
    """
    db = SessionLocal()
    hisob = {"jami": 0, "yozildi": 0, "bor_edi": 0, "bogliq": 0,
             "valyuta": 0, "xato": 0}
    try:
        # Allaqachon provodkasi bor kassa yozuvlari
        bor = {p.hujjat_id for p in db.query(m.Provodka)
               .filter(m.Provodka.hujjat_turi == "kassa").all()
               if p.hujjat_id}

        yozuvlar = (db.query(m.KassaEntry)
                    .order_by(m.KassaEntry.entry_at, m.KassaEntry.id).all())
        for y in yozuvlar:
            hisob["jami"] += 1
            if y.id in bor:
                hisob["bor_edi"] += 1
                continue
            if any((y.linked_payment_id, y.linked_purchase_id,
                    y.linked_cash_id, y.linked_purchase_payment_id,
                    y.linked_supplier_payment_id)):
                hisob["bogliq"] += 1
                continue
            if (y.currency or "so'm") != "so'm":
                hisob["valyuta"] += 1
                continue
            if tekshir:
                hisob["yozildi"] += 1        # yozilardi — lekin yozilmaydi
                continue
            p = gl_ulash.kassa_yozuvi(db, y, kim="Ko'chirish vositasi")
            if p is None:
                hisob["xato"] += 1
            else:
                hisob["yozildi"] += 1

        if tekshir:
            db.rollback()
            print(f"{SARIQ}🔍 TEKSHIRUV REJIMI — hech narsa yozilmadi "
                  f"(yozuvchi funksiya umuman chaqirilmadi){TUGA}")
        else:
            db.commit()
    finally:
        db.close()
    return hisob


def main():
    p = argparse.ArgumentParser(description="Kassa -> Bosh kitob")
    p.add_argument("--tekshir", action="store_true",
                   help="Hech narsa yozmaydi, faqat sanaydi")
    a = p.parse_args()

    h = otkaz(a.tekshir)
    print(f"\n{'='*50}")
    print(f"  kassa yozuvlari      {h['jami']:>6}")
    print(f"  provodka yozildi     {h['yozildi']:>6}")
    print(f"  allaqachon bor edi   {h['bor_edi']:>6}")
    print(f"  bog'langan (o'tdi)   {h['bogliq']:>6}  (to'lov/xarid nusxasi)")
    print(f"  valyutali (o'tdi)    {h['valyuta']:>6}  (kurs qotirilmagan)")
    if h["xato"]:
        print(f"  {QIZIL}yozilmadi          {h['xato']:>6}{TUGA}")
    print(f"{'='*50}")
    if not a.tekshir:
        print(f"{KOK}✅ Bosh kitobga o'tkazildi{TUGA}")
    return 1 if h["xato"] else 0


if __name__ == "__main__":
    sys.exit(main())
