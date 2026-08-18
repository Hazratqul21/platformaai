"""BOSHQARUV BAZASI SINOVI — akkaunt, AI sarfi, limit.

Server kerak emas, toza SQLite bazada ishlaydi.

Nima tekshiriladi:
  1. Boshqaruv jadvallari MIJOZ bazasiga tushib qolmaydi (eng muhimi)
  2. Subdomen kodi tekshiruvi
  3. AI sarfi narxi to'g'ri hisoblanadi
  4. Narx QOTIRILADI — jadval o'zgarsa eski yozuv o'zgarmaydi
  5. Limit: 80% ogoh, 100% to'xtatish, 0 = cheklovsiz
"""
import os
import sys
import tempfile
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


_tmp = tempfile.mkdtemp(prefix="platforma_sinov_")
os.environ["BOSHQARUV_DATABASE_URL"] = f"sqlite:///{_tmp}/boshqaruv.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/mijoz.db"
os.environ["USD_KURS"] = "12600"
os.environ["AI_USTAMA"] = "1.30"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Base, engine                       # noqa: E402
from app import models as m                           # noqa: E402,F401
from app.platforma import models as pm, xizmat as px   # noqa: E402
from app.platforma.db import (BoshqaruvSession, boshqaruv_engine,  # noqa: E402
                              jadvallarni_yarat)
from sqlalchemy import inspect                        # noqa: E402

print("\n" + "=" * 62)
print("BOSHQARUV BAZASI SINOVI")
print("=" * 62 + "\n")

# --- 1. Ajratish -------------------------------------------------------
Base.metadata.create_all(engine)      # mijoz bazasi
jadvallarni_yarat()                   # boshqaruv bazasi

mijoz_jadvallar = set(inspect(engine).get_table_names())
boshqaruv_jadvallar = set(inspect(boshqaruv_engine).get_table_names())

print("1. BAZALAR AJRATILGANMI")
ok(not (mijoz_jadvallar & boshqaruv_jadvallar),
   f"mijoz ({len(mijoz_jadvallar)}) va boshqaruv ({len(boshqaruv_jadvallar)}) "
   f"jadvallari kesishmaydi")
ok("akkauntlar" not in mijoz_jadvallar,
   "`akkauntlar` MIJOZ bazasida YO'Q — boshqa mijozlar ro'yxati sizmaydi")
ok("orders" not in boshqaruv_jadvallar,
   "`orders` boshqaruv bazasida yo'q")

db = BoshqaruvSession()

# --- 2. Kod tekshiruvi -------------------------------------------------
print("\n2. SUBDOMEN KODI")
for yomon in ["", "ab", "1mebel", "mebel sex", "www", "admin",
              "mebel_sex", "mebel.sex", "-mebel"]:
    try:
        px.kod_tekshir(yomon)
        ok(False, f"'{yomon}' rad etilishi kerak edi")
    except ValueError:
        pass
ok(True, "noto'g'ri kodlar rad etildi (bo'sh, qisqa, raqamdan boshlangan, "
         "probelli, band nom, pastki chiziq, nuqta, tiredan boshlangan)")
ok(px.kod_tekshir("mebel-sex") == "mebel-sex", "to'g'ri kod qabul qilindi")
# Subdomen katta-kichik harfni ajratmaydi — «Mebel» xato emas, u
# «mebel» ga keltiriladi. Bo'sh joy ham kesiladi.
ok(px.kod_tekshir("  MebelSex  ") == "mebelsex",
   "katta harf va bo'sh joy normallashtiriladi (rad etilmaydi)")
ok(px.baza_nomi_yasa("mebel-sex") == "inna_mebel_sex",
   "baza nomi: tire -> pastki chiziq")

# --- 3. Akkaunt ----------------------------------------------------------
print("\n3. AKKAUNT")
f1 = px.akkaunt_yarat(db, "mebelsex", "Mebel Sex MCHJ", inn="123456789")
f2 = px.akkaunt_yarat(db, "nonzavod", "Non Zavodi")
ok(f1.id and f2.id, "ikki akkaunt yaratildi")
ok(f1.holat == "sinov" and f1.tayyorlik == "tayyorlanmoqda",
   "yangi akkaunt: holat=sinov, tayyorlik=tayyorlanmoqda")
ok(f1.yozish_mumkinmi, "sinov holatida yozish mumkin")
f2.holat = "muzlatilgan"
ok(not f2.yozish_mumkinmi,
   "muzlatilgan akkaunt YOZA olmaydi (lekin o'qish bloklanmaydi)")
try:
    px.akkaunt_yarat(db, "mebelsex", "Boshqa")
    ok(False, "takroriy kod o'tib ketdi")
except ValueError:
    ok(True, "takroriy kod rad etildi")
ok(db.query(pm.PlatformaAudit).filter(
    pm.PlatformaAudit.amal == "akkaunt_yaratildi").count() == 2,
   "auditga ikki yozuv tushdi")

# --- 4. AI sarfi -------------------------------------------------------
print("\n4. AI SARFI VA NARX")
kirish_narx, chiqish_narx = px.narx_mln_som("claude-sonnet-5")
kutilgan_kirish = Decimal("3.00") * Decimal("12600") * Decimal("1.30")
ok(kirish_narx == kutilgan_kirish,
   f"1 mln kirish tokeni = {kirish_narx} so'm (3 USD × 12600 × 1.30)")

s = px.sarf_yoz(db, f1.id, "anthropic", "claude-sonnet-5",
                kirish_token=1_000_000, chiqish_token=100_000,
                agent="moliya", user_login="aziz")
kutilgan = kutilgan_kirish + Decimal("15.00") * Decimal("12600") * Decimal("1.30") / 10
ok(Decimal(str(s.narx_som)) == kutilgan,
   f"1 mln kirish + 100k chiqish = {s.narx_som} so'm")

nomalum = px.narx_mln_som("yangi-model-2027")
ok(nomalum[0] > 0, "noma'lum model bepul emas — qimmatrog'i bo'yicha hisoblanadi")

# --- 5. Narx QOTIRILADI ------------------------------------------------
print("\n5. NARX QOTIRILISHI")
eski_narx = Decimal(str(s.narx_som))
px.NARX_USD_MLN["claude-sonnet-5"] = ("30.00", "150.00")   # provayder 10× oshirdi
yangi = px.sarf_yoz(db, f1.id, "anthropic", "claude-sonnet-5",
                    kirish_token=1_000_000, chiqish_token=100_000)
db.refresh(s)
ok(Decimal(str(s.narx_som)) == eski_narx,
   "narx oshgach ESKI yozuv o'zgarmadi (QQS stavkasi naqshi)")
ok(Decimal(str(yangi.narx_som)) == eski_narx * 10,
   "yangi yozuv yangi narxda")
px.NARX_USD_MLN["claude-sonnet-5"] = ("3.00", "15.00")     # qaytarildi

# --- 6. Limit ----------------------------------------------------------
print("\n6. LIMIT")
db.query(pm.AiSarf).delete()
db.commit()
px.sarf_yoz(db, f1.id, "gemini", "gemini-2.5-flash",
            kirish_token=1_000_000, chiqish_token=1_000_000)
sarf = px.oylik_sarf(db, f1.id)
ok(sarf["sorov"] == 1 and sarf["token"] == 2_000_000,
   f"oylik sarf: {sarf['sorov']} so'rov, {sarf['token']} token, "
   f"{sarf['som']} so'm")

h = px.limit_holati(db, f1.id)
ok(h["limit_som"] == 0 and not h["toxtatilsin"],
   "limit qo'yilmagan = cheklovsiz")

db.add(pm.AiLimit(akkaunt_id=f1.id, oy=px.joriy_oy(),
                  limit_som=sarf["som"] * 2))
db.commit()
h = px.limit_holati(db, f1.id)
ok(h["foiz"] == 50 and not h["ogoh"] and not h["toxtatilsin"],
   f"50% — ogoh yo'q")

db.query(pm.AiLimit).delete()
db.add(pm.AiLimit(akkaunt_id=f1.id, oy=px.joriy_oy(),
                  limit_som=sarf["som"] * Decimal("1.1")))
db.commit()
h = px.limit_holati(db, f1.id)
ok(h["ogoh"] and not h["toxtatilsin"], f"{h['foiz']}% — ogoh bor, to'xtamaydi")

db.query(pm.AiLimit).delete()
db.add(pm.AiLimit(akkaunt_id=f1.id, oy=px.joriy_oy(), limit_som=sarf["som"]))
db.commit()
h = px.limit_holati(db, f1.id)
ok(h["toxtatilsin"], "100% — AI to'xtaydi")

# --- 7. Akkauntlar ajralganmi -------------------------------------------
print("\n7. AKKAUNTLAR SARFI ARALASHMAYDI")
ok(px.oylik_sarf(db, f2.id)["sorov"] == 0,
   "ikkinchi akkauntning sarfi nol — birinchisiniki unga o'tmadi")

db.close()
print("\n" + "=" * 62)
if _xato:
    print(f"{QIZIL}{_xato} TA XATO{TUGA}")
    sys.exit(1)
print(f"{KOK}HAMMASI O'TDI{TUGA}")
print("=" * 62)
