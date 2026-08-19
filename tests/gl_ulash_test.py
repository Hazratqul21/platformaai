"""GL ULASH SINOVI — parallel yozuv eski usulga MOS keladimi.

Bosqich B ning eng muhim sinovi. Jonli server orqali haqiqiy buyurtma
yaratiladi, topshiriladi, to'lov qilinadi — keyin GL saldosi va eski
`services.client_balance` bir xil raqam berayotgani tekshiriladi.

Mos kelmasa — GL ni asosiy manba qilib bo'lmaydi.

⚠️ TOZA BAZA TALAB QILINADI: sinov GLOBAL invariantni tekshiradi
(GL dagi 4010 saldosi == hamma mijozning jami qarzi). Boshqa
sinovlardan qolgan ma'lumot ustiga yurgizilsa raqamlar aralashadi.
`sinov.sh` har to'plamga toza baza beradi (`yurgiz`).
"""
import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

BASE = os.getenv("BASE", "http://localhost:8070")
PAROL = os.getenv("SINOV_PAROL", "Sinov2026Parol")
KOK, QIZIL, TUGA = "\033[92m", "\033[91m", "\033[0m"
_xato = 0
TOKEN = ""


def ok(shart, matn):
    global _xato
    if shart:
        print(f"{KOK}✅{TUGA} {matn}")
    else:
        _xato += 1
        print(f"{QIZIL}❌{TUGA} {matn}")


def so(yol, usul="GET", data=None):
    r = urllib.request.Request(BASE + yol, method=usul,
                               headers={"Content-Type": "application/json",
                                        "Authorization": f"Bearer {TOKEN}"},
                               data=json.dumps(data).encode() if data else None)
    try:
        with urllib.request.urlopen(r) as x:
            return json.loads(x.read() or "{}")
    except urllib.error.HTTPError as e:
        return {"_xato": e.code, "_matn": e.read().decode()[:200]}


print("\n" + "=" * 62)
print("GL ULASH — parallel yozuv eski usulga mos keladimi")
print("=" * 62 + "\n")

# --- kirish ---
r = urllib.request.Request(BASE + "/api/auth/login", method="POST",
                           headers={"Content-Type": "application/json"},
                           data=json.dumps({"login": "admin",
                                            "password": PAROL}).encode())
try:
    with urllib.request.urlopen(r) as x:
        TOKEN = json.loads(x.read())["token"]
except Exception as e:
    print(f"{QIZIL}Serverga kirib bo'lmadi: {e}{TUGA}")
    print(f"Server {BASE} da ADMIN_PAROL={PAROL} bilan ishga tushirilsin")
    sys.exit(1)

print("1. BOSHLANG'ICH HOLAT")
b0 = so("/api/hisob/balans-tekshiruvi")
ok(b0.get("teng") is True, f"balans teng, {b0.get('provodka',0)} provodka")
qarz0 = Decimal(str(so("/api/hisob/qaydnoma").get("jami_debet", 0)))

# --- mijoz va buyurtma ---
mijoz = so("/api/clients", "POST", {"company": "GL Sinov MCHJ", "phone": "+998901112233"})
mid = mijoz.get("id")
ok(bool(mid), f"mijoz yaratildi (#{mid})")

# Majburiy maydonlar profildan olinadi — sinov istalgan sohada yursin
profil = so("/api/soha/joriy")
attrs = {}
for f in profil.get("maydonlar", []):
    if not f.get("majburiy"):
        continue
    if f.get("variantlar"):
        attrs[f["kalit"]] = f["variantlar"][0]
    elif f["tur"] in ("butun", "kasr", "son"):
        attrs[f["kalit"]] = 300
    else:
        attrs[f["kalit"]] = "K1"

buyurtma = so("/api/orders", "POST", {
    "client_id": mid, "qty": 100, "unit_price": 10000,
    "attributes": attrs, "qqs_rejim": "ustiga"})
oid = buyurtma.get("id")
ok(bool(oid), f"buyurtma yaratildi (#{oid}) · jami {buyurtma.get('total')}")

jami = Decimal(str(buyurtma.get("total") or 0))
qqs = Decimal(str(buyurtma.get("qqs_summa") or 0))

print("\n2. TO'LIQ TOPSHIRISH")
# Buyurtmani «tayyor» holatiga olib chiqamiz — ish tartibi bo'yicha
# ketma-ket o'tamiz (profil statuslarni o'zicha atashi mumkin).
statuslar = {st["mano"]: st["nom"] for st in so("/api/soha/joriy")["statuslar"]}
for mano in ("ishlab_chiqarish", "tayyor"):
    if mano in statuslar:
        import urllib.parse
        nom = urllib.parse.quote(statuslar[mano])
        so(f"/api/orders/{oid}/status?status={nom}", "POST")

t = so(f"/api/orders/{oid}/deliver", "POST", {"qty": 100, "paid_amount": 0})
ok("_xato" not in t, f"topshirildi · mijoz qarzi {t.get('client_debt')}")

def gl_saldo(kod):
    q = [x for x in so("/api/hisob/qaydnoma")["qatorlar"] if x["kod"] == kod]
    return Decimal(str(q[0]["qoldiq"])) if q else Decimal("0")


def eski_jami_qarz():
    """HAMMA mijozning qarzi — GL dagi 4010 saldosi shunga teng bo'lishi
    kerak (bitta mijozniki emas: 4010 umumiy schet)."""
    d = so("/api/finance/debtors")
    qatorlar = d if isinstance(d, list) else (
        d.get("debtors") or d.get("qatorlar") or [])
    return sum(Decimal(str(x.get("debt") or x.get("qarz") or 0))
               for x in qatorlar)


ok(abs(gl_saldo("4010") - eski_jami_qarz()) <= 1,
   f"GL qarzi (4010) == eski usul jami: {gl_saldo('4010')} vs {eski_jami_qarz()}")

print("\n3. DAROMAD QQSSIZ YOZILDIMI")
# Shu buyurtmaning provodkasini topib, uning qatorlarini tekshiramiz —
# saldo umumiy bo'lgani uchun (boshqa buyurtmalar ham bor) aynan shu
# hujjatga qaraymiz.
# Bitta hujjatga bir NECHTA provodka bo'lishi normal: material
# ishlab chiqarishga (Дт2010 Кт1010), tayyor mahsulot (Дт2810 Кт2010),
# SOTUV (Дт4010 Кт9010). Bizga sotuv provodkasi kerak.
pr = [p for p in so("/api/hisob/provodkalar")["provodkalar"]
      if p["hujjat"] == f"buyurtma#{oid}"
      and p["hodisa"] == "buyurtma_topshirildi"]
ok(len(pr) == 1, f"sotuv provodkasi yozildi ({len(pr)})")
qatorlar = {(q["debet"], q["kredit"]): Decimal(str(q["summa"]))
            for q in pr[0]["qatorlar"]}
ok(abs(qatorlar.get(("4010", "9010"), Decimal("0")) - (jami - qqs)) <= 1,
   f"Дт4010 Кт9010 = {qatorlar.get(('4010','9010'))} == QQSsiz {jami - qqs}")
if qqs > 0:
    ok(abs(qatorlar.get(("4010", "6410"), Decimal("0")) - qqs) <= 1,
       f"Дт4010 Кт6410 = QQS {qqs}")
else:
    ok(("4010", "6410") not in qatorlar,
       "QQS nol — QQS qatori umuman yozilmadi")

print("\n4. TO'LOV")
kassa_oldin = gl_saldo("5010")
so("/api/finance/payments", "POST", {"client_id": mid, "amount": float(jami / 2),
                             "method": "Naqd"})
kassa_keyin = gl_saldo("5010")
ok(abs(kassa_keyin - kassa_oldin - jami / 2) <= 1,
   f"kassa {kassa_oldin} -> {kassa_keyin} (+{jami/2})")

ok(abs(gl_saldo("4010") - eski_jami_qarz()) <= 1,
   f"to'lovdan keyin GL {gl_saldo('4010')} == eski usul {eski_jami_qarz()}")

print("\n5. BALANS BUZILMADI")
b = so("/api/hisob/balans-tekshiruvi")
ok(b.get("teng") is True,
   f"debet {b.get('jami_debet')} == kredit {b.get('jami_kredit')}")

print("\n6. TO'LOV PROVODKASI HUJJATGA BOG'LANGAN")
tolov_pr = [p for p in so("/api/hisob/provodkalar")["provodkalar"]
            if p["hodisa"] == "mijoz_tolovi"]
ok(len(tolov_pr) >= 1, f"to'lov provodkasi yozildi ({len(tolov_pr)})")

print("\n" + "=" * 62)
if _xato:
    print(f"{QIZIL}{_xato} TA XATO{TUGA}")
    sys.exit(1)
print(f"{KOK}GL ESKI USULGA MOS — PARALLEL ISHLAYAPTI{TUGA}")
print("=" * 62)
