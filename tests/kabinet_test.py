"""AKKAUNT KABINETI SINOVI — egasi AI sarfini ko'radi, limit qo'yadi.

Ro'yxatdan o'tish -> platforma tokeni -> kabinet. Boshqaruv bazasiga
AI sarfi qo'yiladi va kabinet uni to'g'ri ko'rsatishini tekshiramiz.
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


_tmp = tempfile.mkdtemp(prefix="kabinet_")
os.environ["IJARACHILIK"] = "1"
os.environ["BOSHQARUV_DATABASE_URL"] = f"sqlite:///{_tmp}/boshqaruv.db"
os.environ["MIJOZ_DB_SHABLON"] = f"sqlite:///{_tmp}/{{baza}}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/yagona.db"
os.environ["ASOSIY_DOMEN"] = "innasoft.uz"
os.environ["SEED_EMPTY"] = "1"
os.environ["USD_KURS"] = "12600"
os.environ["AI_USTAMA"] = "1.30"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient       # noqa: E402
from app.main import app                         # noqa: E402
from app import tenancy                          # noqa: E402
from app.platforma import xizmat as px           # noqa: E402
from app.platforma.db import BoshqaruvSession    # noqa: E402
from app.platforma import models as pm           # noqa: E402

print("\n" + "=" * 62)
print("AKKAUNT KABINETI — AI sarfi va limit")
print("=" * 62 + "\n")

with TestClient(app) as c:
    print("1. RO'YXAT VA KIRISH")
    c.post("/api/platforma/royxat", json={
        "login": "aziz@k.uz", "parol": "KabinetP9",
        "akkaunt_kod": "kabtest", "akkaunt_nom": "Kabinet Test", "soha": "mebel"})
    r = c.post("/api/platforma/kir", json={"login": "aziz@k.uz", "parol": "KabinetP9"})
    ok(r.status_code == 200, f"kirish {r.status_code}")
    tok = r.json().get("token")
    ok(bool(tok), "platforma tokeni olindi")
    H = {"authorization": f"Bearer {tok}"}

    print("\n2. TOKENSIZ KIRISH RAD ETILADI")
    ok(c.get("/api/kabinet/mening").status_code == 401, "tokensiz 401")
    ok(c.get("/api/kabinet/mening",
             headers={"authorization": "Bearer soxta"}).status_code == 401,
       "soxta token 401")

    print("\n3. AI SARFI QO'SHAMIZ (boshqaruv bazasiga)")
    db = BoshqaruvSession()
    akk = db.query(pm.Akkaunt).filter(pm.Akkaunt.kod == "kabtest").first()
    px.sarf_yoz(db, akk.id, "gemini", "gemini-2.5-flash",
                kirish_token=500_000, chiqish_token=200_000,
                agent="moliya", user_login="aziz")
    px.sarf_yoz(db, akk.id, "anthropic", "claude-sonnet-5",
                kirish_token=100_000, chiqish_token=50_000,
                agent="sozlash", user_login="dilshod")
    db.close()

    print("\n4. KABINET — MENING")
    r = c.get("/api/kabinet/mening", headers=H).json()
    ok(r["akkaunt"]["nom"] == "Kabinet Test", "akkaunt nomi to'g'ri")
    ok(r["ai"]["sorov"] == 2, f"2 so'rov ko'rsatildi ({r['ai']['sorov']})")
    ok(r["ai"]["som"] > 0, f"AI sarfi: {r['ai']['som']} so'm")
    ok(r["ai"]["limit_som"] == 0 and not r["ai"]["toxtatilgan"],
       "limit qo'yilmagan = cheklovsiz")

    print("\n5. AI SARFI TAFSILOTI")
    r = c.get("/api/kabinet/ai-sarf", headers=H).json()
    ok(len(r["agent_boyicha"]) == 2, f"2 agent bo'yicha ({len(r['agent_boyicha'])})")
    ok(len(r["foydalanuvchi_boyicha"]) == 2, "2 foydalanuvchi bo'yicha")
    # Eng ko'p sarflagan agent birinchi (sonnet qimmat)
    ok(r["agent_boyicha"][0]["nom"] == "sozlash",
       f"eng ko'p sarflagan agent birinchi: {r['agent_boyicha'][0]['nom']}")

    print("\n6. LIMIT QO'YISH")
    jami = c.get("/api/kabinet/mening", headers=H).json()["ai"]["som"]
    r = c.post("/api/kabinet/ai-limit", json={"limit_som": jami * 1.1}, headers=H)
    ok(r.status_code == 200, f"limit qo'yildi {r.status_code}")
    m = c.get("/api/kabinet/mening", headers=H).json()
    ok(m["ai"]["ogoh"] and not m["ai"]["toxtatilgan"],
       f"limitning ~90% i sarflangan — ogoh bor, to'xtamagan ({m['ai']['foiz']}%)")

    r = c.post("/api/kabinet/ai-limit", json={"limit_som": jami * 0.5}, headers=H)
    m = c.get("/api/kabinet/mening", headers=H).json()
    ok(m["ai"]["toxtatilgan"], "limit sarfdan past — AI to'xtatilgan")

    print("\n7. LIMIT MANFIY BO'LMAYDI")
    ok(c.post("/api/kabinet/ai-limit", json={"limit_som": -100},
              headers=H).status_code == 400, "manfiy limit rad etildi")

tenancy.hammasini_yop()
print("\n" + "=" * 62)
if _xato:
    print(f"{QIZIL}{_xato} TA XATO{TUGA}")
    sys.exit(1)
print(f"{KOK}KABINET ISHLADI — AI SARFI SHAFFOF{TUGA}")
print("=" * 62)
