"""ESKI TIZIMDAN KO'CHIRISH — SQLite → platforma bazasi.

Nima uchun kerak: mijozning yillar davomida yig'ilgan ma'lumoti bor va
platformaga o'tishda u yo'qolmasligi kerak. Bu vosita eski TIZIM ERP
bazasidan (SQLite) mijozlar, ombor, buyurtma, to'lov va kassani o'qib,
platformaga yozadi.

╔══════════════════════════════════════════════════════════════════╗
║  MANBA FAQAT O'QILADI. Vosita manba faylni `mode=ro` (read-only) ║
║  URI bilan ochadi — SQLite darajasida yozish IMKONSIZ. Jonli     ║
║  bazaga emas, ZAXIRA nusxasiga qarating.                          ║
╚══════════════════════════════════════════════════════════════════╝

Asosiy o'girish: eski `orders` jadvalidagi karton ustunlari
(length_mm, grade, layers...) platformada ALOHIDA USTUN EMAS — ular
`attributes` JSON iga tushadi. Shuning uchun ko'chirishda faol profil
`karton` bo'lishi shart, aks holda maydonlar tanilmaydi.

Ishlatish:
    .venv/bin/python tools/kochir.py <eski.db> [--tekshir] [--kirish]

    --tekshir  — hech narsa yozmaydi, faqat nima ko'chishini ko'rsatadi
    --kirish   — foydalanuvchi va OCHIQ SESSIYALARNI ham ko'chiradi

`--kirish` YAKUNIY O'TISH (cutover) uchun: eski parollar va ochiq
sessiyalar saqlanadi, ya'ni mijoz uchun bu «tizim yangilandi», «yangi
tizimga ko'chdik» emas. Parallel NUSXA yasayotganda bermang — bitta
sessiya ikki bazada yashab qolsa qaysi nusxaga yozilgani chalkashadi.

RASM FAYLLARI alohida ko'chiriladi: yozuv bu vositada, fayllar esa
`uploads/<baza_nomi>/` ga (nusxalanmasa havolalar singan rasmga olib
boradi).
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal                    # noqa: E402
from app import models as m, domain                # noqa: E402

# Eski `orders` ustuni -> soha maydoni kaliti. Ikkalasi bir xil nomda,
# lekin ro'yxat ATAYLAB aniq yozilgan: eski bazada ortiqcha ustun paydo
# bo'lsa u jimgina `attributes` ga tushib ketmasin.
KARTON_MAYDONLARI = ("length_mm", "width_mm", "height_mm", "layers",
                     "grade", "colors", "is_offset", "tur", "m2_per_box")


def ochish_ro(yol: str) -> sqlite3.Connection:
    """Manbani FAQAT O'QISH uchun ochadi.

    `mode=ro` — SQLite ning o'zi yozishni rad etadi. Xatolik yoki
    e'tiborsizlik tufayli mijozning bazasiga bir harf ham yozilmasin.
    """
    fayl = Path(yol).resolve()
    if not fayl.exists():
        sys.exit(f"❌ Fayl topilmadi: {fayl}")
    conn = sqlite3.connect(f"file:{fayl}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _q(satr, kalit, standart=None):
    """Ustun bo'lmasa yiqilmaydi — eski bazalar turlicha bo'ladi."""
    try:
        qiymat = satr[kalit]
    except (IndexError, KeyError):
        return standart
    return standart if qiymat is None else qiymat


def _d(qiymat, standart="0") -> Decimal:
    try:
        return Decimal(str(qiymat if qiymat is not None else standart))
    except Exception:                                     # noqa: BLE001
        return Decimal(standart)


def _sana(qiymat):
    if not qiymat:
        return None
    matn = str(qiymat)
    for shakl in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(matn[:26], shakl)
        except ValueError:
            continue
    return None


def jadval_bormi(conn, nom: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (nom,)).fetchone())


def kochir(manba: str, tekshir_faqat: bool = False,
           kirish: bool = False) -> dict:
    conn = ochish_ro(manba)
    db = SessionLocal()
    hisob = {}

    try:
        if domain.profil().kalit != "karton":
            print("⚠️  Faol profil «karton» emas — buyurtma maydonlari "
                  "tanilmasligi mumkin. Avval karton profilini faollashtiring.")

        # ---- 1. Mijozlar --------------------------------------------
        # `eski_id -> yangi obyekt` xaritasi: buyurtma va to'lovlar eski
        # id ga bog'langan, yangi bazada id boshqacha bo'ladi.
        mijoz_xarita = {}
        if jadval_bormi(conn, "clients"):
            for r in conn.execute("SELECT * FROM clients"):
                c = m.Client(
                    company=_q(r, "company", "Nomsiz"),
                    contact=_q(r, "contact", ""), phone=_q(r, "phone", ""),
                    inn=_q(r, "inn", ""), pay_type=_q(r, "pay_type", "Naqd"),
                    category=_q(r, "category", "Standart"),
                    credit_limit=_d(_q(r, "credit_limit")),
                    blacklisted=bool(_q(r, "blacklisted", 0)),
                    opening_balance=_d(_q(r, "opening_balance")),
                )
                db.add(c)
                mijoz_xarita[r["id"]] = c
            db.flush()
        hisob["mijozlar"] = len(mijoz_xarita)

        # ---- 2. Yetkazib beruvchilar ---------------------------------
        yb_xarita = {}
        if jadval_bormi(conn, "suppliers"):
            for r in conn.execute("SELECT * FROM suppliers"):
                sp = m.Supplier(name=_q(r, "name", "Nomsiz"),
                                phone=_q(r, "phone", ""),
                                kind=_q(r, "kind", "xomashyo"))
                db.add(sp)
                yb_xarita[r["id"]] = sp
            db.flush()
        hisob["yetkazib_beruvchilar"] = len(yb_xarita)

        # ---- 3. Materiallar ------------------------------------------
        mat_xarita = {}
        if jadval_bormi(conn, "materials"):
            for r in conn.execute("SELECT * FROM materials"):
                mt = m.Material(
                    name=_q(r, "name", "Nomsiz"),
                    category=_q(r, "category", ""), marka=_q(r, "marka", ""),
                    manufacturer=_q(r, "manufacturer", ""),
                    grammaj=_q(r, "grammaj", ""), unit=_q(r, "unit", "kg"),
                    last_price=_d(_q(r, "last_price")),
                    stock_qty=_d(_q(r, "stock_qty")),
                    min_stock=_d(_q(r, "min_stock")),
                    active=bool(_q(r, "active", 1)),
                )
                db.add(mt)
                mat_xarita[r["id"]] = mt
            db.flush()
        hisob["materiallar"] = len(mat_xarita)

        # ---- 4. Qog'oz partiyalari (karton yo'li) --------------------
        lot_xarita = {}
        if jadval_bormi(conn, "raw_lots"):
            for r in conn.execute("SELECT * FROM raw_lots"):
                yb = yb_xarita.get(_q(r, "supplier_id"))
                lot = m.RawLot(
                    lot_no=_q(r, "lot_no", ""),
                    supplier_id=yb.id if yb else None,
                    grade=_q(r, "grade", ""), grammage=int(_q(r, "grammage", 0) or 0),
                    qty_kg=_d(_q(r, "qty_kg")),
                    remaining_kg=_d(_q(r, "remaining_kg")),
                    price_per_kg=_d(_q(r, "price_per_kg")),
                    received_at=(_sana(_q(r, "received_at")) or datetime.utcnow()).date(),
                )
                db.add(lot)
                lot_xarita[r["id"]] = lot
            db.flush()
        hisob["qogoz_partiyalari"] = len(lot_xarita)

        # ---- 5. Buyurtmalar ------------------------------------------
        # ENG MUHIM QADAM: karton ustunlari `attributes` ga o'tadi.
        buyurtma_xarita = {}
        if jadval_bormi(conn, "orders"):
            for r in conn.execute("SELECT * FROM orders"):
                c = mijoz_xarita.get(_q(r, "client_id"))
                if c is None:
                    continue          # mijozsiz buyurtma — tashlab ketiladi
                atr = {}
                for kalit in KARTON_MAYDONLARI:
                    qiymat = _q(r, kalit)
                    if qiymat is None:
                        continue
                    # Decimal JSON da SATR bo'lib saqlanadi — float aniqlikni
                    # yo'qotadi va tannarx tiyinlarda chalkashadi.
                    atr[kalit] = (str(qiymat) if kalit == "m2_per_box"
                                  else (bool(qiymat) if kalit == "is_offset"
                                        else qiymat))
                yaratilgan = _sana(_q(r, "created_at")) or datetime.utcnow()
                o = m.Order(
                    client_id=c.id, attributes=atr,
                    product_name=_q(r, "product_name", ""),
                    qty=_d(_q(r, "qty"), "1"),
                    delivered_qty=_d(_q(r, "delivered_qty")),
                    unit_cost=_d(_q(r, "unit_cost")),
                    unit_price=_d(_q(r, "unit_price")),
                    total=_d(_q(r, "total")),
                    prepaid_percent=int(_q(r, "prepaid_percent", 0) or 0),
                    status=_q(r, "status", "Kutishda"),
                    note=_q(r, "note", ""), photo=_q(r, "photo", ""),
                    created_at=yaratilgan,
                    due_date=(_sana(_q(r, "due_date")) or yaratilgan).date(),
                    payment_due_date=(_sana(_q(r, "payment_due_date")) or yaratilgan).date(),
                    delivered_at=(_sana(_q(r, "delivered_at")).date()
                                  if _sana(_q(r, "delivered_at")) else None),
                    accepted_stamp=bool(_q(r, "accepted_stamp", 0)),
                )
                db.add(o)
                buyurtma_xarita[r["id"]] = o
            db.flush()
        hisob["buyurtmalar"] = len(buyurtma_xarita)

        # ---- 6. To'lovlar --------------------------------------------
        tolov_soni = 0
        if jadval_bormi(conn, "payments"):
            for r in conn.execute("SELECT * FROM payments"):
                c = mijoz_xarita.get(_q(r, "client_id"))
                if c is None:
                    continue
                o = buyurtma_xarita.get(_q(r, "order_id"))
                db.add(m.Payment(
                    client_id=c.id, order_id=o.id if o else None,
                    amount=_d(_q(r, "amount")), method=_q(r, "method", "Naqd"),
                    paid_at=(_sana(_q(r, "paid_at")) or datetime.utcnow()).date(),
                    note=_q(r, "note", ""),
                ))
                tolov_soni += 1
        hisob["tolovlar"] = tolov_soni

        # ---- 7. Kassa jurnali ----------------------------------------
        # Bog'lanishlar (linked_*) ATAYLAB ko'chirilmaydi: ular eski
        # id larga ishora qiladi va yangi bazada boshqa yozuvga tushib
        # ketishi mumkin edi. Pul summasi va izohi saqlanadi.
        kassa_soni = 0
        if jadval_bormi(conn, "kassa_entries"):
            for r in conn.execute("SELECT * FROM kassa_entries"):
                db.add(m.KassaEntry(
                    direction=_q(r, "direction", "Kirim"),
                    who=_q(r, "who", ""), note=_q(r, "note", ""),
                    amount=_d(_q(r, "amount")),
                    firm=_q(r, "firm", "Asosiy"),
                    currency=_q(r, "currency", "so'm"),
                    entry_at=(_sana(_q(r, "entry_at")) or datetime.utcnow()).date(),
                    created_by=_q(r, "created_by", "ko'chirildi"),
                ))
                kassa_soni += 1
        hisob["kassa_yozuvlari"] = kassa_soni

        # ---- 8. Xodimlar ---------------------------------------------
        emp_xarita = {}
        if jadval_bormi(conn, "employees"):
            for r in conn.execute("SELECT * FROM employees"):
                emp = m.Employee(
                    name=_q(r, "name", "Nomsiz"),
                    position=_q(r, "position", "Stanokchi"),
                    phone=_q(r, "phone", ""),
                    rate_per_box=_d(_q(r, "rate_per_box"), "150"),
                    brigade=_q(r, "brigade", ""), firm=_q(r, "firm", ""),
                    active=bool(_q(r, "active", 1)),
                )
                db.add(emp)
                emp_xarita[r["id"]] = emp
            db.flush()
        hisob["xodimlar"] = len(emp_xarita)

        # ---- 9. Xaridlar (yetkazib beruvchidan) ---------------------
        xarid_xarita = {}
        if jadval_bormi(conn, "purchases"):
            for r in conn.execute("SELECT * FROM purchases"):
                mt = mat_xarita.get(_q(r, "material_id"))
                yb = yb_xarita.get(_q(r, "supplier_id"))
                if mt is None or yb is None:
                    continue
                pdate = (_sana(_q(r, "purchased_at")) or datetime.utcnow()).date()
                pu = m.Purchase(
                    material_id=mt.id, supplier_id=yb.id,
                    qty=_d(_q(r, "qty"), "1"), unit=_q(r, "unit", "kg"),
                    fmt=_q(r, "fmt", ""), unit_price=_d(_q(r, "unit_price")),
                    total=_d(_q(r, "total")),
                    payment_type=_q(r, "payment_type", "Naqd"),
                    paid_amount=_d(_q(r, "paid_amount")),
                    due_date=_sana(_q(r, "due_date")).date() if _sana(_q(r, "due_date")) else None,
                    purchased_at=pdate, note=_q(r, "note", ""),
                    firm=_q(r, "firm", ""),
                )
                db.add(pu)
                xarid_xarita[r["id"]] = pu
            db.flush()
        hisob["xaridlar"] = len(xarid_xarita)

        # ---- 10. Xarid to'lovlari ----------------------------------
        n = 0
        if jadval_bormi(conn, "purchase_payments"):
            for r in conn.execute("SELECT * FROM purchase_payments"):
                pu = xarid_xarita.get(_q(r, "purchase_id"))
                if pu is None:
                    continue
                db.add(m.PurchasePayment(
                    purchase_id=pu.id, amount=_d(_q(r, "amount")),
                    method=_q(r, "method", "Naqd"),
                    paid_at=(_sana(_q(r, "paid_at")) or datetime.utcnow()).date(),
                    note=_q(r, "note", ""),
                ))
                n += 1
        hisob["xarid_tolovlari"] = n

        # ---- 11. Kassa harakatlari (sex xarajat / xodim avansi) -----
        n = 0
        if jadval_bormi(conn, "cash_entries"):
            for r in conn.execute("SELECT * FROM cash_entries"):
                emp = emp_xarita.get(_q(r, "employee_id"))
                db.add(m.CashEntry(
                    employee_id=emp.id if emp else None,
                    kind=_q(r, "kind", "Xarajat"), amount=_d(_q(r, "amount")),
                    note=_q(r, "note", ""), firm=_q(r, "firm", ""),
                    entry_at=(_sana(_q(r, "entry_at")) or datetime.utcnow()).date(),
                ))
                n += 1
        hisob["kassa_harakatlari"] = n

        # ---- 12. Sdelshina (ish yozuvlari) -------------------------
        n = 0
        if jadval_bormi(conn, "work_entries"):
            for r in conn.execute("SELECT * FROM work_entries"):
                emp = emp_xarita.get(_q(r, "employee_id"))
                o = buyurtma_xarita.get(_q(r, "order_id"))
                if emp is None:
                    continue
                db.add(m.WorkEntry(
                    employee_id=emp.id, order_id=o.id if o else None,
                    qty=_d(_q(r, "qty")), qc_passed=bool(_q(r, "qc_passed", 1)),
                    rate=_d(_q(r, "rate")), amount=_d(_q(r, "amount")),
                    worked_at=(_sana(_q(r, "worked_at")) or datetime.utcnow()).date(),
                ))
                n += 1
        hisob["sdelshina"] = n

        # ---- 13. Ombor harakatlari (stock + material moves) --------
        n = 0
        if jadval_bormi(conn, "stock_moves"):
            for r in conn.execute("SELECT * FROM stock_moves"):
                lot = lot_xarita.get(_q(r, "lot_id"))
                o = buyurtma_xarita.get(_q(r, "order_id"))
                if lot is None:
                    continue
                db.add(m.StockMove(
                    lot_id=lot.id, order_id=o.id if o else None,
                    kg=_d(_q(r, "kg")), cost=_d(_q(r, "cost")),
                    moved_at=_sana(_q(r, "moved_at")) or datetime.utcnow(),
                    note=_q(r, "note", ""),
                ))
                n += 1
        hisob["ombor_harakati"] = n
        n2 = 0
        if jadval_bormi(conn, "material_moves"):
            for r in conn.execute("SELECT * FROM material_moves"):
                mt = mat_xarita.get(_q(r, "material_id"))
                o = buyurtma_xarita.get(_q(r, "order_id"))
                if mt is None:
                    continue
                db.add(m.MaterialMove(
                    material_id=mt.id, qty=_d(_q(r, "qty")),
                    reason=_q(r, "reason", ""), order_id=o.id if o else None,
                    at=_sana(_q(r, "at")) or datetime.utcnow(),
                ))
                n2 += 1
        hisob["material_harakati"] = n2

        # ---- 14. To'lov grafigi (yetkazib beruvchiga) --------------
        n = 0
        if jadval_bormi(conn, "payment_schedules"):
            for r in conn.execute("SELECT * FROM payment_schedules"):
                yb = yb_xarita.get(_q(r, "supplier_id"))
                if yb is None:
                    continue
                db.add(m.PaymentSchedule(
                    supplier_id=yb.id,
                    due_date=(_sana(_q(r, "due_date")) or datetime.utcnow()).date(),
                    amount=_d(_q(r, "amount")), paid=bool(_q(r, "paid", 0)),
                ))
                n += 1
        hisob["tolov_grafigi"] = n

        # ---- 15. Sozlamalar (rekvizit, brak %) — UPSERT ------------
        # NEGA: hujjat rekvizitlari va brak foizi hisob-kitobga ta'sir
        # qiladi. Ular ko'chmasa akt/nakladnoy bo'sh rekvizit bilan
        # chiqadi va tannarx brak foizisiz noto'g'ri bo'ladi.
        n = 0
        if jadval_bormi(conn, "settings"):
            for r in conn.execute("SELECT * FROM settings"):
                k = _q(r, "key")
                if not k:
                    continue
                db.merge(m.Setting(key=k, value=_q(r, "value", "")))
                n += 1
        hisob["sozlamalar"] = n

        # ---- 16. KATALOGLAR — birlik, lavozim, bo'lim -----------------
        # Nomi bo'yicha UPSERT: akkaunt tayyorlanganda `seed_catalogs`
        # standart ro'yxatni yozib qo'ygan bo'lishi mumkin, mijozniki
        # esa boshqacha. Takror nom `unique` cheklovini buzardi.
        for jadval, model, hisob_nomi in (("units", m.Unit, "birliklar"),
                                          ("positions", m.Position, "lavozimlar"),
                                          ("categories", m.Category, "bolimlar")):
            n = 0
            if jadval_bormi(conn, jadval):
                for r in conn.execute(f"SELECT * FROM {jadval}"):
                    nom = (_q(r, "name") or "").strip()
                    if not nom:
                        continue
                    bor = db.query(model).filter(model.name == nom).first()
                    if bor is None:
                        db.add(model(name=nom))
                    n += 1
            hisob[hisob_nomi] = n
        db.flush()

        # ---- 17. XIZMATLAR va FORMULALAR -----------------------------
        # Formula tannarxga to'g'ridan-to'g'ri ta'sir qiladi (qavat,
        # kley sarfi). Ko'chmasa hisob-kitob mijozdagidan farq qiladi.
        # NOMI BO'YICHA UPSERT, `merge` EMAS. `db.merge()` birlamchi
        # kalit (`id`) bo'yicha ishlaydi — `formulas.name` esa unique.
        # Seed allaqachon shu nomdagi formulani yozgan bo'lsa, merge
        # yangi qator qo'shmoqchi bo'lib `UNIQUE constraint failed`
        # beradi va BUTUN ko'chirish yiqiladi. (Mashqda ushlandi.)
        n = 0
        if jadval_bormi(conn, "services"):
            for r in conn.execute("SELECT * FROM services"):
                nom = (_q(r, "name") or "").strip()
                if not nom:
                    continue
                bor = db.query(m.Service).filter(m.Service.name == nom).first()
                if bor is None:
                    bor = m.Service(name=nom[:80])
                    db.add(bor)
                bor.price = _d(_q(r, "price"))
                bor.unit = _q(r, "unit", "m²")[:20]
                bor.formula = _q(r, "formula", "x*y*n")[:120]
                bor.active = bool(_q(r, "active", 1))
                n += 1
        hisob["xizmatlar"] = n

        n = 0
        if jadval_bormi(conn, "formulas"):
            for r in conn.execute("SELECT * FROM formulas"):
                nom = (_q(r, "name") or "").strip()
                if not nom:
                    continue
                bor = db.query(m.Formula).filter(m.Formula.name == nom).first()
                if bor is None:
                    bor = m.Formula(name=nom[:60])
                    db.add(bor)
                bor.expression = _q(r, "expression", "")[:200]
                bor.description = _q(r, "description", "")[:200]
                bor.active = bool(_q(r, "active", 1))
                n += 1
        hisob["formulalar"] = n
        db.flush()

        # ---- 18. BUYURTMA RASMLARI -----------------------------------
        # Yozuv ko'chiriladi, FAYLLAR esa alohida ko'chiriladi
        # (`uploads/<baza_nomi>/`). Fayl ko'chirilmasa havola singan
        # rasmga olib boradi — shuning uchun ikkisi BIR paytda
        # qilinishi kerak (yo'riqnoma: docs/ish-jarayoni).
        n = 0
        if jadval_bormi(conn, "order_photos"):
            for r in conn.execute("SELECT * FROM order_photos"):
                o = buyurtma_xarita.get(_q(r, "order_id"))
                fayl = (_q(r, "filename") or "").strip()
                if o is None or not fayl:
                    continue
                db.add(m.OrderPhoto(
                    order_id=o.id, filename=fayl[:200],
                    created_at=_sana(_q(r, "created_at")) or datetime.utcnow()))
                n += 1
        hisob["buyurtma_rasmlari"] = n

        # ---- 19. AUDIT JURNALI ---------------------------------------
        # «Kim nima qildi» tarixi. Bu ham mijozning ma'lumoti: kim
        # narxni o'zgartirgani, kim to'lovni o'chirgani shu yerda.
        n = 0
        if jadval_bormi(conn, "audit_logs"):
            for r in conn.execute("SELECT * FROM audit_logs ORDER BY id"):
                db.add(m.AuditLog(
                    who=(_q(r, "who") or "")[:100],
                    action=(_q(r, "action") or "")[:200],
                    detail=_q(r, "detail", "") or "",
                    at=_sana(_q(r, "at")) or datetime.utcnow()))
                n += 1
        hisob["audit_yozuvlari"] = n

        # ---- 20. KIRISH: foydalanuvchilar va ochiq sessiyalar --------
        # BU MA'LUMOT EMAS, KIRISH HUQUQI — shuning uchun alohida
        # bayroq (`--kirish`) bilan boshqariladi.
        #
        # YAKUNIY O'TISHDA SHART. Aks holda mijozning xodimlari eski
        # paroli bilan kira olmaydi va bu ular uchun «yangilanish»
        # emas, «yangi tizim» bo'ladi — aynan biz qochayotgan narsa.
        #
        # PARALLEL NUSXAGA BERILMAYDI: bitta sessiya ikki bazada
        # yashab qolsa, odam qaysi nusxaga yozayotganini bilmaydi.
        #
        # Parol OCHIQ ko'rinishda hech qayerda yo'q: bcrypt xeshi
        # o'zgartirilmasdan ko'chiriladi.
        n_user, n_yangi = 0, 0
        user_xarita = {}
        if kirish and jadval_bormi(conn, "users"):
            for r in conn.execute("SELECT * FROM users"):
                login = (_q(r, "login") or "").strip()
                xesh = _q(r, "password_hash") or ""
                if not login or not xesh:
                    continue
                bor = db.query(m.User).filter(m.User.login == login).first()
                if bor is None:
                    bor = m.User(login=login[:50], password_hash=xesh,
                                 name=(_q(r, "name") or login)[:100],
                                 role=(_q(r, "role") or "Menejer")[:30])
                    db.add(bor)
                    n_yangi += 1
                else:
                    # Akkaunt tayyorlanganda yasalgan vaqtinchalik
                    # foydalanuvchi ustiga mijozning HAQIQIY paroli
                    # yoziladi — u o'z parolini o'zgarmagan deb biladi.
                    bor.password_hash = xesh
                    bor.name = (_q(r, "name") or bor.name)[:100]
                    bor.role = (_q(r, "role") or bor.role)[:30]
                # Eski tizimda majburiy parol almashtirish yo'q edi.
                # Bayroq yoqiq qolsa odam kirgan zahoti «parolni
                # almashtiring» oynasiga tushardi.
                bor.parol_almashtirilsin = False
                db.flush()
                user_xarita[r["id"]] = bor
                n_user += 1
        hisob["foydalanuvchilar"] = n_user
        if kirish:
            hisob["yangi_foydalanuvchi"] = n_yangi

        # Brauzerdagi va Telegram ilovasidagi token BAZADA yashaydi.
        # Ko'chirilsa odam qayta kirmaydi: ekran ochiladi va ishlaydi.
        # Muddati o'tganlari olinmaydi — baza behuda shishmasin.
        n = 0
        if kirish and jadval_bormi(conn, "auth_tokens"):
            hozir = datetime.utcnow()
            for r in conn.execute("SELECT * FROM auth_tokens"):
                token = (_q(r, "token") or "").strip()
                u = user_xarita.get(_q(r, "user_id"))
                muddat = _sana(_q(r, "expires"))
                if not token or u is None or muddat is None or muddat < hozir:
                    continue
                if db.get(m.AuthToken, token) is not None:
                    continue
                db.add(m.AuthToken(token=token, user_id=u.id, expires=muddat))
                n += 1
        hisob["ochiq_sessiyalar"] = n

        if tekshir_faqat:
            db.rollback()
            print("🔍 TEKSHIRUV REJIMI — hech narsa yozilmadi")
        else:
            db.add(m.AuditLog(
                who="Ko'chirish vositasi", action="Eski tizimdan ko'chirildi",
                detail=", ".join(f"{k}: {v}" for k, v in hisob.items())))
            db.commit()
    finally:
        db.close()
        conn.close()

    return hisob


def main():
    p = argparse.ArgumentParser(description="Eski TIZIM bazasidan ko'chirish")
    p.add_argument("manba", help="Eski SQLite fayl (ZAXIRA nusxasi!)")
    p.add_argument("--tekshir", action="store_true",
                   help="Hech narsa yozmaydi, faqat sanaydi")
    p.add_argument("--kirish", action="store_true",
                   help="Foydalanuvchi va ochiq sessiyalarni ham ko'chiradi "
                        "(YAKUNIY o'tish uchun; parallel nusxaga bermang)")
    a = p.parse_args()

    print(f"Manba (faqat o'qish): {a.manba}")
    if a.kirish:
        print("🔑 Kirish ham ko'chiriladi — parol xeshi va ochiq sessiyalar")
    hisob = kochir(a.manba, a.tekshir, a.kirish)
    print()
    for kalit, son in hisob.items():
        print(f"  {kalit:<24} {son}")
    print(f"\n{'🔍 Tekshirildi' if a.tekshir else '✅ Ko`chirildi'}")


if __name__ == "__main__":
    main()
