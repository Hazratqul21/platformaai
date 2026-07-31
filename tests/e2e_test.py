"""GOFRA ERP — to'liq hayotiy sikl (E2E) testi. Har bir TZ bandi tekshiriladi."""
import json
import urllib.parse
import urllib.request

BASE = "http://localhost:8000"
FAILS = []


def call(method, path, body=None, token=None, expect=200):
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
        return e.code, json.loads(e.read())


def check(name, cond, detail=""):
    mark = "✓" if cond else "✗"
    print(f"{mark} {name}" + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        FAILS.append(f"{name}: {detail}")


def login(u):
    s, d = call("POST", "/api/auth/login", {"login": u, "password": "1234"})
    assert s == 200, d
    return d["token"]


rahbar = login("admin")

# ---------- Foydalanuvchi boshqaruvi: admin o'zi xodimlarga login yaratadi ----------
for lg, nm, rl in [("menejer", "Aziza Y.", "Menejer"), ("sklad", "Bobur T.", "Sklad mudiri"),
                   ("sex", "Jasur E.", "Sex boshlig'i"), ("buxgalter", "Nilufar S.", "Buxgalter")]:
    s, d = call("POST", "/api/users", {"login": lg, "password": "1234", "name": nm, "role": rl}, rahbar)
    check(f"Admin xodimga login yaratdi: {lg}", s == 200, str(d))

s, d = call("POST", "/api/users", {"login": "menejer", "password": "1234", "name": "X", "role": "Menejer"}, rahbar)
check("Takroriy login rad etiladi (409)", s == 409, str(d))
s, d = call("POST", "/api/users", {"login": "test2", "password": "12", "name": "X", "role": "Menejer"}, rahbar)
check("Qisqa parol rad etiladi", s == 400, str(d))

menejer = login("menejer")
sklad = login("sklad")
sex = login("sex")
bux = login("buxgalter")

s, d = call("POST", "/api/users", {"login": "hack", "password": "1234", "name": "H", "role": "Rahbar"}, menejer)
check("Oddiy xodim user yarata olmaydi (403)", s == 403, str(d))
s, us = call("GET", "/api/users", token=rahbar)
check("Foydalanuvchilar ro'yxati (5 ta)", s == 200 and len(us) == 5, str(len(us) if s == 200 else d))
# parol yangilash
uid_m = [u["id"] for u in us if u["login"] == "menejer"][0]
s, d = call("POST", f"/api/users/{uid_m}/password", {"password": "9999"}, rahbar)
check("Admin parol yangilaydi", s == 200, str(d))
s, d = call("POST", "/api/auth/login", {"login": "menejer", "password": "9999"})
check("Yangi parol bilan kirish ishlaydi", s == 200, str(d))
menejer = d["token"] if s == 200 else menejer
# o'chirish testi (vaqtinchalik user)
s, d = call("POST", "/api/users", {"login": "tmp", "password": "1234", "name": "Tmp", "role": "Menejer"}, rahbar)
s, d2 = call("DELETE", f"/api/users/{d['id']}", token=rahbar)
check("Admin userni o'chiradi", s == 200 or d2.get("ok"), str(d2))
me_id = [u["id"] for u in us if u["login"] == "admin"][0]
s, d = call("DELETE", f"/api/users/{me_id}", token=rahbar)
check("O'zini o'chirish taqiqlangan", s == 400, str(d))

# ---------- 1. CRM ----------
s, c = call("POST", "/api/clients", {
    "company": "TEST Qurilish MChJ", "contact": "Test Aka", "phone": "+998900000001",
    "inn": "123456789", "pay_type": "Naqd", "category": "Yangi",
    "credit_limit": 5_000_000}, menejer)
check("1.1 Mijoz yaratish (menejer)", s == 200 and c["id"], str(c)[:100])
CID = c["id"]

s, d = call("POST", "/api/clients", {"company": "X"}, sklad, )
check("6. Rol cheklovi: sklad mijoz yarata olmaydi", s == 403, str(d))

# ---------- 1.2 Smeta ----------
s, q = call("POST", "/api/orders/quote", {
    "length_mm": 400, "width_mm": 300, "height_mm": 250, "layers": 3,
    "grade": "K1", "colors": 2, "qty": 1000, "client_id": CID}, menejer)
m2_expected = ((400 + 300) * 2 + 40) * (250 + 300) / 1e6
check("1.2 m² formula (FEFCO 0201)", abs(q["m2_per_box"] - m2_expected) < 1e-6,
      f"{q['m2_per_box']} vs {m2_expected}")
check("1.2 5% brak jami m²da", abs(q["need_m2_total"] - round(q["m2_per_box"] * 1000 * 1.05, 2)) < 0.01,
      str(q["need_m2_total"]))
check("1.2 Menejer bloki: tannarx/marja bor", "unit_cost" in q and "margin_percent" in q)
check("1.2 Yangi mijoz marjasi 30%", q["margin_percent"] == 30, str(q["margin_percent"]))
# tannarx = material*1.05 + labor + colors*120
s, st = call("GET", "/api/finance/settings", token=rahbar)
calc_cost = round(q["m2_per_box"] * q["material_price_m2"] * 1.05 + 150 + 2 * 120, 2)
check("4.1 Tannarx formulasi", abs(q["unit_cost"] - calc_cost) < 0.02, f"{q['unit_cost']} vs {calc_cost}")

# ---------- Kredit limiti: block rejimi ----------
call("POST", "/api/finance/settings", {"values": {"credit_mode": "block"}}, rahbar)
s, d = call("POST", "/api/orders", {
    "length_mm": 400, "width_mm": 300, "height_mm": 250, "layers": 3, "grade": "K1",
    "colors": 0, "qty": 5000, "client_id": CID}, menejer)  # ~18 mln > 5 mln limit
check("4.2 Limit oshsa block rejimida 409", s == 409, f"status={s} {str(d)[:80]}")
call("POST", "/api/finance/settings", {"values": {"credit_mode": "warn"}}, rahbar)

# ---------- Buyurtma + status oqimi ----------
s, o = call("POST", "/api/orders", {
    "length_mm": 400, "width_mm": 300, "height_mm": 250, "layers": 3, "grade": "K1",
    "colors": 1, "qty": 1000, "client_id": CID, "prepaid_percent": 30}, menejer)
check("1.3 Buyurtma yaratildi (Kutishda)", s == 200 and o["status"] == "Kutishda", str(o)[:100])
OID = o["id"]

# FIFO tekshiruvi: spisaniyadan oldin eng eski lot qoldig'i (ombor kg hisobida)
s, raw = call("GET", "/api/warehouse/raw", token=sklad)
k1 = [g for g in raw["groups"] if g["grade"] == "K1"][0]
open_lots = [l for l in k1["lots"] if l["remaining_kg"] > 0]
oldest = min(open_lots, key=lambda l: l["received_at"])
before = oldest["remaining_kg"]

s, d = call("POST", f"/api/orders/{OID}/status?status=Muzokara", token=menejer)
check("1.3 Kutishda→Muzokara", s == 200 and d["status"] == "Muzokara", str(d)[:80])
s, d = call("POST", f"/api/orders/{OID}/status?status=Sexda kesilmoqda", token=menejer)
check("1.3 Muzokara→Sexda (tasdiq)", s == 200, str(d)[:80])

s, raw2 = call("GET", "/api/warehouse/raw", token=sklad)
k1b = [g for g in raw2["groups"] if g["grade"] == "K1"][0]
oldest_after = [l for l in k1b["lots"] if l["id"] == oldest["id"]][0]
# kerakli m² ni lot grammaji bo'yicha kg ga o'giramiz
need_m2 = o["m2_per_box"] * 1000 * 1.05
need_kg = need_m2 * (k1["grammage"] / 1000)
check("2.1 FIFO: eng eski lotdan yechildi", oldest_after["remaining_kg"] < before,
      f"{before} -> {oldest_after['remaining_kg']}")
check("2.2 Brak 5% bilan yechildi (kg)", abs((k1["stock_kg"] - k1b["stock_kg"]) - need_kg) < 0.5,
      f"yechilgan={k1['stock_kg']-k1b['stock_kg']:.2f} kg kutilgan={need_kg:.2f} kg")

# Sex boshlig'i faqat Omborga o'tkaza oladi, Yetkazildi — Sklad mudiri/Rahbar
s, d = call("POST", f"/api/orders/{OID}/status?status=Yetkazib berildi", token=rahbar)
check("1.3 Sexdan to'g'ri Yetkazildi'ga sakrab bo'lmaydi", s == 400, str(d)[:80])
s, d = call("POST", f"/api/orders/{OID}/status?status=Omborga tushdi", token=sex)
check("1.3 Sexda→Omborga (sex boshlig'i)", s == 200, str(d)[:80])

# Tayyor mahsulot omborida ko'rinadi
s, fin = call("GET", "/api/warehouse/finished", token=sklad)
check("2.1 Tayyor mahsulot omborida", any(x["order_id"] == OID for x in fin))

# Mijozga topshirish (to'liq) — endi qarz TOPSHIRILGAN mol bo'yicha hisoblanadi
s, d = call("POST", f"/api/orders/{OID}/deliver", {"qty": o["qty"], "paid_amount": 0}, rahbar)
check("1.3 Omborga→Mijozga topshirildi (to'liq)", s == 200 and d["status"] == "Yetkazib berildi",
      str(d)[:80])
check("Qisman topshirish: delivered_qty to'g'ri", d["delivered_qty"] == o["qty"], str(d.get("delivered_qty")))

# ---------- e-tasdiq stempeli ----------
s, d = call("POST", f"/api/orders/{OID}/accept-stamp", token=menejer)
check("5.1 E-tasdiq stempeli", s == 200 and d["accepted_stamp"] is True)

# ---------- Debitor / to'lov / aging ----------
s, bal = call("GET", f"/api/clients/{CID}", token=bux)
total = o["total"]
check("4.2 Balans karta: qarz = topshirilgan mol − to'langan", abs(bal["debt"] - total) < 0.01,
      f"{bal['debt']} vs {total}")
s, d = call("POST", "/api/finance/payments", {"client_id": CID, "order_id": OID,
                                              "amount": total / 2, "method": "Naqd"}, bux)
check("4.2 To'lov qabul qilindi", s == 200)
s, bal = call("GET", f"/api/clients/{CID}", token=bux)
check("4.2 Qarz yarmiga tushdi", abs(bal["debt"] - total / 2) < 0.01, str(bal["debt"]))
s, deb = call("GET", "/api/finance/debtors", token=bux)
me = [x for x in deb if x["client_id"] == CID]
check("4.2 Aging: 0-15 bucketda", me and abs(me[0]["aging"]["0-15"] - total / 2) < 0.01,
      str(me[:1]))

# ---------- Takroriy buyurtma ----------
s, r = call("POST", f"/api/orders/{OID}/reorder?qty=500", token=menejer)
check("1.1 Takroriy buyurtma", s == 200 and r["qty"] == 500 and r["status"] == "Kutishda",
      str(r)[:80])

# ---------- Qora ro'yxat ----------
s, d = call("PUT", f"/api/clients/{CID}", {
    "company": "TEST Qurilish MChJ", "contact": "Test Aka", "phone": "+998900000001",
    "inn": "123456789", "pay_type": "Naqd", "category": "Yangi",
    "credit_limit": 5_000_000, "blacklisted": True}, menejer)
s, d = call("POST", "/api/orders", {"length_mm": 300, "width_mm": 200, "height_mm": 150,
                                    "layers": 3, "grade": "K1", "colors": 0, "qty": 100,
                                    "client_id": CID}, menejer)
check("1.1 Qora ro'yxat: buyurtma bloklanadi", s == 409, f"status={s}")

# ---------- Ombor: kirim + inventarizatsiya (kg hisobida, marka erkin yoziladi) ----------
s, lot = call("POST", "/api/warehouse/raw", {"supplier_id": 1, "grade": "Erkin marka X",
                                             "grammage": 140, "qty_kg": 1000,
                                             "price_per_kg": 8500}, sklad)
check("2.1 Lot kirimi (erkin marka, kg)", s == 200 and lot["lot_no"], str(lot))
s, raw = call("GET", "/api/warehouse/raw", token=sklad)
k0 = [g for g in raw["groups"] if g["grade"] == "Erkin marka X"][0]
sys_kg = k0["stock_kg"]
check("2.1 Kirim kg to'g'ri yozildi", abs(sys_kg - 1000) < 0.01, f"{sys_kg} kg")
s, inv = call("POST", "/api/warehouse/inventory", {"grade": "Erkin marka X", "grammage": 140,
                                                   "actual_kg": sys_kg - 50, "note": "test"}, sklad)
check("2.2 Inventarizatsiya: kamomad aktlashtirildi", s == 200 and abs(inv["diff_kg"] + 50) < 0.01,
      str(inv))
s, raw = call("GET", "/api/warehouse/raw", token=sklad)
k0b = [g for g in raw["groups"] if g["grade"] == "Erkin marka X"][0]
check("2.2 Kamomad qoldiqdan yechildi", abs(k0b["stock_kg"] - (sys_kg - 50)) < 0.01,
      f"{k0b['stock_kg']} vs {sys_kg-50}")

# ---------- HR ----------
s, emps = call("GET", "/api/hr/employees", token=sex)
E = emps[0]["id"]
before_today = emps[0]["today_earned"]
s, w = call("POST", "/api/hr/work", {"employee_id": E, "qty": 200, "qc_passed": True}, sex)
check("3.1 QC o'tgan ish: pul yozildi", s == 200 and w["amount"] == emps[0]["rate_per_box"] * 200,
      str(w))
s, w2 = call("POST", "/api/hr/work", {"employee_id": E, "qty": 50, "qc_passed": False}, sex)
check("3.1 QC o'tmagan: 0 so'm", s == 200 and w2["amount"] == 0, str(w2))
s, emps2 = call("GET", "/api/hr/employees", token=sex)
check("3.1 Real vaqt kunlik hisob", emps2[0]["today_earned"] == before_today + w["amount"],
      f"{emps2[0]['today_earned']} vs {before_today}+{w['amount']}")
s, d = call("POST", "/api/hr/cash", {"employee_id": E, "kind": "Avans", "amount": 300000}, bux)
check("3.2 Avans kassaga yozildi", s == 200)
s, pr = call("GET", "/api/hr/payroll", token=bux)
me_pr = [r for r in pr if r["employee_id"] == E][0]
check("3.3 Oylik = ishbay − avans", abs(me_pr["net"] - (me_pr["earned"] - me_pr["advances"])) < 0.01,
      str(me_pr))

# ---------- HR analitika (kirdi-chiqdi, brak %, fond dinamikasi) ----------
s, an = call("GET", "/api/hr/analytics", token=bux)
check("HR analitika: 6 oylik seriya", s == 200 and len(an["months"]) == 6, str(an)[:80])
cur = an["months"][-1]
check("HR analitika: joriy oy fondi = payroll yig'indisi",
      abs(cur["earned"] - sum(r["earned"] for r in pr)) < 0.01,
      f"{cur['earned']} vs {sum(r['earned'] for r in pr)}")
emp_an = [x for x in an["per_employee"] if x["id"] == E][0]
check("HR analitika: xodim balans = kirdi − chiqdi",
      abs(emp_an["balance"] - (emp_an["earned_total"] - emp_an["taken_total"])) < 0.01, str(emp_an))
check("HR analitika: brak % hisoblanadi",
      emp_an["boxes_bad"] >= 50 and emp_an["brak_percent"] > 0, str(emp_an))
check("HR analitika: 1 qutiga fakt ish haqi",
      an["totals"]["labor_per_box_fact"] > 0, str(an["totals"]))
s, d = call("GET", "/api/hr/analytics", token=menejer)
check("HR analitika menejer uchun yopiq (403)", s == 403, str(d))

# ---------- Kreditor ----------
s, sups = call("GET", "/api/warehouse/suppliers", token=bux)
sp = sups[0]
debt_before = sp["debt"]
s, d = call("POST", "/api/warehouse/suppliers/pay", {"supplier_id": sp["id"],
                                                     "amount": 1_000_000}, bux)
check("4.3 Yetkazib beruvchiga to'lov", s == 200)
s, sups2 = call("GET", "/api/warehouse/suppliers", token=bux)
sp2 = [x for x in sups2 if x["id"] == sp["id"]][0]
check("4.3 Kreditor qarz kamaydi", abs(sp2["debt"] - (debt_before - 1_000_000)) < 0.01,
      f"{sp2['debt']} vs {debt_before-1_000_000}")

# ---------- Cash flow / dashboard ----------
s, cf = call("GET", "/api/finance/cashflow?days=7", token=rahbar)
check("4.3 Cash flow prognoz", s == 200 and cf["forecast_balance"] == cf["expected_in"] - cf["expected_out"])
s, dash = call("GET", "/api/finance/dashboard", token=rahbar)
check("4.4 Dashboard to'liq", all(k in dash for k in
      ["today_sales", "month_sales", "growth_percent", "total_debit", "total_credit",
       "top_debtors", "margins", "low_stock", "cashflow"]))

# ---------- Sozlama ta'siri ----------
call("POST", "/api/finance/settings", {"values": {"brak_percent": "8"}}, rahbar)
s, q2 = call("POST", "/api/orders/quote", {"length_mm": 400, "width_mm": 300, "height_mm": 250,
                                           "layers": 3, "grade": "K1", "colors": 0, "qty": 100}, menejer)
check("Sozlama: brak 8% smeta o'zgardi",
      abs(q2["need_m2_total"] - round(q2["m2_per_box"] * 100 * 1.08, 2)) < 0.01, str(q2["need_m2_total"]))
call("POST", "/api/finance/settings", {"values": {"brak_percent": "5"}}, rahbar)


# ---------- Yuk xati (nakladnoy) 3 format ----------
def raw(path, token):
    req = urllib.request.Request(BASE + urllib.parse.quote(path, safe="/?=&"))
    req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, ""

for ext, ct in [("pdf", "pdf"), ("xlsx", "spreadsheet"), ("docx", "wordprocessing")]:
    st, ctype = raw(f"/api/reports/nakladnoy/{OID}.{ext}", bux)
    check(f"5. Yuk xati .{ext}", st == 200 and ct in ctype, f"{st} {ctype}")

# ---------- Konstruktor ----------
s, sec = call("POST", "/api/sections", {"name": "Test bo'lim", "icon": "🛠",
              "fields": [{"label": "Nomi", "type": "matn"}, {"label": "Narxi", "type": "pul"}]}, rahbar)
check("Konstruktor: bo'lim yaratildi", s == 200 and sec["fields"][0]["key"] == "f1", str(sec)[:80])
SID = sec["id"]
s, d = call("POST", f"/api/sections/{SID}/records", {"data": {"f1": "Pichoq", "f2": "250000"}}, rahbar)
check("Konstruktor: yozuv qo'shildi", s == 200, str(d))
s, d = call("POST", f"/api/sections/{SID}/records", {"data": {"f1": "X", "f2": "abc"}}, rahbar)
check("Konstruktor: noto'g'ri raqam rad etiladi", s == 400, str(d))
s, d = call("GET", f"/api/sections/{SID}/records", token=menejer)
check("Konstruktor: yozuvlar o'qiladi", s == 200 and d["records"][0]["data"]["f2"] == 250000.0, str(d)[:80])
st, ctype = raw(f"/api/sections/{SID}/export.xlsx", rahbar)
check("Konstruktor: Excel eksport", st == 200, str(st))
s, d = call("POST", "/api/sections", {"name": "H", "icon": "x", "fields": []}, menejer)
check("Konstruktor: faqat rahbar yaratadi (403)", s == 403, str(d))
s, d = call("DELETE", f"/api/sections/{SID}", token=rahbar)
check("Konstruktor: bo'lim o'chirildi", s == 200, str(d))

# ---------- Kassa qoidalari ----------
s, d = call("POST", "/api/hr/cash", {"kind": "Avans", "employee_id": None, "amount": 1000}, bux)
check("Kassa: xodimsiz pul berish rad (400)", s == 400, str(d))
s, d = call("POST", "/api/hr/cash", {"kind": "Xarajat", "employee_id": E, "amount": 1000}, bux)
check("Kassa: xodimga xarajat yozish rad (400)", s == 400, str(d))
s, d = call("POST", "/api/hr/cash", {"kind": "Xarajat", "employee_id": None,
                                     "amount": 75000, "note": "Test skotch"}, bux)
check("Kassa: sex xarajati yoziladi", s == 200, str(d))

print()

# ---------- Bekor qilishda xomashyo qaytishi ----------
# avvalgi testda qora ro'yxatga kiritilgan edi — chiqaramiz
call("PUT", f"/api/clients/{CID}", {
    "company": "TEST Qurilish MChJ", "contact": "Test Aka", "phone": "+998900000001",
    "inn": "123456789", "pay_type": "Naqd", "category": "Yangi",
    "credit_limit": 100_000_000, "blacklisted": False}, menejer)
s, o2 = call("POST", "/api/orders", {"length_mm": 300, "width_mm": 200, "height_mm": 150,
             "layers": 3, "grade": "K1", "colors": 0, "qty": 500, "client_id": CID}, menejer)
check("Bekor testi: buyurtma yaratildi", s == 200, str(o2)[:60])
s, raw_b = call("GET", "/api/warehouse/raw", token=sklad)
k2_before = [g for g in raw_b["groups"] if g["grade"] == "K1"][0]["stock_kg"]
call("POST", f"/api/orders/{o2['id']}/status?status=Sexda kesilmoqda", token=menejer)
s, d = call("POST", f"/api/orders/{o2['id']}/status?status=Bekor qilindi", token=menejer)
check("Sexdan bekor qilish mumkin", s == 200, str(d)[:60])
s, raw_a = call("GET", "/api/warehouse/raw", token=sklad)
k2_after = [g for g in raw_a["groups"] if g["grade"] == "K1"][0]["stock_kg"]
check("Bekor: xomashyo omborga qaytdi (kg)", abs(k2_after - k2_before) < 0.5,
      f"{k2_before} -> {k2_after}")

# ---------- Kiritish validatsiyalari ----------
s, d = call("POST", "/api/orders/quote", {"length_mm": 0, "width_mm": 300, "height_mm": 250,
             "layers": 3, "grade": "K1", "colors": 0, "qty": 100}, menejer)
check("Validatsiya: 0 mm o'lcham rad", s == 400, str(d))
s, d = call("POST", "/api/orders/quote", {"length_mm": 400, "width_mm": 300, "height_mm": 250,
             "layers": 4, "grade": "K1", "colors": 0, "qty": 100}, menejer)
check("Validatsiya: 4-qavat rad", s == 400, str(d))

# --- Buyurtma turlari: 1/2/3/5 слой + Самоклейка / Офсет / Картон Меловка ---
for _tur in ["1 слой", "2 слой", "3 слой", "5 слой", "Самоклейка", "Офсет", "Картон Меловка"]:
    s, d = call("POST", "/api/orders/quote", {"length_mm": 400, "width_mm": 300,
                "height_mm": 250, "tur": _tur, "grade": "K1", "colors": 1, "qty": 100}, menejer)
    check(f"Tur '{_tur}' bilan smeta", s == 200 and d.get("unit_price", 0) > 0, str(d)[:60])
s, d = call("POST", "/api/orders/quote", {"length_mm": 400, "width_mm": 300, "height_mm": 250,
             "tur": "7 слой", "grade": "K1", "colors": 0, "qty": 100}, menejer)
check("Validatsiya: noma'lum tur rad", s == 400, str(d)[:60])
# gofra bo'lmagan materiallar bir qatlamli bo'lib yoziladi + qo'shimcha izoh saqlanadi
s, o = call("POST", "/api/orders", {"length_mm": 300, "width_mm": 200, "height_mm": 150,
            "tur": "Самоклейка", "grade": "K1", "colors": 0, "qty": 100, "client_id": CID,
            "note": "Тагига картон қўйилсин"}, menejer)
check("Tur 'Самоклейка' buyurtma: qavat=1", s == 200 and o["tur"] == "Самоклейка"
      and o["layers"] == 1, str(o)[:70])
check("Qo'shimcha izoh saqlanadi", o.get("note") == "Тагига картон қўйилсин", str(o.get("note")))
s, o2 = call("POST", "/api/orders", {"length_mm": 300, "width_mm": 200, "height_mm": 150,
             "tur": "Офсет", "grade": "K1", "colors": 0, "qty": 100, "client_id": CID}, menejer)
check("Tur 'Офсет' is_offset belgisini qo'yadi", s == 200 and o2["is_offset"] is True, str(o2)[:60])
s, d = call("POST", "/api/finance/payments", {"client_id": CID, "amount": -5000}, bux)
check("Validatsiya: manfiy to'lov rad", s == 400, str(d))
s, d = call("POST", "/api/warehouse/raw", {"supplier_id": 1, "grade": "K1", "grammage": 120,
             "qty_kg": -10, "price_per_kg": 3000}, sklad)
check("Validatsiya: manfiy kirim rad", s == 400, str(d))
s, d = call("POST", "/api/warehouse/raw", {"supplier_id": 1, "grade": "", "grammage": 120,
             "qty_kg": 10, "price_per_kg": 3000}, sklad)
check("Validatsiya: bo'sh marka rad", s == 400, str(d))
s, d = call("POST", "/api/hr/work", {"employee_id": E, "qty": 0}, sex)
check("Validatsiya: 0 quti ish qaydi rad", s == 400, str(d))

# ---------- Rol cheklovi: buyurtma statusi ----------
s2, o3 = call("POST", "/api/orders", {"length_mm": 350, "width_mm": 250, "height_mm": 200,
             "layers": 3, "grade": "K1", "colors": 0, "qty": 300, "client_id": CID}, menejer)
call("POST", f"/api/orders/{o3['id']}/status?status=Sexda kesilmoqda", token=menejer)
call("POST", f"/api/orders/{o3['id']}/status?status=Omborga tushdi", token=sex)
s2, d3 = call("POST", f"/api/orders/{o3['id']}/status?status=Yetkazib berildi", token=sex)
check("Rol: sex yetkazib bera olmaydi (403)", s2 == 403, str(d3)[:70])
s2, d3 = call("POST", f"/api/orders/{o3['id']}/status?status=Yetkazib berildi", token=sklad)
check("Rol: sklad mudiri yetkazadi", s2 == 200, str(d3)[:70])

# ---------- POLIGRAFIYA: kataloglar + materiallar + zakup ----------
s, units = call("GET", "/api/catalog/units", token=rahbar)
check("Katalog: birliklar bor", s == 200 and len(units) >= 6, str(len(units)))
s, pos = call("GET", "/api/catalog/positions", token=rahbar)
check("Katalog: Kleychi/Kashirovkachi bor", any(p["name"] == "Kleychi" for p in pos) and any(p["name"] == "Kashirovkachi" for p in pos), str([p["name"] for p in pos]))
s, d = call("POST", "/api/catalog/categories", {"name": "Test bo'lim"}, rahbar)
check("Katalog: admin bo'lim qo'shadi", s == 200, str(d))
s, d = call("POST", "/api/catalog/categories", {"name": "Test bo'lim"}, rahbar)
check("Katalog: takroriy bo'lim rad", s == 409, str(d))
s, d = call("POST", "/api/catalog/categories", {"name": "X"}, menejer)
check("Katalog: menejer bo'lim qo'sha olmaydi", s == 403, str(d))

# material
s, mat = call("POST", "/api/catalog/materials", {"name": "Test qog'oz", "category": "Qog'oz",
              "grammaj": "140 гр", "unit": "kg", "min_stock": 100}, rahbar)
check("Material yaratildi", s == 200 and "140" in mat["display"], str(mat)[:60])
MATID = mat["id"]

# xizmat + formula
s, sv = call("GET", "/api/catalog/services", token=rahbar)
check("Xizmatlar: laminatsiya/noj/lak bor", any("Laminatsiya" in x["name"] for x in sv) and any("Noj" in x["name"] for x in sv), str(len(sv)))
s, fo = call("GET", "/api/catalog/formulas", token=rahbar)
fid = [x["id"] for x in fo if "Kley" in x["name"]][0]
kname = [x["name"] for x in fo if "Kley" in x["name"]][0]
s, d = call("PUT", f"/api/catalog/formulas/{fid}", {"name": kname, "expression": "x*y*0.15*n", "description": "test"}, rahbar)
check("Formula tahrirlandi", s == 200 and d["expression"] == "x*y*0.15*n", str(d)[:50])
s, d = call("PUT", f"/api/catalog/formulas/{fid}", {"name": kname, "expression": "__import__('os')", "description": ""}, rahbar)
check("Formula: xavfli kod rad", s == 400, str(d))

# zakup
s, sups2 = call("GET", "/api/warehouse/suppliers", token=rahbar)
SUP = sups2[0]["id"]
s, pur = call("POST", "/api/purchase", {"material_name": "Test qog'oz", "supplier_id": SUP,
              "qty": 500, "unit": "kg", "fmt": "85*59", "unit_price": 13000,
              "payment_type": "Qarz", "paid_amount": 0, "due_days": 30}, rahbar)
check("Zakup: qarzga xarid (material nomi bilan)", s == 200 and pur["debt"] == 6500000.0, str(pur)[:60])
PURID = pur["id"]
# qoldiq oshdimi
s, mats = call("GET", "/api/catalog/materials?category=Qog'oz", token=rahbar)
my = [x for x in mats if x["id"] == MATID][0]
check("Zakup: material qoldig'i oshdi (500)", my["stock_qty"] == 500.0, str(my["stock_qty"]))
# qarzga to'lov
s, d = call("POST", "/api/purchase/pay", {"purchase_id": PURID, "amount": 6500000, "method": "O'tkazma"}, rahbar)
check("Zakup: qarz to'landi", s == 200 and d["debt"] == 0.0, str(d)[:50])
# naqd xaridda qarz 0
s, pur2 = call("POST", "/api/purchase", {"material_name": "Test qog'oz", "supplier_id": SUP,
               "qty": 100, "unit_price": 13000, "payment_type": "Naqd"}, rahbar)
check("Zakup: naqd xarid qarzi 0", s == 200 and pur2["debt"] == 0.0, str(pur2["debt"]))
# validatsiya
s, d = call("POST", "/api/purchase", {"material_name": "Test qog'oz", "supplier_id": SUP,
            "qty": -5, "unit_price": 13000, "payment_type": "Naqd"}, rahbar)
check("Zakup: manfiy miqdor rad", s == 400, str(d))
# yangi material nomi yozilsa — o'zi yaratiladi (ruchnoy kiritish)
s, pur3 = call("POST", "/api/purchase", {"material_name": "Butunlay yangi material ZZ",
               "supplier_id": SUP, "qty": 7, "unit_price": 1000, "payment_type": "Naqd"}, rahbar)
check("Zakup: yangi material nomi o'zi saqlanadi",
      s == 200 and pur3["material"] == "Butunlay yangi material ZZ", str(pur3)[:70])
# xatolik ketsa — xaridni tuzatish
s, ed = call("PUT", f"/api/purchase/{pur3['id']}", {"qty": 3, "unit_price": 2000}, rahbar)
check("Zakup: xarid tuzatildi", s == 200 and ed["qty"] == 3.0 and ed["total"] == 6000.0, str(ed)[:70])
s, dele = call("DELETE", f"/api/purchase/{pur3['id']}", None, rahbar)
check("Zakup: xato xarid o'chirildi", s == 200, str(dele)[:50])

# ---------- Kassa jurnali (kirim-chiqim) ----------
# Kassaga mijoz to'lovi, avans va xarid ham avtomat tushadi, shuning uchun
# jurnalda faqat shu blok yozgan summalar bo'lmaydi — farq o'lchanadi.
_, j0 = call("GET", "/api/kassa?firm=Sinov sex", token=rahbar)
s, d = call("POST", "/api/kassa", {"direction": "Kirim", "who": "Test mijoz",
            "amount": 500000, "firm": "Sinov sex"}, rahbar)
check("Kassa jurnal: kirim yozildi", s == 200 and d["direction"] == "Kirim", str(d)[:60])
s, d = call("POST", "/api/kassa", {"direction": "Chiqim", "who": "Remont",
            "note": "stanok", "amount": 300000, "firm": "Sinov sex"}, rahbar)
check("Kassa jurnal: chiqim yozildi", s == 200, str(d)[:60])
KEID = d["id"]
s, d = call("POST", "/api/kassa", {"direction": "Kirim", "who": "Valyuta",
            "amount": 100, "currency": "USD", "firm": "Sinov sex"}, rahbar)
check("Kassa jurnal: USD yozuv", s == 200 and d["currency"] == "USD", str(d)[:60])
s, j = call("GET", "/api/kassa?firm=Sinov sex", token=rahbar)
check("Kassa jurnal: balans to'g'ri (500k-300k=200k)",
      j["kirim"] - j0["kirim"] == 500000.0
      and j["chiqim"] - j0["chiqim"] == 300000.0
      and j["balans"] - j0["balans"] == 200000.0
      and j["usd_kirim"] - j0["usd_kirim"] == 100.0,
      str((j["kirim"] - j0["kirim"], j["chiqim"] - j0["chiqim"],
           j["usd_kirim"] - j0["usd_kirim"])))
s, d = call("POST", "/api/kassa", {"direction": "Noto'g'ri", "who": "X", "amount": 1}, rahbar)
check("Kassa jurnal: noto'g'ri yo'nalish rad", s == 400, str(d))
s, d = call("POST", "/api/kassa", {"direction": "Kirim", "who": "", "amount": 1}, rahbar)
check("Kassa jurnal: bo'sh nom rad", s == 400, str(d))
s, d = call("POST", "/api/kassa", {"direction": "Kirim", "who": "X", "amount": 1}, menejer)
check("Kassa jurnal: menejer yoza olmaydi (403)", s == 403, str(d))
s, d = call("DELETE", f"/api/kassa/{KEID}", token=rahbar)
check("Kassa jurnal: rahbar o'chiradi", s == 200, str(d))

# ---------- Kassa: pul harakati manbaga bog'lanishi ----------
_, kb = call("GET", "/api/kassa", token=rahbar)
s, tolov = call("POST", "/api/finance/payments",
                {"client_id": CID, "amount": 777000, "method": "Naqd",
                 "note": "Kassa bog'lash sinovi"}, bux)
check("Kassa bog'lash: to'lov yozildi", s == 200 and tolov.get("id"), str(tolov)[:70])
_, ka = call("GET", "/api/kassa", token=rahbar)
check("Kassa bog'lash: mijoz to'lovi kassaga tushdi",
      ka["kirim"] - kb["kirim"] == 777000.0, str(ka["kirim"] - kb["kirim"]))
yozuv = next((e for e in ka["entries"]
              if e["note"] and "Kassa bog'lash sinovi" in e["note"]), None)
check("Kassa bog'lash: yozuv izohi bilan topildi", yozuv is not None, str(ka["entries"][:1]))
if yozuv:
    s, d = call("DELETE", f"/api/kassa/{yozuv['id']}", token=rahbar)
    check("Kassa bog'lash: bog'langan yozuvni kassadan o'chirish taqiqlangan",
          s == 400, f"status={s} {str(d)[:60]}")
s, spisok = call("GET", f"/api/finance/payments?client_id={CID}", token=rahbar)
check("Kassa bog'lash: to'lovlar ro'yxati ishlaydi",
      s == 200 and any(p["id"] == tolov["id"] for p in spisok), str(spisok)[:70])
s, d = call("DELETE", f"/api/finance/payments/{tolov['id']}", token=rahbar)
check("Kassa bog'lash: to'lov Moliyadan o'chirildi", s == 200, str(d)[:60])
_, kc = call("GET", "/api/kassa", token=rahbar)
check("Kassa bog'lash: to'lov o'chirilgach kassadan ham ketdi",
      kc["kirim"] == kb["kirim"], str((kb["kirim"], kc["kirim"])))
s, d = call("DELETE", f"/api/finance/payments/{tolov['id']}", token=menejer)
check("Kassa bog'lash: menejer to'lov o'chira olmaydi", s in (403, 404), f"status={s}")

# ---------- Tannarx: qog'oz narxi topilmasa ochiq ogohlantirish ----------
s, q_yoq = call("POST", "/api/orders/quote",
                {"length_mm": 400, "width_mm": 300, "height_mm": 250, "tur": "3 слой",
                 "grade": "Butunlay noma'lum qog'oz ZZZ", "colors": 2, "qty": 100}, menejer)
check("Tannarx: noma'lum qog'ozda ogohlantirish beriladi",
      s == 200 and q_yoq["material_price_m2"] == 0 and q_yoq.get("narx_ogoh"),
      str(q_yoq)[:80])
# 150 гр qog'oz 10 000 so'm/kg dan olindi -> 1 m² = 10000*150/1000 = 1500 so'm
call("POST", "/api/purchase", {"material_name": "Sinov qogoz 150гр", "supplier_id": SUP,
     "qty": 100, "unit": "kg", "unit_price": 10000, "payment_type": "Naqd"}, rahbar)
s, q_bor = call("POST", "/api/orders/quote",
                {"length_mm": 400, "width_mm": 300, "height_mm": 250, "tur": "3 слой",
                 "grade": "Sinov qogoz 150гр", "colors": 2, "qty": 100}, menejer)
check("Tannarx: xarid qilingan qog'ozda narx topiladi",
      s == 200 and q_bor["material_price_m2"] == 1500.0 and not q_bor.get("narx_ogoh")
      and q_bor["narx_manba"], str(q_bor)[:130])
s, q_kir = call("POST", "/api/orders/quote",
                {"length_mm": 400, "width_mm": 300, "height_mm": 250, "tur": "3 слой",
                 "grade": "Синов қоғоз 150 гр", "colors": 2, "qty": 100}, menejer)
check("Tannarx: kirillcha yozilgan bir xil qog'oz ham topiladi",
      s == 200 and q_kir["material_price_m2"] == 1500.0, str(q_kir)[:110])
check("Tannarx: qog'oz narxi tannarxga kirdi",
      q_bor["unit_cost"] > q_yoq["unit_cost"],
      str((q_yoq["unit_cost"], q_bor["unit_cost"])))

if FAILS:
    print(f"❌ {len(FAILS)} ta muammo:")
    for x in FAILS:
        print("  -", x)
else:
    print("✅ HAMMA TESTLAR O'TDI")
