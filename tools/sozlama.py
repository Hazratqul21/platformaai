#!/usr/bin/env python3
"""PLATFORMA SOZLAMASINI BAZAGA YOZADI — admin ekranisiz.

    python tools/sozlama.py --korish
    python tools/sozlama.py inn_provayder ihamkor
    python tools/sozlama.py inn_manzil 'https://xxx/api/v1/info?tin={inn}'
    python tools/sozlama.py inn_kalit --sorash
    python tools/sozlama.py inn_kalit --ochir

NEGA ALOHIDA VOSITA, TO'G'RIDAN-TO'G'RI SQL EMAS:

  · KALIT BUYRUQ TARIXIGA TUSHMAYDI. `psql -c "... 'kalit'"` deb
    yozilsa, kalit `~/.bash_history` da, `psql` tarixida va serverning
    `ps` ro'yxatida qoladi. `--sorash` esa uni terminaldan ko'rinmasdan
    o'qiydi va hech qayerga yozmaydi.

  · TEKSHIRUV. `inn_manzil` da `{inn}` o'rni bo'lmasa, qidiruv jimgina
    ishlamay qo'yadi — buni faqat mijoz ro'yxatdan o'tolmaganda bilib
    qolardik. Bu yerda darrov rad etiladi.

  · TASODIFIY YOZUVDAN HIMOYA. Faqat ma'lum kalitlar qabul qilinadi,
    ya'ni xato yozilgan nom yangi keraksiz qator yasab qo'ymaydi.

  · `--korish` da SIR QIYMAT TO'LIQ CHIQMAYDI — faqat oxirgi 4 belgi.
    Ekran yozib olinayotgan bo'lsa ham kalit ochilmaydi.

Serverda ishlatish:

    docker exec -it innasoft-app python tools/sozlama.py --korish
    docker exec -it innasoft-app python tools/sozlama.py inn_kalit --sorash
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.platforma.db import BoshqaruvSession, jadvallarni_yarat   # noqa: E402
from app.platforma import models as pm                             # noqa: E402

# Faqat shular yoziladi. Har biri: (izoh, sirmi)
KALITLAR = {
    "inn_provayder": ("Provayder nomi: ihamkor / maxsus / bo'sh = o'chirilgan", False),
    "inn_manzil":    ("So'rov manzili, {inn} o'rni SHART", False),
    "inn_kalit":     ("API kaliti — SIR", True),
    "inn_sarlavha":  ("Kalit sarlavhasi. Bo'sh = Authorization: Bearer", False),
}


def korinish(kalit: str, qiymat: str) -> str:
    """Sir qiymat to'liq ko'rsatilmaydi."""
    if not qiymat:
        return "(bo'sh)"
    if KALITLAR[kalit][1]:
        return ("…" + qiymat[-4:]) if len(qiymat) > 4 else "…"
    return qiymat


def korsat(db):
    bor = {x.kalit: x for x in db.query(pm.PlatformaSozlama).all()}
    print()
    print(f"{'KALIT':16} {'QIYMAT':46} O'ZGARTIRILGAN")
    print("-" * 84)
    for k, (izoh, sirmi) in KALITLAR.items():
        y = bor.get(k)
        q = korinish(k, y.qiymat if y else "")
        vaqt = y.ozgartirilgan.strftime("%Y-%m-%d %H:%M") if y else "—"
        print(f"{k:16} {q[:46]:46} {vaqt}")
        print(f"{'':16} {izoh}")
    print()
    tayyor = bool(bor.get("inn_provayder") and bor["inn_provayder"].qiymat
                  and bor.get("inn_manzil") and bor["inn_manzil"].qiymat)
    print("INN qidiruvi:", "YOQILGAN" if tayyor else
          "o'chirilgan — forma qo'lda kiritishga o'tadi (bu xato emas)")
    print()


def tekshir(kalit: str, qiymat: str) -> str | None:
    """Xato matnini qaytaradi, xato bo'lmasa None."""
    if kalit == "inn_manzil" and qiymat:
        if not qiymat.startswith(("http://", "https://")):
            return "Manzil http:// yoki https:// bilan boshlansin"
        if "{inn}" not in qiymat:
            return ("Manzilda {inn} o'rni bo'lishi SHART — aks holda har "
                    "so'rov bir xil raqamga ketadi")
    if kalit == "inn_provayder" and qiymat and qiymat not in ("ihamkor", "maxsus"):
        return "Provayder: ihamkor yoki maxsus (yoki bo'sh — o'chirish)"
    return None


def main():
    p = argparse.ArgumentParser(description="Platforma sozlamasi (INN qidiruvi)")
    p.add_argument("kalit", nargs="?", help="; ".join(KALITLAR))
    p.add_argument("qiymat", nargs="?", default=None)
    p.add_argument("--sorash", action="store_true",
                   help="qiymatni terminaldan ko'rinmasdan so'rash (kalit uchun)")
    p.add_argument("--ochir", action="store_true", help="qiymatni bo'shatish")
    p.add_argument("--korish", action="store_true", help="hozirgi holatni ko'rsatish")
    a = p.parse_args()

    jadvallarni_yarat()          # jadval yo'q bo'lsa yaratiladi
    db = BoshqaruvSession()
    try:
        if a.korish or not a.kalit:
            korsat(db)
            return 0

        if a.kalit not in KALITLAR:
            print(f"❌ Noma'lum kalit: {a.kalit}")
            print("   Mumkin:", ", ".join(KALITLAR))
            return 1

        if a.ochir:
            qiymat = ""
        elif a.sorash:
            qiymat = getpass.getpass(f"{a.kalit} qiymati (ko'rinmaydi): ").strip()
        elif a.qiymat is None:
            print(f"❌ Qiymat berilmadi. `--sorash` yoki `--ochir` ishlating.")
            return 1
        else:
            qiymat = a.qiymat.strip()

        xato = tekshir(a.kalit, qiymat)
        if xato:
            print(f"❌ {xato}")
            return 1

        from app.platforma.xizmat import sozlama_yoz
        sozlama_yoz(db, a.kalit, qiymat, sirmi=KALITLAR[a.kalit][1],
                    izoh=KALITLAR[a.kalit][0], kim="tools/sozlama.py")
        db.commit()
        # Qiymatning O'ZI chop etilmaydi — sir bo'lsa ham, bo'lmasa ham
        # bir xil tartib: log fayllarga tushib qolmasin.
        print(f"✅ {a.kalit} yozildi -> {korinish(a.kalit, qiymat)}")
        korsat(db)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
