"""RO'YXATDAN O'TISH — TO'LIQ OQIM SINOVI.

Ro'yxatdan o'tish -> fon vazifasi bazani tayyorlaydi -> firma subdomeniga
kirib ERP ga login qilinadi. Bir jarayonda, ikki firma bilan.

FastAPI TestClient: BackgroundTasks javobdan KEYIN sinxron ishlaydi,
shuning uchun /royxat javobidan so'ng baza tayyor bo'ladi.
"""
import os
import sys
import tempfile
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


_tmp = tempfile.mkdtemp(prefix="royxat_")
os.environ["IJARACHILIK"] = "1"
os.environ["BOSHQARUV_DATABASE_URL"] = f"sqlite:///{_tmp}/boshqaruv.db"
os.environ["MIJOZ_DB_SHABLON"] = f"sqlite:///{_tmp}/{{baza}}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/yagona.db"
os.environ["ASOSIY_DOMEN"] = "innasoft.uz"
os.environ["SEED_EMPTY"] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient       # noqa: E402
from app.main import app                         # noqa: E402
from app import tenancy                          # noqa: E402

print("\n" + "=" * 62)
print("RO'YXATDAN O'TISH — TO'LIQ OQIM")
print("=" * 62 + "\n")

with TestClient(app) as c:
    print("1. RO'YXATDAN O'TISH")
    r = c.post("/api/platforma/royxat", json={
        "login": "aziz@mebel.uz", "parol": "MebelParol9",
        "firma_kod": "mebelsex", "firma_nom": "Mebel Sex MCHJ",
        "inn": "301234567", "soha": "mebel"})
    ok(r.status_code == 200, f"ro'yxatdan o'tish javobi {r.status_code}")
    ok(r.json().get("manzil") == "https://mebelsex.innasoft.uz",
       f"subdomen manzili: {r.json().get('manzil')}")

    print("\n2. BAZA TAYYORLANDIMI (fon vazifasi)")
    h = c.get("/api/platforma/holat/mebelsex").json()
    ok(h["tayyorlik"] == "tayyor", f"baza holati: {h['tayyorlik']} "
       f"({h.get('izoh') or 'izohsiz'})")

    print("\n3. FIRMA SUBDOMENIDA ERP GA KIRISH")
    # Host sarlavhasi orqali middleware firmani aniqlaydi.
    r = c.post("/api/auth/login",
               json={"login": "admin", "password": "MebelParol9"},
               headers={"host": "mebelsex.innasoft.uz"})
    ok(r.status_code == 200, f"ERP login javobi {r.status_code}")
    tok = r.json().get("token")
    ok(bool(tok), "token olindi")
    # Ro'yxatda parol berilgani uchun majburiy almashtirish YO'Q
    ok(not r.json().get("parol_almashtirilsin"),
       "parol ro'yxatda o'rnatilgani uchun majburiy almashtirish yo'q")

    print("\n4. TANLANGAN SOHA FAOL BO'LDIMI")
    r = c.get("/api/soha/joriy", headers={"host": "mebelsex.innasoft.uz",
                                          "authorization": f"Bearer {tok}"})
    ok(r.status_code == 200, f"soha/joriy javobi {r.status_code}")
    ok("mebel" in r.text.lower() or "Mebel" in r.text,
       f"faol soha mebel: {r.json().get('nom', '?')}")

    print("\n5. IKKINCHI FIRMA — ARALASHMAYDIMI")
    c.post("/api/platforma/royxat", json={
        "login": "guli@non.uz", "parol": "NonParol99",
        "firma_kod": "nonzavod", "firma_nom": "Non Zavodi", "soha": "non"})
    r = c.post("/api/auth/login", json={"login": "admin", "password": "NonParol99"},
               headers={"host": "nonzavod.innasoft.uz"})
    tok2 = r.json().get("token")
    ok(bool(tok2), "ikkinchi firma admini kirdi")
    # Mebel firmasining tokeni non firmasida ISHLAMASLIGI kerak
    r = c.get("/api/soha/joriy", headers={"host": "nonzavod.innasoft.uz",
                                          "authorization": f"Bearer {tok}"})
    ok(r.status_code == 401, f"mebel tokeni non firmasida rad etildi ({r.status_code})")

    r = c.get("/api/soha/joriy", headers={"host": "nonzavod.innasoft.uz",
                                          "authorization": f"Bearer {tok2}"})
    ok(r.status_code == 200 and ("non" in r.text.lower()),
       f"non firmasi o'z sohasini ko'rdi: {r.json().get('nom', '?')}")

    print("\n6. TAKRORIY KOD RAD ETILADI")
    r = c.post("/api/platforma/royxat", json={
        "login": "boshqa@x.uz", "parol": "BoshqaParol9",
        "firma_kod": "mebelsex", "firma_nom": "Boshqa"})
    ok(r.status_code == 400, f"band subdomen rad etildi ({r.status_code})")

    print("\n7. FIRMASIZ ERP SO'ROVI RAD ETILADI")
    r = c.get("/api/soha/joriy", headers={"host": "yoqfirma.innasoft.uz"})
    ok(r.status_code == 400, f"yo'q firma so'rovi rad etildi ({r.status_code})")

tenancy.hammasini_yop()
print("\n" + "=" * 62)
if _xato:
    print(f"{QIZIL}{_xato} TA XATO{TUGA}")
    sys.exit(1)
print(f"{KOK}RO'YXATDAN O'TISHDAN ERP GACHA — TO'LIQ ISHLADI{TUGA}")
print("=" * 62)
