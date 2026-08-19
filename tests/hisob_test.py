"""BOSH KITOB SINOVI — ikki yoqlama yozuvning qat'iy qoidalari.

Bu yerda tekshiriladigan narsa «200 qaytdimi» emas — BUXGALTERIYA
QOIDALARI buzilmasligi. Har biri real xatoga qarshi:

  · o'chirilgan provodka -> soliq tekshiruvida javob yo'q
  · yopilgan davrga yozuv -> topshirilgan hisobot bilan mos kelmaydi
  · manfiy summa -> oborot noto'g'ri chiqadi
  · balans buzilishi -> hisobot yig'ilmaydi
"""
import os
import sys
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

KOK, QIZIL, TUGA = "\033[92m", "\033[91m", "\033[0m"
_xato = 0


def ok(shart, matn):
    global _xato
    if shart:
        print(f"{KOK}✅{TUGA} {matn}")
    else:
        _xato += 1
        print(f"{QIZIL}❌{TUGA} {matn}")


_tmp = tempfile.mkdtemp(prefix="hisob_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/gl.db"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import models as m                       # noqa: E402
from app.db import Base, engine, SessionLocal     # noqa: E402
from app.hisob import xizmat as gl                # noqa: E402
NOL = Decimal("0")

Base.metadata.create_all(engine)
db = SessionLocal()

print("\n" + "=" * 62)
print("BOSH KITOB — ikki yoqlama yozuv")
print("=" * 62 + "\n")

print("1. HISOBLAR REJASI VA QOIDALAR YUKLANDI")
n_s, n_q = gl.yukla(db)
ok(n_s >= 25, f"{n_s} schet yuklandi (BHMS №21)")
ok(n_q == 10, f"{n_q} provodka qoidasi")
ok(db.query(m.Schet).filter(m.Schet.kod == "4010").first() is not None,
   "4010 (xaridorlardan olinadigan) bor")
# Ikkinchi marta yuklash takrorlamasin
n_s2, _ = gl.yukla(db)
ok(n_s2 == 0, "qayta yuklashda takrorlanmadi (mijoz o'zgarishi buzilmaydi)")

print("\n2. SOTUV PROVODKASI — qoida bo'yicha")
p = gl.qoida_boyicha(db, "buyurtma_topshirildi", date(2026, 8, 10),
                     {"qqssiz": Decimal("1000000"), "qqs": Decimal("120000"),
                      "tannarx": Decimal("600000")},
                     hujjat_turi="buyurtma", hujjat_id=1, kim="Sinov")
ok(p is not None and len(p.qatorlar) == 3,
   f"3 qator yozildi ({len(p.qatorlar) if p else 0})")
ok(gl.saldo(db, "4010")["qoldiq"] == Decimal("1120000"),
   f"mijoz qarzi 1 120 000 (QQS bilan) — {gl.saldo(db,'4010')['qoldiq']}")
ok(gl.saldo(db, "9010")["qoldiq"] == Decimal("1000000"),
   "daromad QQSSIZ yozildi")
ok(gl.saldo(db, "6410")["qoldiq"] == Decimal("120000"), "QQS majburiyati")

print("\n3. QQS TO'LOVCHI EMAS — QQS qatori tushmaydi")
p2 = gl.qoida_boyicha(db, "buyurtma_topshirildi", date(2026, 8, 11),
                      {"qqssiz": Decimal("500000"), "qqs": Decimal("0"),
                       "tannarx": Decimal("300000")})
ok(len(p2.qatorlar) == 2, f"QQS nol -> 2 qator ({len(p2.qatorlar)})")

print("\n4. TO'LOV QARZNI KAMAYTIRADI")
gl.qoida_boyicha(db, "mijoz_tolovi", date(2026, 8, 12),
                 {"summa": Decimal("620000")}, hujjat_turi="tolov")
ok(gl.saldo(db, "4010")["qoldiq"] == Decimal("1000000"),
   f"qarz 1 620 000 - 620 000 = 1 000 000 ({gl.saldo(db,'4010')['qoldiq']})")
ok(gl.saldo(db, "5010")["qoldiq"] == Decimal("620000"), "kassada 620 000")

print("\n5. BALANS — debet == kredit  ← eng muhimi")
b = gl.balans_tekshiruvi(db)
ok(b["teng"] and b["jami_debet"] == b["jami_kredit"],
   f"jami debet == kredit ({b['jami_debet']}), {b['provodka']} provodka")

print("\n6. QAT'IY QOIDALAR")
try:
    gl.provodka_yoz(db, "qolda", date(2026, 8, 10),
                    [{"debet": "5010", "kredit": "4010", "summa": Decimal("-100")}])
    ok(False, "manfiy summa o'tib ketdi")
except ValueError as e:
    ok("manfiy" in str(e).lower(), "manfiy summa rad etildi (storno ishlatilsin)")

try:
    gl.provodka_yoz(db, "qolda", date(2026, 8, 10),
                    [{"debet": "5010", "kredit": "5010", "summa": Decimal("100")}])
    ok(False, "bir xil schet o'tib ketdi")
except ValueError:
    ok(True, "debet va kredit bir xil bo'lishi rad etildi")

try:
    gl.provodka_yoz(db, "qolda", date(2026, 8, 10),
                    [{"debet": "5010", "kredit": "4010", "summa": Decimal("0")}])
    ok(False, "bo'sh provodka o'tib ketdi")
except ValueError:
    ok(True, "hamma summa nol bo'lgan provodka rad etildi")

print("\n7. STORNO — o'chirish emas, teskari yozuv")
oldingi_qarz = gl.saldo(db, "4010")["qoldiq"]
oldingi_soni = db.query(m.Provodka).count()
st = gl.storno(db, p2.id, "mijoz buyurtmadan voz kechdi", kim="Buxgalter")
ok(db.query(m.Provodka).count() == oldingi_soni + 1,
   "provodka O'CHIRILMADI — yangisi qo'shildi")
ok(db.get(m.Provodka, p2.id) is not None, "asl provodka joyida turibdi")
ok(gl.saldo(db, "4010")["qoldiq"] == oldingi_qarz - Decimal("500000"),
   f"saldo tiklandi ({gl.saldo(db,'4010')['qoldiq']})")
try:
    gl.storno(db, p2.id, "yana")
    ok(False, "ikki marta storno o'tib ketdi")
except ValueError:
    ok(True, "ikki marta storno rad etildi")

print("\n8. YOPILGAN DAVRGA YOZIB BO'LMAYDI")
gl.davrni_yop(db, "2026-08", kim="Buxgalter")
try:
    gl.qoida_boyicha(db, "mijoz_tolovi", date(2026, 8, 20),
                     {"summa": Decimal("100000")})
    ok(False, "yopilgan davrga yozuv o'tib ketdi")
except ValueError as e:
    ok("yopilgan" in str(e), "yopilgan davrga yozuv rad etildi")

# Boshqa oyga yozish ishlashi kerak
p3 = gl.qoida_boyicha(db, "mijoz_tolovi", date(2026, 9, 5),
                      {"summa": Decimal("100000")})
ok(p3 is not None, "yopilmagan oyga yozuv ishlaydi")

print("\n9. HISOBOTLAR")
aq = gl.aylanma_qaydnoma(db)
ok(len(aq) >= 5, f"aylanma qaydnoma: {len(aq)} schet harakatda")
fz = gl.foyda_zarar(db)
ok(fz["daromad"] > 0 and fz["xarajat"] > 0,
   f"foyda-zarar: daromad {fz['daromad']}, xarajat {fz['xarajat']}, "
   f"foyda {fz['foyda']}")

print("\n10. MIJOZ QOIDANI O'ZGARTIRA OLADI")
import json
q = db.query(m.ProvodkaQoida).filter(
    m.ProvodkaQoida.hodisa == "buyurtma_topshirildi").first()
tarif = json.loads(q.tarif_json)
# Savdo korxonasi: 2810 (tayyor mahsulot) o'rniga 2910 (tovarlar)
for qat in tarif["qatorlar"]:
    if qat.get("kredit") == "2810":
        qat["kredit"] = "2910"
q.tarif_json = json.dumps(tarif, ensure_ascii=False)
db.commit()
p4 = gl.qoida_boyicha(db, "buyurtma_topshirildi", date(2026, 9, 6),
                      {"qqssiz": Decimal("200000"), "qqs": Decimal("0"),
                       "tannarx": Decimal("150000")})
kreditlar = {x.kredit for x in p4.qatorlar}
ok("2910" in kreditlar and "2810" not in kreditlar,
   f"o'zgartirilgan qoida ishladi: {kreditlar} (kod yozilmadi)")

print("\n11. BALANS — aktiv == passiv")
# Toza baza: ustav kapitali -> material xaridi -> sotuv -> to'lov
db.query(m.ProvodkaQatori).delete()
db.query(m.Provodka).delete()
db.query(m.YopilganDavr).delete()
db.commit()
# Qoidani standartga qaytaramiz (10-bo'lim uni o'zgartirgan edi)
db.query(m.ProvodkaQoida).delete()
db.commit()
gl.yukla(db)

S = date(2026, 10, 5)
gl.provodka_yoz(db, "qolda", S, [{"debet": "5010", "kredit": "8710",
                                  "summa": Decimal("10000000"),
                                  "izoh": "Ustav kapitali"}])
gl.qoida_boyicha(db, "material_kirim", S,
                 {"qqssiz": Decimal("3000000"), "qqs": NOL})
gl.qoida_boyicha(db, "yetkazuvchiga_tolov", S, {"summa": Decimal("3000000")})
gl.qoida_boyicha(db, "material_ishlab_chiqarishga", S, {"summa": Decimal("2000000")})
gl.qoida_boyicha(db, "mahsulot_tayyor", S, {"summa": Decimal("2000000")})
gl.qoida_boyicha(db, "buyurtma_topshirildi", S,
                 {"qqssiz": Decimal("5000000"), "qqs": Decimal("600000"),
                  "tannarx": Decimal("2000000")})
gl.qoida_boyicha(db, "mijoz_tolovi", S, {"summa": Decimal("4000000")})

b = gl.balans(db)
ok(b["yigildimi"],
   f"aktiv {b['aktiv_jami']} == passiv {b['passiv_jami']} "
   f"(farq {b['farq']})")
fz2 = gl.foyda_zarar(db)
ok(fz2["foyda"] == Decimal("3000000"),
   f"foyda 5 000 000 - 2 000 000 = {fz2['foyda']}")
kodlar = {x["kod"] for x in b["passiv"]}
ok("8330" in kodlar, "joriy davr foydasi passivda ko'rsatildi")

db.close()
print("\n" + "=" * 62)
if _xato:
    print(f"{QIZIL}{_xato} TA XATO{TUGA}")
    sys.exit(1)
print(f"{KOK}BOSH KITOB QOIDALARI QO'RIQLANADI{TUGA}")
print("=" * 62)
