"""HAMMA MIJOZ BAZASIDA MIGRATSIYA — ijarachilik uchun.

Bitta bazada `migrate.py` yetarli, lekin 50 mijozda 50 baza bor va har
biri yangilanishi kerak. Bu vosita boshqaruv bazasidan firmalar ro'yxatini
oladi va har biriga: sxema yangilash + butunlik tekshiruvi.

QOIDA: bittasi xato bersa QOLGANLARI DAVOM ETADI. Bitta firma tufayli
hammasi to'xtab qolmasin. Oxirida hisobot.

Ishga tushirish:
    IJARACHILIK=1 BOSHQARUV_DATABASE_URL=... MIJOZ_DB_SHABLON=... \
        .venv/bin/python tools/migratsiya.py --hammasi
    ... --firma mebelsex        # bitta firma
    ... --hammasi --butunlik    # migratsiyadan keyin butunlik ham
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

KOK, QIZIL, SARIQ, TUGA = "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def _firmalar(faqat: str | None):
    from app.platforma.db import BoshqaruvSession
    from app.platforma import models as pm
    db = BoshqaruvSession()
    try:
        q = db.query(pm.Firma).filter(pm.Firma.holat != "ochirilgan")
        if faqat:
            q = q.filter(pm.Firma.kod == faqat)
        return [(f.kod, f.baza_nomi) for f in q.all()]
    finally:
        db.close()


def _bittasi(kod: str, baza_nomi: str, butunlik: bool) -> tuple[bool, str]:
    """Bitta firma bazasini yangilaydi. (muvaffaqiyat, xabar)."""
    from app import tenancy
    from app.platforma.tayyorlash import sxema_tayyorla
    try:
        engine = tenancy.firma_engine(baza_nomi)
        sxema_tayyorla(engine)          # faqat qo'shadi — migrate.py qoidasi
        if butunlik:
            xatolar = _butunlik(baza_nomi)
            if xatolar:
                return False, f"butunlik: {xatolar} nomuvofiqlik"
        return True, "ok"
    except Exception as e:              # noqa: BLE001 — hisobotga yoziladi
        return False, f"{type(e).__name__}: {e}"


def _butunlik(baza_nomi: str) -> int:
    """`butunlik.tekshir_hammasi` ni shu firma bazasida yurgizadi,
    NOMUVOFIQLIK sonini qaytaradi (ogohlantirishlar hisobga olinmaydi)."""
    from app import tenancy
    from tools.butunlik import tekshir_hammasi
    sess = tenancy.firma_sessiya(baza_nomi)
    try:
        n = tekshir_hammasi(sess)
        return len(n.xato)
    finally:
        sess.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--hammasi", action="store_true")
    p.add_argument("--firma", type=str, default=None)
    p.add_argument("--butunlik", action="store_true",
                   help="migratsiyadan keyin butunlik tekshiruvi ham")
    a = p.parse_args()

    if not os.getenv("IJARACHILIK"):
        print(f"{SARIQ}Ogohlantirish: IJARACHILIK yoqilmagan. Bu vosita "
              f"ijarachilik rejimi uchun.{TUGA}")
    if not (a.hammasi or a.firma):
        print("--hammasi yoki --firma <kod> bering")
        return 2

    firmalar = _firmalar(None if a.hammasi else a.firma)
    if not firmalar:
        print("Firma topilmadi")
        return 0

    print(f"\n{len(firmalar)} ta baza yangilanadi"
          f"{' + butunlik' if a.butunlik else ''}\n" + "─" * 54)
    muvaffaq, xato = 0, []
    for kod, baza in firmalar:
        ok, xabar = _bittasi(kod, baza, a.butunlik)
        belgi = f"{KOK}✓{TUGA}" if ok else f"{QIZIL}✗{TUGA}"
        print(f"  {belgi} {kod:20s} {xabar}")
        if ok:
            muvaffaq += 1
        else:
            xato.append(kod)

    print("─" * 54)
    print(f"  {muvaffaq}/{len(firmalar)} muvaffaqiyatli")
    if xato:
        print(f"{QIZIL}  XATO: {', '.join(xato)}{TUGA}")
        return 1
    print(f"{KOK}  HAMMASI YANGILANDI{TUGA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
