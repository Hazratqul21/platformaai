from datetime import date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import get_user, require_roles
from .. import models as m
from .. import domain
from .. import services as s
from .. import kassa_sync as ks

router = APIRouter(prefix="/api/finance", tags=["Moliya"])

def _sotilgan():
    """Sotilgan hisoblanadigan maqomlar — ish tartibidan (modul) olinadi."""
    return domain.statuslar("ishlab_chiqarish", "tayyor", "topshirildi")


class PayIn(BaseModel):
    client_id: int
    order_id: int | None = None
    amount: float
    method: str = "Naqd"
    note: str = ""


@router.post("/payments")
def add_payment(data: PayIn, db: Session = Depends(get_db),
                user=Depends(require_roles("Buxgalter", "Menejer"))):
    c = db.get(m.Client, data.client_id)
    if not c:
        raise HTTPException(404, "Мижоз топилмади")
    if data.amount <= 0:
        raise HTTPException(400, "Тўлов суммаси 0 дан катта бўлсин")
    if data.order_id:
        o = db.get(m.Order, data.order_id)
        if not o or o.client_id != c.id:
            raise HTTPException(400, "Буюртма бу мижозга тегишли эмас")
    p = m.Payment(client_id=c.id, order_id=data.order_id,
                  amount=Decimal(str(data.amount)), method=data.method, note=data.note)
    db.add(p)
    db.flush()
    ks.mijoz_tolovi(db, p, user.name)
    # Bosh kitob — parallel (xatosi to'lovni to'xtatmaydi)
    from ..hisob import ulash as gl_ulash
    gl_ulash.mijoz_tolovi(db, p, user.name)
    db.add(m.AuditLog(who=user.name, action="To'lov qabul qilindi",
                      detail=f"{c.company} · {data.amount:,.0f} so'm · {data.method}"))
    db.commit()
    return {"id": p.id}


@router.get("/payments")
def payment_list(client_id: int | None = None, limit: int = 300,
                 db: Session = Depends(get_db), user=Depends(get_user)):
    """To'lovlar ro'yxati — xato kiritilganini topib o'chirish uchun."""
    q = db.query(m.Payment)
    if client_id:
        q = q.filter(m.Payment.client_id == client_id)
    rows = q.order_by(m.Payment.paid_at.desc(), m.Payment.id.desc()).limit(
        max(1, min(limit, 1000))).all()
    return [{"id": p.id, "client_id": p.client_id,
             "client": p.client.company if p.client else "—",
             "order_id": p.order_id, "amount": float(p.amount), "method": p.method,
             "paid_at": p.paid_at.isoformat(), "note": p.note} for p in rows]


@router.delete("/payments/{pid}")
def del_payment(pid: int, db: Session = Depends(get_db),
                user=Depends(require_roles("Rahbar"))):
    """Xato kiritilgan to'lovni o'chirish.

    Ilgari bunday imkon yo'q edi — noto'g'ri yozilgan to'lov mijoz qarzini
    umrbod buzib turardi va faqat bazaga qo'lda kirib tuzatish mumkin edi.
    Kassadagi nusxasi ham shu bilan birga o'chadi.
    """
    p = db.get(m.Payment, pid)
    if not p:
        raise HTTPException(404, "Тўлов топилмади")
    c = db.get(m.Client, p.client_id)
    client_id = p.client_id
    summa, usul, sana = float(p.amount), p.method, p.paid_at
    ks.ochir(db, "payment", p.id)
    db.delete(p)
    db.add(m.AuditLog(
        who=user.name, action="To'lov o'chirildi",
        detail=f"{c.company if c else '?'} · {summa:,.0f} so'm · {usul} · "
               f"{sana.strftime('%d.%m.%Y')}".replace(",", " ")))
    db.commit()
    bal = s.client_balance(db, client_id)
    return {"ok": True, "client_debt": float(bal["debt"])}


@router.get("/debtors")
def debtors(firm: str | None = None, db: Session = Depends(get_db), user=Depends(get_user)):
    """Debitor qarzdorlik + aging jadvali (TZ 4.2)."""
    return s.debt_aging(db, firm)


@router.get("/cashflow")
def cashflow(days: int = 7, firm: str | None = None,
             db: Session = Depends(get_db), user=Depends(get_user)):
    return s.cash_flow_forecast(db, days, firm)


@router.get("/dashboard")
def dashboard(firm: str | None = None, db: Session = Depends(get_db), user=Depends(get_user)):
    """Rahbar bosh sahifasi (TZ 4.4).

    firm berilsa — barcha ko'rsatkich shu firma bo'yicha hisoblanadi.
    Buyurtmada firma ustuni yo'q, u mijozning firmasidan olinadi.
    Firmasi belgilanmagan yozuv ikkala firmada ham ko'rinadi (ro'yxatlardagi qoida bilan bir xil).
    """
    today = date.today()
    month_start = today.replace(day=1)
    prev_start = (month_start - timedelta(days=1)).replace(day=1)

    def firma_order(q):
        return q.filter(m.Order.client.has(m.Client.firm.in_([firm, ""]))) if firm else q

    def firma_kassa(q):
        return q.filter(m.KassaEntry.firm.in_([firm, ""])) if firm else q

    def sales_between(a, b):
        q = (db.query(func.coalesce(func.sum(m.Order.total), 0))
             .filter(m.Order.status.in_(_sotilgan()),
                     m.Order.created_at >= a, m.Order.created_at < b))
        return Decimal(firma_order(q).scalar())

    today_sales = sales_between(today, today + timedelta(days=1))
    month_sales = sales_between(month_start, today + timedelta(days=1))
    prev_sales = sales_between(prev_start, month_start)
    growth = float((month_sales - prev_sales) / prev_sales * 100) if prev_sales else 0

    aging_data = s.debt_aging(db, firm)
    total_debit = sum(x["debt"] for x in aging_data)
    # Bizning qarzimiz = har yetkazib beruvchi bo'yicha qarz (zakup xaridlari va
    # ombor partiyalari birga hisoblanadi — supplier_balance ichida). Avansda
    # turgan (manfiy qarz) yetkazib beruvchi qarzni kamaytirmaydi.
    total_credit = 0.0
    for sup in db.query(m.Supplier).all():
        bal = s.supplier_balance(db, sup.id, firm)
        if bal["debt"] > 0:
            total_credit += float(bal["debt"])

    # kassa jurnali balansi (kirim - chiqim, so'mda) — firma bo'yicha
    kassa_kirim = float(firma_kassa(
        db.query(func.coalesce(func.sum(m.KassaEntry.amount), 0))
        .filter(m.KassaEntry.direction == "Kirim",
                m.KassaEntry.currency == "so'm")).scalar())
    kassa_chiqim = float(firma_kassa(
        db.query(func.coalesce(func.sum(m.KassaEntry.amount), 0))
        .filter(m.KassaEntry.direction == "Chiqim",
                m.KassaEntry.currency == "so'm")).scalar())

    top_debtors = aging_data[:5]

    # marja dinamikasi — oxirgi 6 oy
    margins, sales_series = [], []
    for i in range(5, -1, -1):
        mstart = (month_start - timedelta(days=1)).replace(day=1) if i else month_start
        # oyni to'g'ri hisoblash
        y, mo = today.year, today.month - i
        while mo <= 0:
            mo += 12
            y -= 1
        a = date(y, mo, 1)
        b = date(y + (mo == 12), (mo % 12) + 1, 1)
        rows = firma_order(
            db.query(m.Order)
            .filter(m.Order.status.in_(_sotilgan()), m.Order.created_at >= a, m.Order.created_at < b)
        ).all()
        rev = sum(Decimal(o.total) for o in rows)
        cost = sum(Decimal(o.unit_cost) * o.qty for o in rows)
        margin = float((rev - cost) / rev * 100) if rev else 0
        margins.append({"month": a.strftime("%Y-%m"), "margin": round(margin, 1)})
        sales_series.append({"month": a.strftime("%Y-%m"), "sales": float(rev)})

    counts = {st: firma_order(db.query(func.count(m.Order.id))
                              .filter(m.Order.status == st)).scalar()
              for st in domain.modul().nomlar}

    return {
        "today_sales": float(today_sales), "month_sales": float(month_sales),
        "growth_percent": round(growth, 1),
        "total_debit": total_debit, "total_credit": total_credit,
        "top_debtors": top_debtors, "margins": margins, "sales_series": sales_series,
        "order_counts": counts,
        "kassa_balans": kassa_kirim - kassa_chiqim,
        "kassa_kirim": kassa_kirim, "kassa_chiqim": kassa_chiqim,
        "low_stock": s.low_stock_alerts(db),
        "cashflow": s.cash_flow_forecast(db, 7, firm),
    }


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), user=Depends(require_roles("Rahbar", "Buxgalter", "Menejer"))):
    return {k: s.get_setting(db, k) for k in s.DEFAULT_SETTINGS}


class SettingsIn(BaseModel):
    values: dict[str, str]


class FormulaCheckIn(BaseModel):
    key: str      # formula_m2 | formula_sebestoimost
    expr: str


@router.post("/formula-check")
def formula_check(data: FormulaCheckIn, user=Depends(require_roles("Rahbar"))):
    """Formulani saqlashdan oldin tekshirib ko'rish — yozayotganda darhol javob."""
    xato = s.formula_xato(data.expr, data.key)
    if xato:
        return {"ok": False, "xato": xato}
    namuna = {"l": 400, "w": 300, "h": 250, "m": 0.8, "p": 1700,
              "b": 1.05, "c": 1, "k": 120}
    ruxsat = s.FORMULA_VARS.get(data.key, {})
    natija = s.eval_formula(data.expr, **{v: namuna[v] for v in ruxsat})
    return {"ok": True, "natija": round(natija, 4),
            "izoh": ", ".join(f"{v}={namuna[v]}" for v in ruxsat)}


@router.post("/settings")
def set_settings(data: SettingsIn, db: Session = Depends(get_db),
                 user=Depends(require_roles("Rahbar"))):
    # Formulalar oldindan tekshiriladi — noto'g'ri formula bazaga tushmasin,
    # aks holda tizim jimgina zaxira formulaga o'tib ketadi va hech kim sezmaydi
    for key in ("formula_m2", "formula_sebestoimost"):
        if key in data.values:
            xato = s.formula_xato(data.values[key], key)
            if xato:
                nom = "м² формуласи" if key == "formula_m2" else "таннарх формуласи"
                raise HTTPException(400, f"{nom}: {xato}")
    for k, v in data.values.items():
        if k not in s.DEFAULT_SETTINGS:
            continue
        row = db.get(m.Setting, k)
        if row:
            row.value = v
        else:
            db.add(m.Setting(key=k, value=v))
    db.add(m.AuditLog(who=user.name, action="Sozlamalar o'zgardi",
                      detail=", ".join(sorted(data.values))[:180]))
    db.commit()
    return {"ok": True}


@router.get("/audit")
def audit(limit: int = 400, db: Session = Depends(get_db), user=Depends(get_user)):
    # Foydalanuvchi kiritgan amallarni to'liq ko'ra olsin (ilgari 80 ta bilan
    # cheklangan edi — eski yozuvlar "yo'qolgandek" ko'rinardi).
    limit = max(1, min(limit, 3000))
    rows = db.query(m.AuditLog).order_by(m.AuditLog.at.desc()).limit(limit).all()
    # Bazada UTC saqlanadi — foydalanuvchiga Toshkent vaqti ko'rsatiladi
    return [{"who": r.who, "action": r.action, "detail": r.detail,
             "at": s.mahalliy_vaqt(r.at).isoformat()} for r in rows]
