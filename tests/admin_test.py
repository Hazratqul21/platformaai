"""ADMIN PANELI SINOVI — biz hamma akkauntni ko'ramiz va boshqaramiz.

Admin muhit o'zgaruvchisidan yaratiladi. Akkaunt egasi admin
endpointlariga kira OLMASLIGI kerak — bu ham tekshiriladi.
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


_tmp = tempfile.mkdtemp(prefix="admin_")
os.environ["IJARACHILIK"] = "1"
os.environ["BOSHQARUV_DATABASE_URL"] = f"sqlite:///{_tmp}/boshqaruv.db"
os.environ["MIJOZ_DB_SHABLON"] = f"sqlite:///{_tmp}/{{baza}}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/yagona.db"
os.environ["ASOSIY_DOMEN"] = "innasoft.uz"
os.environ["SEED_EMPTY"] = "1"
# Admin muhit o'zgaruvchisidan yaratiladi
os.environ["PLATFORMA_ADMIN_LOGIN"] = "admin@innasoft.uz"
os.environ["PLATFORMA_ADMIN_PAROL"] = "SuperAdmin9"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient       # noqa: E402
from app.main import app                         # noqa: E402
from app import tenancy                          # noqa: E402

print("\n" + "=" * 62)
print("ADMIN PANELI — akkauntlarni boshqarish")
print("=" * 62 + "\n")

with TestClient(app) as c:
    print("1. IKKI AKKAUNT RO'YXATDAN O'TADI")
    for kod, nom, soha in [("aaa", "Birinchi", "mebel"), ("bbb", "Ikkinchi", "non")]:
        c.post("/api/platforma/royxat", json={
            "login": f"{kod}@x.uz", "parol": "UserParol9",
            "akkaunt_kod": kod, "akkaunt_nom": nom, "soha": soha})

    print("\n2. ADMIN KIRADI")
    r = c.post("/api/platforma/kir",
               json={"login": "admin@innasoft.uz", "parol": "SuperAdmin9"})
    ok(r.status_code == 200 and r.json().get("roli") == "admin",
       f"admin kirdi, roli={r.json().get('roli')}")
    AH = {"authorization": f"Bearer {r.json()['token']}"}

    print("\n3. EGA ADMIN ENDPOINTIGA KIRA OLMAYDI")
    r = c.post("/api/platforma/kir", json={"login": "aaa@x.uz", "parol": "UserParol9"})
    UH = {"authorization": f"Bearer {r.json()['token']}"}
    ok(c.get("/api/admin/akkauntlar", headers=UH).status_code == 403,
       "akkaunt egasi admin panelidan 403 oladi")
    ok(c.get("/api/admin/akkauntlar").status_code == 401, "tokensiz 401")

    print("\n4. ADMIN HAMMA AKKAUNTNI KO'RADI")
    r = c.get("/api/admin/akkauntlar", headers=AH).json()
    ok(r["jami"] == 2, f"2 akkaunt ko'rindi ({r['jami']})")
    kodlar = {a["kod"] for a in r["akkauntlar"]}
    ok(kodlar == {"aaa", "bbb"}, f"kodlar: {kodlar}")

    print("\n5. AKKAUNTNI MUZLATISH")
    aid = [a["id"] for a in r["akkauntlar"] if a["kod"] == "aaa"][0]
    r = c.post(f"/api/admin/akkaunt/{aid}/holat",
               json={"holat": "muzlatilgan", "sabab": "to'lov yo'q"}, headers=AH)
    ok(r.status_code == 200 and r.json()["holat"] == "muzlatilgan", "muzlatildi")

    # Muzlatilgan akkaunt YOZA olmaydi, lekin O'QIY oladi
    r = c.post("/api/auth/login", json={"login": "admin", "password": "UserParol9"},
               headers={"host": "aaa.innasoft.uz"})
    tok = r.json().get("token")
    yoz = c.post("/api/clients", json={"company": "Test"},
                 headers={"host": "aaa.innasoft.uz", "authorization": f"Bearer {tok}"})
    ok(yoz.status_code == 402, f"muzlatilgan akkauntda yozish 402 ({yoz.status_code})")
    oqi = c.get("/api/soha/joriy",
                headers={"host": "aaa.innasoft.uz", "authorization": f"Bearer {tok}"})
    ok(oqi.status_code == 200, f"muzlatilgan akkauntda o'qish ochiq ({oqi.status_code})")

    print("\n6. ADMIN QAYTA OCHADI")
    c.post(f"/api/admin/akkaunt/{aid}/holat", json={"holat": "faol"}, headers=AH)
    yoz = c.post("/api/clients", json={"company": "Test"},
                 headers={"host": "aaa.innasoft.uz", "authorization": f"Bearer {tok}"})
    ok(yoz.status_code in (200, 201), f"ochilgach yozish ishlaydi ({yoz.status_code})")

    print("\n7. PLATFORMA AUDIT")
    r = c.get("/api/admin/audit", headers=AH).json()
    amallar = {x["amal"] for x in r["amallar"]}
    ok("holat_ozgardi" in amallar and "akkaunt_yaratildi" in amallar,
       f"audit yozildi: {amallar}")

    print("\n8. NOTO'G'RI HOLAT RAD ETILADI")
    ok(c.post(f"/api/admin/akkaunt/{aid}/holat",
              json={"holat": "yoq_holat"}, headers=AH).status_code == 400,
       "noto'g'ri holat rad etildi")

tenancy.hammasini_yop()
print("\n" + "=" * 62)
if _xato:
    print(f"{QIZIL}{_xato} TA XATO{TUGA}")
    sys.exit(1)
print(f"{KOK}ADMIN PANELI ISHLADI{TUGA}")
print("=" * 62)
