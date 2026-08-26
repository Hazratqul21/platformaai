#!/usr/bin/env python3
"""KATALOGLARNI PROFILGA MOSLASH — begona izlarni tozalaydi.

    .venv/bin/python tools/katalog_yangila.py --tekshir
    .venv/bin/python tools/katalog_yangila.py

NEGA KERAK. Ilgari HAR akkauntga karton sexining kataloglari
quyilardi: «Kleychi», «Flekso operatori», «Gofrokarton», «Kraxmal
kley». Bilyard klubi xodim qo'shmoqchi bo'lsa, lavozim ro'yxatidan
«Laminatchi» ni tanlashi kerak edi.

Endi kataloglar profil ichida (`kataloglar` bloki), lekin ILGARI
ochilgan akkauntlarda eski ro'yxat qolgan. Bu vosita ularni
profilga moslaydi.

XAVFSIZLIK — ISHLATILAYOTGANIGA TEGILMAYDI:
  · lavozim — birorta xodimda turgan bo'lsa qoldiriladi
  · material bo'limi — birorta materialda turgan bo'lsa qoldiriladi
  · xizmat/formula — nomi buyurtma izohlarida uchrasa qoldiriladi
Ya'ni vosita faqat HECH QAYERDA ishlatilmagan yozuvni oladi.
Shubha bo'lsa — qoldiradi.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal                      # noqa: E402
from app import models as m, domain                  # noqa: E402
from app.seed import seed_catalogs                   # noqa: E402

KOK, SARIQ, QIZIL, TUGA = "\033[92m", "\033[93m", "\033[91m", "\033[0m"


def _ishlatilgan_lavozimlar(db) -> set[str]:
    return {(e.position or "").strip() for e in db.query(m.Employee).all()}


def _ishlatilgan_kategoriyalar(db) -> set[str]:
    return {(x.category or "").strip() for x in db.query(m.Material).all()}


def yangila(tekshir: bool = False) -> dict:
    db = SessionLocal()
    hisob = {"ochirildi": 0, "qoldirildi": 0, "qoshildi": 0}
    try:
        # Profil shabloni avval YANGILANADI. Akkaunt bazasidagi nusxa
        # eski bo'lishi mumkin (`kataloglar` bloki qo'shilgunicha
        # ochilgan akkaunt). `profillarni_yukla` faqat mijoz TEGMAGAN
        # profilni yangilaydi — tahrirlanganiga tegmaydi.
        from app.migrate import profillarni_yukla
        profillarni_yukla(db)
        domain.qayta_yukla(db)
        profil = domain.profil()
        kat = profil.kataloglar or {}
        print(f"Faol profil: {profil.nom} ({profil.kalit})")
        if not kat:
            print(f"{SARIQ}⚠️  Bu profilda `kataloglar` bloki yo'q — "
                  f"eski yozuvlar tegilmaydi{TUGA}")
            return hisob

        kerak_lavozim = set(kat.get("lavozimlar") or [])
        kerak_kategoriya = set(kat.get("kategoriyalar") or [])
        band_lavozim = _ishlatilgan_lavozimlar(db)
        band_kategoriya = _ishlatilgan_kategoriyalar(db)

        for yozuv in db.query(m.Position).all():
            if yozuv.name in kerak_lavozim:
                continue
            if yozuv.name in band_lavozim:
                hisob["qoldirildi"] += 1
                print(f"  · «{yozuv.name}» qoldirildi — xodimda ishlatilgan")
                continue
            print(f"  − lavozim: {yozuv.name}")
            if not tekshir:
                db.delete(yozuv)
            hisob["ochirildi"] += 1

        for yozuv in db.query(m.Category).all():
            if yozuv.name in kerak_kategoriya:
                continue
            if yozuv.name in band_kategoriya:
                hisob["qoldirildi"] += 1
                print(f"  · «{yozuv.name}» qoldirildi — materialda ishlatilgan")
                continue
            print(f"  − bo'lim: {yozuv.name}")
            if not tekshir:
                db.delete(yozuv)
            hisob["ochirildi"] += 1

        # Xizmat va formula: profilda yo'q bo'lsa va hech qayerda
        # eslatilmagan bo'lsa olinadi.
        kerak_xizmat = {x.get("nom") for x in (kat.get("xizmatlar") or [])}
        kerak_formula = {f.get("nom") for f in (kat.get("formulalar") or [])}
        for yozuv in db.query(m.Service).all():
            if yozuv.name in kerak_xizmat:
                continue
            print(f"  − xizmat: {yozuv.name}")
            if not tekshir:
                db.delete(yozuv)
            hisob["ochirildi"] += 1
        for yozuv in db.query(m.Formula).all():
            if yozuv.name in kerak_formula:
                continue
            print(f"  − formula: {yozuv.name}")
            if not tekshir:
                db.delete(yozuv)
            hisob["ochirildi"] += 1

        if not tekshir:
            db.flush()      # o'chirilganlar hisobga olinsin

        # BIRLIKLAR. Bular matn sifatida material, xizmat va xaridda
        # turadi (FK emas) — shuning uchun o'chirishdan oldin uchala
        # joyda ishlatilmaganiga ishonch hosil qilinadi. Aks holda
        # material birligi ro'yxatda yo'q qiymatga aylanib qolardi.
        kerak_birlik = set(kat.get("birliklar") or [])
        band_birlik = set()
        for x in db.query(m.Material).all():
            band_birlik.add((x.unit or "").strip())
        for x in db.query(m.Service).all():
            band_birlik.add((x.unit or "").strip())
        for x in db.query(m.Purchase).all():
            band_birlik.add((x.unit or "").strip())
        for yozuv in db.query(m.Unit).all():
            if yozuv.name in kerak_birlik:
                continue
            if yozuv.name in band_birlik:
                hisob["qoldirildi"] += 1
                print(f"  · «{yozuv.name}» qoldirildi — ishlatilgan birlik")
                continue
            print(f"  − birlik: {yozuv.name}")
            if not tekshir:
                db.delete(yozuv)
            hisob["ochirildi"] += 1


        if not tekshir:
            db.flush()

        # Profilnikini qo'shamiz (bori takrorlanmaydi)
        oldin = (db.query(m.Position).count() + db.query(m.Category).count()
                 + db.query(m.Service).count() + db.query(m.Formula).count()
                 + db.query(m.Unit).count())
        seed_catalogs(db, kat)
        db.flush()
        keyin = (db.query(m.Position).count() + db.query(m.Category).count()
                 + db.query(m.Service).count() + db.query(m.Formula).count()
                 + db.query(m.Unit).count())
        hisob["qoshildi"] = max(0, keyin - oldin)

        if tekshir:
            db.rollback()
            print(f"\n{SARIQ}🔍 TEKSHIRUV REJIMI — hech narsa "
                  f"o'zgartirilmadi{TUGA}")
        else:
            db.add(m.AuditLog(who="Katalog vositasi",
                              action="Kataloglar profilga moslandi",
                              detail=f"{profil.kalit}: "
                                     f"-{hisob['ochirildi']} +{hisob['qoshildi']}"))
            db.commit()
    finally:
        db.close()
    return hisob


def main():
    p = argparse.ArgumentParser(description="Kataloglarni profilga moslash")
    p.add_argument("--tekshir", action="store_true",
                   help="Hech narsa o'zgartirmaydi, faqat ko'rsatadi")
    a = p.parse_args()
    h = yangila(a.tekshir)
    print(f"\n{'='*46}")
    print(f"  o'chirildi   {h['ochirildi']:>4}")
    print(f"  qo'shildi    {h['qoshildi']:>4}")
    print(f"  qoldirildi   {h['qoldirildi']:>4}  (ishlatilgani)")
    print(f"{'='*46}")
    if not a.tekshir:
        print(f"{KOK}✅ Kataloglar profilga mos{TUGA}")


if __name__ == "__main__":
    main()
