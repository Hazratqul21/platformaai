"""Birinchi ishga tushirish: admin foydalanuvchi yaratiladi.

Demo ma'lumotlar (mijozlar, partiyalar, buyurtmalar) faqat SEED_DEMO=1
muhit o'zgaruvchisi bilan yuklanadi:  SEED_DEMO=1 ./run.sh
Oddiy (prod) rejimda tizim bo'sh boshlanadi.
"""
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from . import models as m
from . import services as s
from .auth import hash_pw
from . import domain
from .domain import soha_yoz, soha_oqi


def seed_catalogs(db: Session):
    """Standart kataloglar — birlik, lavozim, bo'lim, xizmat, formula.
    Prod rejimda ham yuklanadi (bularsiz tizim ishlamaydi)."""
    for name in m.DEFAULT_UNITS:
        db.add(m.Unit(name=name))
    for name in m.DEFAULT_POSITIONS:
        db.add(m.Position(name=name))
    for name in m.DEFAULT_CATEGORIES:
        db.add(m.Category(name=name))

    # ishlab chiqarish xizmatlari (poligrafiya) — narx/o'lchov/formula
    services = [
        ("Laminatsiya", 2500, "m²", "x*y*n"),
        ("Noj (pichoq)", 150000, "dona", "n"),          # bir marta forma narxi
        ("Tisneniye", 3000, "m²", "x*y*n"),
        ("Viborochniy lak", 2000, "m²", "x*y*n"),
        ("Matoviy lak", 1800, "m²", "x*y*n"),
        ("Glyansoviy lak", 1800, "m²", "x*y*n"),
        ("Laklash (umumiy)", 1500, "m²", "x*y*n"),
        ("Bosma (1 rang)", 120, "dona", "n"),
    ]
    for name, price, unit, formula in services:
        db.add(m.Service(name=name, price=Decimal(price), unit=unit, formula=formula))

    # sozlanadigan formulalar (sebestoyimost) — sanoat standartlariga
    # moslangan: layner (tekis qavat) + fluting (gofra, koef. 1.35), kg da.
    # o'zgaruvchilar: x,y — o'lcham (m), g — grammaj (g/m²), n — soni (dona)
    formulas = [
        ("Tekis qavat (layner), kg", "x*y*g*n/1000",
         "1 tekis qavat og'irligi: m² × grammaj ÷ 1000"),
        ("Gofra qavat (fluting), kg", "x*y*g*1.35*n/1000",
         "Gofra qavat 1.35 koef. bilan (to'lqin ko'proq qog'oz oladi)"),
        ("3-qavat karton, kg", "x*y*(2*g+1.35*gf)*n/1000",
         "2 layner (g) + 1 fluting (gf) — jami og'irlik kg"),
        ("Kley, kg", "x*y*0.01*n",
         "Kraxmal kley ~10 g/m² (0.01 kg/m²) — sanoat me'yori"),
        ("Laminatsiya, m²", "x*y*n", "Qoplama maydoni m²"),
        ("Lak, m²", "x*y*n", "Laklanadigan maydon m²"),
    ]
    for name, expr, desc in formulas:
        db.add(m.Formula(name=name, expression=expr, description=desc))


def seed_real(db: Session):
    """Master Excel'dan real ma'lumotlar — qog'oz xaridlari va to'lovlar.
    To'lovlar FIFO bo'yicha eng eski xaridga yotqiziladi (qarz aynan chiqadi).
    Ishga tushirish: SEED_REAL=1 ./run.sh"""
    import json
    from datetime import datetime as _dt
    path = os.path.join(os.path.dirname(__file__), "real_data.json")
    if not os.path.exists(path):
        return
    data = json.load(open(path, encoding="utf-8"))

    def pdate(s):
        try:
            return _dt.strptime(s[:10], "%Y-%m-%d").date()
        except Exception:
            return date.today()

    sup = m.Supplier(name="Max Star (qog'oz yetkazib beruvchi)", phone="")
    db.add(sup)
    db.flush()

    # materiallar katalogi (real qog'oz turlari + grammaj)
    mat_by_key = {}
    for mm in data["materials"]:
        mat = m.Material(name=mm["paper"], category="Qog'oz", grammaj=mm["gr"],
                         unit="kg", last_price=Decimal(str(mm["price"])))
        db.add(mat)
        db.flush()
        mat_by_key[(mm["paper"], mm["gr"])] = mat

    # xaridlar (hammasi qarzga — keyin to'lovlar FIFO yopadi)
    purchases = []
    for p in sorted(data["purchases"], key=lambda x: x["date"] or "2026-01-01"):
        mat = mat_by_key.get((p["paper"], p["gr"]))
        if not mat:
            mat = m.Material(name=p["paper"], category="Qog'oz", grammaj=p["gr"],
                             unit="kg", last_price=Decimal(str(p["narx"])))
            db.add(mat)
            db.flush()
            mat_by_key[(p["paper"], p["gr"])] = mat
        total = Decimal(str(p["summa"]))
        pur = m.Purchase(
            material_id=mat.id, supplier_id=sup.id, qty=Decimal(str(p["kg"])),
            unit="kg", fmt=p["fmt"], unit_price=Decimal(str(p["narx"])),
            total=total, payment_type="Qarz", paid_amount=Decimal("0"),
            due_date=pdate(p["date"]) + timedelta(days=30),
            purchased_at=pdate(p["date"]), firm="макс стар")
        db.add(pur)
        db.flush()
        mat.stock_qty = Decimal(mat.stock_qty) + Decimal(str(p["kg"]))
        db.add(m.MaterialMove(material_id=mat.id, qty=Decimal(str(p["kg"])),
                              reason=f"Xarid #{pur.id}"))
        purchases.append(pur)

    # to'lovlar FIFO — eng eski xariddan yopamiz (Master Excel mantiqi)
    remaining = {pur.id: Decimal(pur.total) for pur in purchases}
    order_ids = [pur.id for pur in purchases]
    for pay in sorted(data["payments"], key=lambda x: x["date"] or "2026-01-01"):
        amt = Decimal(str(pay["amount"]))
        pdt = pdate(pay["date"])
        method = pay.get("method") or "O'tkazma"
        method = "Karta" if "карт" in method else ("O'tkazma" if "переч" in method else "Naqd")
        for pid in order_ids:
            if amt <= 0:
                break
            if remaining[pid] <= 0:
                continue
            take = min(remaining[pid], amt)
            db.add(m.PurchasePayment(purchase_id=pid, amount=take,
                                     method=method, paid_at=pdt))
            remaining[pid] -= take
            amt -= take

    # --- Kassa jurnali (приход-расход Excel'dan, 2 firma) ---
    kassa = data.get("kassa", [])
    for k in kassa:
        db.add(m.KassaEntry(
            firm=k["firm"], direction=k["dir"], who=k["who"], note=k["note"],
            amount=Decimal(str(k["amount"])), currency=k["currency"],
            entry_at=pdate(k["date"]), created_by="Excel import"))

    # --- Kassadan bo'limlarga tarqatish ---
    # 1) Ishchilar: аванс/ойлик olganlar -> Xodimlar + "Pul berildi" tarixi
    worker_names = set()
    worker_firm = {}
    for k in kassa:
        if k["dir"] == "Chiqim" and any(w in (k["note"] or "").lower()
                                        for w in ("аванс", "ойлик")):
            worker_names.add(k["who"])
            worker_firm.setdefault(k["who"], k["firm"])
    emp_by_name = {}
    for name in sorted(worker_names):
        e = m.Employee(name=name, position="Ishchi", rate_per_box=Decimal("150"),
                       firm=worker_firm.get(name, ""))
        db.add(e)
        db.flush()
        emp_by_name[name] = e

    INTERNAL = {"каса", "км", "kassa"}  # ichki o'tkazmalar — mijoz emas
    client_by_name = {}
    for k in kassa:
        if k["currency"] != "so'm":
            continue  # USD faqat kassa jurnalida turadi
        amt = Decimal(str(k["amount"]))
        when = pdate(k["date"])
        if k["dir"] == "Chiqim":
            if k["who"] in worker_names:
                # ishchiga berilgan pul (avans/oylik/mayda) -> HR tarixi
                db.add(m.CashEntry(employee_id=emp_by_name[k["who"]].id,
                                   kind="Avans", amount=amt, firm=k["firm"],
                                   note=k["note"] or "Kassadan", entry_at=when))
            else:
                # tovar/xizmat rasxodi (kley, remont, zapchast, qog'oz...)
                label = k["who"] + ((" — " + k["note"]) if k["note"] else "")
                db.add(m.CashEntry(employee_id=None, kind="Xarajat", firm=k["firm"],
                                   amount=amt, note=label, entry_at=when))
        else:  # Kirim
            if k["who"].lower() in INTERNAL:
                continue
            c = client_by_name.get(k["who"])
            if not c:
                c = m.Client(company=k["who"], category="Standart",
                             pay_type="Naqd", firm=k["firm"])
                db.add(c)
                db.flush()
                client_by_name[k["who"]] = c
            db.add(m.Payment(client_id=c.id, amount=amt, method="Naqd",
                             paid_at=when, note=k["note"] or "Kassa kirim"))

    # --- Лист2: yetkazib beruvchiga to'lov jadvali (rejalashtirilgan to'lovlar) ---
    for sc in data.get("schedule", []):
        db.add(m.PaymentSchedule(supplier_id=sup.id, due_date=pdate(sc["date"]),
                                 amount=Decimal(str(sc["amount"]))))

    db.add(m.AuditLog(who="Tizim", action="Real ma'lumotlar yuklandi (Excel)",
                      detail=f"{len(purchases)} xarid, {len(data['payments'])} to'lov, "
                             f"kredit limit {data.get('credit_limit', 0):,.0f} so'm / "
                             f"{data.get('credit_days', 30)} kun"))
    db.commit()


def seed(db: Session):
    if db.query(m.User).first():
        return

    # --- bitta boshqaruvchi: hammasini o'zi boshqaradi,
    #     kerak bo'lsa xodimlarga o'zi login yaratadi (Sozlamalar bo'limida) ---
    db.add(m.User(login="admin", password_hash=hash_pw("1234"),
                  name="Boshqaruvchi", role="Rahbar"))

    # --- standart kataloglar (prod rejimda ham kerak) ---
    seed_catalogs(db)

    # --- Rejimlar: standart = mijozning Excel ma'lumotlari (birinchi run'da) ---
    if os.getenv("SEED_DEMO") == "1":
        pass  # quyida demo yuklanadi
    elif os.getenv("SEED_EMPTY") == "1":
        db.add(m.AuditLog(who="Tizim", action="Tizim ishga tushdi",
                          detail="Bo'sh rejim — admin/1234, parolni almashtiring"))
        db.commit()
        return
    else:
        # STANDART: mijozning Excel'laridagi haqiqiy ma'lumotlar yuklanadi —
        # qog'oz xaridlari (макс стар) + kassa jurnali (приход-расход).
        # Mijoz hech narsani qaytadan kiritmasdan davom etaveradi.
        db.commit()
        seed_real(db)
        return

    # --- yetkazib beruvchilar ---
    sup1 = m.Supplier(name="Toshkent Qog'oz Kombinati", phone="+998 71 200 11 22")
    sup2 = m.Supplier(name="Andijon Kraft Paper", phone="+998 74 300 44 55")
    sup3 = m.Supplier(name="Kazakhstan Paper Mills", phone="+7 727 300 00 11")
    db.add_all([sup1, sup2, sup3])
    db.flush()

    # --- xomashyo lotlari (FIFO uchun narxlari har xil) ---
    lots = [
        (sup1, "K1", 3, 16000, 2900, 60), (sup1, "K1", 3, 12000, 3100, 25),
        (sup2, "K1", 3, 9000, 3250, 8),
        (sup1, "K0", 3, 14000, 2500, 40), (sup2, "K0", 3, 8000, 2650, 12),
        (sup2, "K2", 3, 12000, 3600, 35), (sup3, "K2", 3, 8000, 3750, 10),
        (sup3, "T-22", 5, 15000, 4800, 30), (sup3, "T-22", 5, 8000, 5000, 9),
        (sup1, "T-23", 5, 9000, 5400, 20),
    ]
    lot_objs = []
    for i, (sup, grade, layers, qty, price, days_ago) in enumerate(lots, 1):
        # eski m2 qiymatlarini kg ga taxminan o'giramiz (demo uchun):
        # grammaj = 120 g/m2 -> kg = m2 * 0.12; narx so'm/kg = narx_m2 / 0.12
        grammage = 120 if layers == 3 else 200
        kg = (Decimal(qty) * Decimal(grammage) / Decimal(1000)).quantize(Decimal("0.01"))
        price_kg = (Decimal(price) * Decimal(1000) / Decimal(grammage)).quantize(Decimal("0.01"))
        lot = m.RawLot(
            lot_no=f"LOT-{i:04d}", supplier_id=sup.id, grade=grade, grammage=grammage,
            qty_kg=kg, remaining_kg=kg, price_per_kg=price_kg,
            received_at=date.today() - timedelta(days=days_ago))
        db.add(lot)
        lot_objs.append(lot)
    db.flush()

    # --- yetkazib beruvchi to'lovlari + grafik ---
    db.add(m.SupplierPayment(supplier_id=sup1.id, amount=Decimal("95000000"),
                             paid_at=date.today() - timedelta(days=30), note="Qisman to'lov"))
    db.add(m.SupplierPayment(supplier_id=sup2.id, amount=Decimal("85000000"),
                             paid_at=date.today() - timedelta(days=15), note="O'tkazma"))
    db.add(m.SupplierPayment(supplier_id=sup3.id, amount=Decimal("150000000"),
                             paid_at=date.today() - timedelta(days=20), note="O'tkazma"))
    for d, amt, sup in [(3, 15000000, sup1), (10, 12000000, sup3), (17, 10000000, sup3)]:
        db.add(m.PaymentSchedule(supplier_id=sup.id,
                                 due_date=date.today() + timedelta(days=d),
                                 amount=Decimal(amt)))

    # --- mijozlar ---
    clients_data = [
        ("Kompaniya 1 MChJ", "Sardor A.", "+998901112233", "305412890", "Pul o'tkazish", "VIP", 120_000_000),
        ("Kompaniya A", "Malika R.", "+998935556677", "301877665", "Pul o'tkazish", "VIP", 200_000_000),
        ("Kompaniya B", "Botir K.", "+998971234567", "308455112", "Naqd", "Standart", 50_000_000),
        ("Kompaniya C", "Dilnoza T.", "+998662223344", "204811733", "Naqd", "Standart", 30_000_000),
        ("Kompaniya 2 MChJ", "Akmal N.", "+998733334455", "202988441", "Pul o'tkazish", "Standart", 40_000_000),
        ("Kompaniya 3 XK", "Umid S.", "+998909876543", "", "Naqd", "Yangi", 10_000_000),
        ("Kompaniya D", "G'ayrat M.", "+998942221100", "207344556", "Naqd", "Standart", 25_000_000),
    ]
    clients = []
    for comp, contact, phone, inn, pt, cat, limit in clients_data:
        c = m.Client(company=comp, contact=contact, phone=phone, inn=inn,
                     pay_type=pt, category=cat, credit_limit=Decimal(limit))
        db.add(c)
        clients.append(c)
    db.flush()

    # --- buyurtmalar (6 oy tarixi, har xil status) ---
    sizes = [(400, 300, 250), (600, 400, 400), (300, 200, 150), (500, 350, 300),
             (350, 250, 200), (450, 300, 350), (250, 200, 100)]
    grade_pool = [("K1", 3), ("K0", 3), ("K2", 3), ("T-22", 5), ("T-23", 5)]
    statuses_hist = [m.ST_YETKAZILDI] * 6 + [m.ST_OMBORDA, m.ST_SEXDA, m.ST_KUTISHDA, m.ST_MUZOKARA]
    orders = []
    for i in range(34):
        c = random.choice(clients)
        L, W, H = random.choice(sizes)
        grade, layers = random.choice(grade_pool)
        colors = random.choice([0, 0, 1, 2])
        qty = random.choice([500, 1000, 1500, 2000, 3000, 5000])
        days_ago = random.randint(0, 170) if i < 24 else random.randint(0, 25)
        status = random.choice(statuses_hist) if days_ago < 30 else m.ST_YETKAZILDI
        q = s.quote(db, L, W, H, layers, grade, colors, qty, c.category)
        created = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 10))
        o = m.Order(
            client_id=c.id, length_mm=L, width_mm=W, height_mm=H, layers=layers,
            grade=grade, colors=colors, qty=qty, m2_per_box=q["m2_per_box"],
            unit_cost=q["unit_cost"], unit_price=q["unit_price"], total=q["total"],
            status=status, created_at=created,
            due_date=created.date() + timedelta(days=15),
            delivered_at=created.date() + timedelta(days=random.randint(3, 8))
            if status == m.ST_YETKAZILDI else None,
            accepted_stamp=status == m.ST_YETKAZILDI and random.random() > 0.4,
        )
        db.add(o)
        orders.append(o)
    db.flush()
    # 2-qadam: soha maydonlarini attributes ga ham yozamiz. flush'dan keyin —
    # bu yerda `tur`/`is_offset` berilmagan, ular ustun standartidan keladi.
    for o in orders:
        soha_yoz(o)

    # --- spisaniya (sotilganlar uchun FIFO retrospektiv emas — soddalashtirib bugungi lotlardan) ---
    for o in orders:
        if o.status in (m.ST_SEXDA, m.ST_OMBORDA, m.ST_YETKAZILDI):
            brak = Decimal("1.05")
            xom, marka = domain.xomashyo_kerak(o)
            if xom is None:
                continue   # bu sohada avtomatik spisaniya yo'q
            need = (xom * brak).quantize(Decimal("0.0001"))
            try:
                s.fifo_writeoff(db, marka, need, order_id=o.id,
                                note=f"Buyurtma #{o.id} spisaniya")
            except ValueError:
                pass

    # --- mijoz to'lovlari (qisman — debitor qarz qolsin) ---
    for o in orders:
        if o.status in (m.ST_OMBORDA, m.ST_YETKAZILDI):
            share = random.choice([Decimal("1"), Decimal("1"), Decimal("0.7"),
                                   Decimal("0.5"), Decimal("0.3"), Decimal("0")])
            if share > 0:
                db.add(m.Payment(
                    client_id=o.client_id, order_id=o.id,
                    amount=(Decimal(o.total) * share).quantize(Decimal("0.01")),
                    method=random.choice(["Naqd", "O'tkazma"]),
                    paid_at=o.created_at.date() + timedelta(days=random.randint(1, 20))))

    # --- xodimlar va ish qaydlari ---
    emps_data = [
        ("Olim Rahimov", "Stanokchi", 160, "1-brigada"),
        ("Sherzod Aliyev", "Stanokchi", 160, "1-brigada"),
        ("Kamol Yo'ldoshev", "Yordamchi", 110, "1-brigada"),
        ("Farrux Nazarov", "Stanokchi", 165, "2-brigada"),
        ("Islom Qodirov", "Flekso operatori", 190, "2-brigada"),
        ("Ravshan Xolmatov", "Yordamchi", 105, "2-brigada"),
    ]
    emps = []
    for name, pos, rate, brig in emps_data:
        e = m.Employee(name=name, position=pos, rate_per_box=Decimal(rate), brigade=brig)
        db.add(e)
        emps.append(e)
    db.flush()

    for _ in range(70):
        e = random.choice(emps)
        qty = random.randint(150, 900)
        qc = random.random() > 0.06
        amount = Decimal(e.rate_per_box) * qty if qc else Decimal("0")
        db.add(m.WorkEntry(
            employee_id=e.id, order_id=random.choice(orders).id, qty=qty,
            qc_passed=qc, rate=e.rate_per_box, amount=amount,
            worked_at=date.today() - timedelta(days=random.randint(0, 27))))

    # --- kassa: avans va xarajatlar ---
    cash_data = [
        (emps[0], "Avans", 800000, "Oylikdan avans"),
        (emps[1], "Avans", 500000, "Oylikdan avans"),
        (emps[3], "Avans", 1200000, "Oylikdan avans"),
        (emps[2], "Avans", 150000, "Yo'lkira + tushlik"),
        (None, "Xarajat", 420000, "Kley 20 kg"),
        (None, "Xarajat", 180000, "Skotch 48mm x 36 dona"),
        (None, "Xarajat", 950000, "Stanok pichog'i almashtirish"),
    ]
    for e, kind, amt, note in cash_data:
        db.add(m.CashEntry(employee_id=e.id if e else None, kind=kind,
                           amount=Decimal(amt), note=note,
                           entry_at=date.today() - timedelta(days=random.randint(0, 20))))

    # --- POLIGRAFIYA: qog'oz katalogi (Master Excel'dan) + xaridlar ---
    papers = [
        ("Silver pak", "140"), ("Silver pak", "170"), ("Silver pak", "190"),
        ("Silver pak", "210"), ("Silver pak", "250"), ("Silver pak", "270"),
        ("Silver pak", "300"), ("Fin kraft", "145"), ("Fin kraft", "160"),
        ("Xitoy", "140"), ("Xitoy sток", "125"), ("Nemis eko", "140"),
        ("MM nemis", "140"), ("Ekonom", "140"),
    ]
    paper_mats = []
    for name, gr in papers:
        mat = m.Material(name=name, category="Qog'oz", grammaj=f"{gr} гр",
                         unit="kg", last_price=Decimal(random.choice([11600, 12400, 13300, 13700, 14300])))
        db.add(mat)
        paper_mats.append(mat)
    # yana bir nechta boshqa material
    for nm, cat, unit, price in [("Kley PVA", "Kley", "kg", 18000),
                                 ("Ofset bo'yoq (qora)", "Bo'yoq", "kg", 45000),
                                 ("Matoviy lak", "Lak", "litr", 38000),
                                 ("Laminatsiya plyonkasi", "Plyonka", "rulon", 250000)]:
        db.add(m.Material(name=nm, category=cat, unit=unit, last_price=Decimal(price)))
    db.flush()

    # xaridlar (Excel'dagi kabi kg'da, naqd va qarzga)
    suppliers_p = [sup1, sup2, sup3]
    for i in range(20):
        mat = random.choice(paper_mats)
        sup = random.choice(suppliers_p)
        qty = Decimal(random.randint(90, 1200))
        price = Decimal(mat.last_price)
        total = (qty * price).quantize(Decimal("0.01"))
        ptype = random.choice(["Naqd", "Naqd", "Qarz", "Qarz", "Keyinroq to'lash"])
        days_ago = random.randint(1, 180)
        paid = total if ptype == "Naqd" else (total * Decimal(random.choice(["0", "0.3", "0.5", "1"]))).quantize(Decimal("0.01"))
        pur = m.Purchase(
            material_id=mat.id, supplier_id=sup.id, qty=qty, unit="kg",
            fmt=random.choice(["85*59", "62*76", "ф62*85", "90*85", "66*68"]),
            unit_price=price, total=total, payment_type=ptype, paid_amount=paid,
            due_date=(date.today() + timedelta(days=random.randint(5, 30))) if ptype != "Naqd" else None,
            purchased_at=date.today() - timedelta(days=days_ago))
        db.add(pur)
        mat.stock_qty = Decimal(mat.stock_qty) + qty
        db.flush()
        db.add(m.MaterialMove(material_id=mat.id, qty=qty, reason=f"Xarid #{pur.id}"))

    # --- audit boshlang'ich yozuvi ---
    db.add(m.AuditLog(who="Tizim", action="Demo ma'lumotlar yuklandi",
                      detail="Birinchi ishga tushirish"))
    db.commit()
