"""AGENT KO'RSATMASI SINOVI — prompt koddan bazaga chiqdimi.

Uch daraja: kod -> platforma -> akkaunt. Va eng muhimi: XAVFSIZLIK
qismi hech qanday tahrirda yo'qolmasligi kerak.
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


_tmp = tempfile.mkdtemp(prefix="korsatma_")
os.environ["IJARACHILIK"] = "1"
os.environ["BOSHQARUV_DATABASE_URL"] = f"sqlite:///{_tmp}/boshqaruv.db"
os.environ["MIJOZ_DB_SHABLON"] = f"sqlite:///{_tmp}/{{baza}}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/yagona.db"
os.environ["ASOSIY_DOMEN"] = "innasoft.uz"
os.environ["SEED_EMPTY"] = "1"
os.environ["PLATFORMA_ADMIN_LOGIN"] = "admin@innasoft.uz"
os.environ["PLATFORMA_ADMIN_PAROL"] = "SuperAdmin9"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient       # noqa: E402
from app.main import app                         # noqa: E402
from app import tenancy, agent as ai             # noqa: E402
from app import korsatma as kors                 # noqa: E402

print("\n" + "=" * 62)
print("AGENT KO'RSATMASI — kod -> platforma -> akkaunt")
print("=" * 62 + "\n")

with TestClient(app) as c:
    # Ikki akkaunt: birida o'zgartiramiz, ikkinchisi tegilmasin
    for kod in ("aaa", "bbb"):
        c.post("/api/platforma/royxat", json={
            "login": f"{kod}@x.uz", "parol": "UserParol9",
            "akkaunt_kod": kod, "akkaunt_nom": kod.upper(), "soha": "mebel"})

    def erp(kod):
        r = c.post("/api/auth/login", json={"login": "admin", "password": "UserParol9"},
                   headers={"host": f"{kod}.innasoft.uz"})
        return {"host": f"{kod}.innasoft.uz",
                "authorization": f"Bearer {r.json()['token']}"}

    A, B = erp("aaa"), erp("bbb")

    print("1. STANDART HOLAT — kod darajasi")
    r = c.get("/api/agent/korsatma", headers=A).json()
    # 5 ta: eski 4 ta (sozlash/ombor/moliya/buyurtma — ko'rsatmasi
    # saqlanadi) + BITTA yordamchi (2026-08-20 dan ishlatiladigani).
    # Ko'rsatma tahriri hamma kalit uchun ochiq qoladi.
    ok(len(r["agentlar"]) == 5, f"5 agent ({len(r['agentlar'])})")
    ok(any(a["kalit"] == "yordamchi" for a in r["agentlar"]),
       "birlashgan «yordamchi» ro'yxatda")
    ok(all(a["manba"] == "kod" for a in r["agentlar"]),
       "hammasi koddan kelyapti")
    ok(len(r["xavfsizlik_qismi"]) > 20, "xavfsizlik qismi ko'rsatilgan")

    print("\n2. AKKAUNT O'Z KO'RSATMASINI YOZADI")
    yangi = ("Sen — ombor yordamchisisan. Bizda «omborchi» deyiladi. "
             "Har javobda material nomini KATTA harfda yoz. " * 2)
    r = c.put("/api/agent/korsatma/ombor", json={"korsatma": yangi}, headers=A)
    ok(r.status_code == 200 and r.json()["manba"] == "akkaunt",
       f"saqlandi ({r.status_code})")

    r = c.get("/api/agent/korsatma", headers=A).json()
    ombor = [a for a in r["agentlar"] if a["kalit"] == "ombor"][0]
    ok(ombor["manba"] == "akkaunt" and "omborchi" in ombor["korsatma"],
       "yangi ko'rsatma ko'rinyapti")

    print("\n3. IKKINCHI AKKAUNTGA O'TMAGANMI  ← eng muhimi")
    r = c.get("/api/agent/korsatma", headers=B).json()
    ombor_b = [a for a in r["agentlar"] if a["kalit"] == "ombor"][0]
    ok(ombor_b["manba"] == "kod" and "omborchi" not in ombor_b["korsatma"],
       "ikkinchi akkaunt o'z (kod) ko'rsatmasini ko'rdi")

    print("\n4. XAVFSIZLIK QISMI YO'QOLMADI")
    tok = tenancy.ornat(tenancy.sorovdan_akkaunt("aaa.innasoft.uz"))
    toliq = kors.ol("ombor")
    tenancy.tozala(tok)
    ok("omborchi" in toliq, "tahrirlangan qism bor")
    ok(ai._UMUMIY_USLUB.strip() in toliq,
       "XAVFSIZLIK qismi (raqamni o'ylab topma) majburan qo'shildi")

    print("\n5. CHEGARALAR")
    ok(c.put("/api/agent/korsatma/ombor", json={"korsatma": "qisqa"},
             headers=A).status_code == 400, "juda qisqa rad etildi")
    ok(c.put("/api/agent/korsatma/ombor", json={"korsatma": "x" * 9000},
             headers=A).status_code == 400,
       "juda uzun rad etildi (AI xarajati)")
    ok(c.put("/api/agent/korsatma/yoq_agent", json={"korsatma": "a" * 100},
             headers=A).status_code == 404, "yo'q agent rad etildi")

    print("\n6. STANDARTGA QAYTARISH")
    r = c.delete("/api/agent/korsatma/ombor", headers=A)
    ok(r.status_code == 200 and r.json()["manba"] == "kod", "koddagi zaxiraga qaytdi")

    print("\n7. PLATFORMA DARAJASI — biz hammaga beramiz")
    r = c.post("/api/platforma/kir",
               json={"login": "admin@innasoft.uz", "parol": "SuperAdmin9"})
    AH = {"authorization": f"Bearer {r.json()['token']}"}
    plat = ("Sen — ombor yordamchisisan. PLATFORMA YANGILANISHI: "
            "javob oxirida qoldiq kamayib borayotgan materialni eslat. " * 2)
    r = c.put("/api/admin/agent-shablon/ombor", json={"korsatma": plat}, headers=AH)
    ok(r.status_code == 200, f"platforma shabloni saqlandi ({r.status_code})")

    for kod, H in (("aaa", A), ("bbb", B)):
        rr = c.get("/api/agent/korsatma", headers=H).json()
        o = [a for a in rr["agentlar"] if a["kalit"] == "ombor"][0]
        ok(o["manba"] == "platforma" and "PLATFORMA YANGILANISHI" in o["korsatma"],
           f"{kod}: platforma ko'rsatmasini oldi (kod qayta joylanmasdan)")

    print("\n8. AKKAUNT TANLOVI PLATFORMANIKIDAN USTUN")
    c.put("/api/agent/korsatma/ombor",
          json={"korsatma": "Sen — ombor yordamchisisan. MENING QOIDAM ustun. " * 3},
          headers=A)
    a_r = [x for x in c.get("/api/agent/korsatma", headers=A).json()["agentlar"]
           if x["kalit"] == "ombor"][0]
    b_r = [x for x in c.get("/api/agent/korsatma", headers=B).json()["agentlar"]
           if x["kalit"] == "ombor"][0]
    ok(a_r["manba"] == "akkaunt" and "MENING QOIDAM" in a_r["korsatma"],
       "o'zgartirgan akkaunt o'z ko'rsatmasini ko'rdi")
    ok(b_r["manba"] == "platforma", "tegmagan akkaunt platformanikida qoldi")

    print("\n9. EGA BO'LMAGAN ROL TAHRIRLAY OLMAYDI")
    ok(c.get("/api/agent/korsatma",
             headers={"host": "aaa.innasoft.uz"}).status_code == 401,
       "tokensiz 401")

tenancy.hammasini_yop()
print("\n" + "=" * 62)
if _xato:
    print(f"{QIZIL}{_xato} TA XATO{TUGA}")
    sys.exit(1)
print(f"{KOK}KO'RSATMA BAZADAN BOSHQARILADI — XAVFSIZLIK SAQLANDI{TUGA}")
print("=" * 62)
