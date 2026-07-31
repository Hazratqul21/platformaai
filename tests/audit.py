"""To'liq modul auditi — har bir ERP/CRM/WMS moduli endpoint'larini
jonli serverda tekshiradi. Ishga tushirish: server ochiq bo'lganda
.venv/bin/python tests/audit.py [port]"""
import json
import sys
import urllib.parse
import urllib.request

PORT = sys.argv[1] if len(sys.argv) > 1 else "8000"
BASE = f"http://localhost:{PORT}"
FAILS = []
MODULES = {}


def call(method, path, body=None, token=None):
    path = urllib.parse.quote(path, safe="/?=&")
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"detail": str(e)}


def ck(module, name, cond, detail=""):
    MODULES.setdefault(module, [0, 0])
    if cond:
        MODULES[module][0] += 1
    else:
        MODULES[module][1] += 1
        FAILS.append(f"[{module}] {name}: {detail}")


rahbar = call("POST", "/api/auth/login", {"login": "admin", "password": "1234"})[1]["token"]

# ============ CRM ============
s, cs = call("GET", "/api/clients", token=rahbar)
ck("CRM", "mijozlar ro'yxati", s == 200)

# ============ Buyurtmalar ============
s, os_ = call("GET", "/api/orders", token=rahbar)
ck("Buyurtmalar", "ro'yxat", s == 200)

# ============ Ombor (WMS) — xomashyo + tayyor + material ============
s, raw = call("GET", "/api/warehouse/raw", token=rahbar)
ck("Ombor(WMS)", "xomashyo qoldiqlari", s == 200 and "groups" in raw)
s, fin = call("GET", "/api/warehouse/finished", token=rahbar)
ck("Ombor(WMS)", "tayyor mahsulot", s == 200)
s, mv = call("GET", "/api/warehouse/moves", token=rahbar)
ck("Ombor(WMS)", "harakatlar tarixi", s == 200)
s, sup = call("GET", "/api/warehouse/suppliers", token=rahbar)
ck("Ombor(WMS)", "yetkazib beruvchilar", s == 200)
s, inv = call("GET", "/api/warehouse/inventory", token=rahbar)
ck("Ombor(WMS)", "inventarizatsiya", s == 200)

# ============ Kataloglar ============
for cat in ["units", "positions", "categories", "materials", "services", "formulas"]:
    s, d = call("GET", f"/api/catalog/{cat}", token=rahbar)
    ck("Kataloglar", cat, s == 200 and isinstance(d, list) and len(d) >= 0)

# ============ Xarid (Zakup) ============
s, pur = call("GET", "/api/purchase", token=rahbar)
ck("Xarid(Zakup)", "xaridlar", s == 200 and "total_bought" in pur)
s, dbt = call("GET", "/api/purchase/debts", token=rahbar)
ck("Xarid(Zakup)", "yetkazib beruvchi qarzlari", s == 200 and "total_debt" in dbt)

# ============ HR ============
s, emps = call("GET", "/api/hr/employees", token=rahbar)
ck("HR", "xodimlar", s == 200)
s, w = call("GET", "/api/hr/work", token=rahbar)
ck("HR", "ish qaydlari", s == 200)
s, csh = call("GET", "/api/hr/cash", token=rahbar)
ck("HR", "kassa", s == 200)
s, pr = call("GET", "/api/hr/payroll", token=rahbar)
ck("HR", "oylik vedomost", s == 200)
s, an = call("GET", "/api/hr/analytics", token=rahbar)
ck("HR", "analitika", s == 200 and "months" in an)

# ============ Moliya ============
s, deb = call("GET", "/api/finance/debtors", token=rahbar)
ck("Moliya", "debitorlar", s == 200)
s, cf = call("GET", "/api/finance/cashflow?days=7", token=rahbar)
ck("Moliya", "pul oqimi", s == 200 and "forecast_balance" in cf)
s, dash = call("GET", "/api/finance/dashboard", token=rahbar)
ck("Moliya", "dashboard", s == 200 and "month_sales" in dash)
s, aud = call("GET", "/api/finance/audit", token=rahbar)
ck("Moliya", "audit jurnali", s == 200)
s, st = call("GET", "/api/finance/settings", token=rahbar)
ck("Moliya", "sozlamalar", s == 200)

# ============ Hisobotlar (Excel/PDF/Word) ============
def raw_ct(path):
    req = urllib.request.Request(BASE + urllib.parse.quote(path, safe="/?=&."))
    req.add_header("Authorization", "Bearer " + rahbar)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, ""


reports = [
    ("warehouse.xlsx", "spreadsheet"), ("cash.xlsx", "spreadsheet"),
    ("payroll.xlsx", "spreadsheet"), ("purchases.xlsx", "spreadsheet"),
]
for name, ct in reports:
    st, ctype = raw_ct(f"/api/reports/{name}")
    ck("Hisobotlar", name, st == 200 and ct in ctype, f"{st} {ctype}")
# mijozga bog'liq hisobotlar (agar mijoz bo'lsa)
if cs:
    cid = cs[0]["id"]
    st, _ = raw_ct(f"/api/reports/sverka/{cid}.xlsx")
    ck("Hisobotlar", "sverka.xlsx", st == 200)
if os_:
    oid = os_[0]["id"]
    for ext in ["pdf"]:
        st, _ = raw_ct(f"/api/reports/act/{oid}.{ext}")
        ck("Hisobotlar", f"act.{ext}", st == 200)
    for ext in ["pdf", "xlsx", "docx"]:
        st, _ = raw_ct(f"/api/reports/nakladnoy/{oid}.{ext}")
        ck("Hisobotlar", f"nakladnoy.{ext}", st == 200)

# ============ Kassa jurnali ============
s, kj = call("GET", "/api/kassa", token=rahbar)
ck("Kassa jurnali", "jurnal", s == 200 and "balans" in kj)
st, ctype = raw_ct("/api/kassa/export.xlsx")
ck("Kassa jurnali", "export.xlsx", st == 200)

# ============ Konstruktor ============
s, sec = call("GET", "/api/sections", token=rahbar)
ck("Konstruktor", "bo'limlar", s == 200)

# ============ Foydalanuvchilar ============
s, us = call("GET", "/api/users", token=rahbar)
ck("Foydalanuvchilar", "ro'yxat", s == 200 and len(us) >= 1)

# ============ NATIJA ============
print("\n" + "=" * 50)
print("  TO'LIQ MODUL AUDITI")
print("=" * 50)
total_ok = total_fail = 0
for mod, (ok, fail) in sorted(MODULES.items()):
    total_ok += ok
    total_fail += fail
    mark = "✓" if fail == 0 else "✗"
    print(f"  {mark} {mod:18s} {ok} ta ishlaydi" + (f", {fail} XATO" if fail else ""))
print("-" * 50)
print(f"  JAMI: {total_ok} endpoint ishlaydi, {total_fail} xato")
if FAILS:
    print("\n  MUAMMOLAR:")
    for x in FAILS:
        print("   -", x)
else:
    print("  ✅ BARCHA MODULLAR TO'LIQ ISHLAYDI")
