from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import get_user, require_roles
from .. import models as m
from .. import services as s
from .. import kassa_sync as ks

router = APIRouter(prefix="/api/hr", tags=["HR"])


class EmployeeIn(BaseModel):
    name: str
    position: str = "Stanokchi"
    phone: str = ""
    rate_per_box: float = 150
    brigade: str = ""
    firm: str = ""


class SalaryIn(BaseModel):
    employee_id: int
    amount: float
    firm: str = ""

class WorkIn(BaseModel):
    employee_id: int
    order_id: int | None = None
    qty: int
    qc_passed: bool = True


class CashIn(BaseModel):
    employee_id: int | None = None
    kind: str  # Avans / Xarajat
    amount: float
    note: str = ""
    firm: str = ""


@router.get("/employees")
def employees(firm: str | None = None, db: Session = Depends(get_db), user=Depends(get_user)):
    today = date.today()
    today_work = (
        db.query(m.WorkEntry.employee_id, func.coalesce(func.sum(m.WorkEntry.amount), 0).label("amount"))
        .filter(m.WorkEntry.qc_passed.is_(True), m.WorkEntry.worked_at == today)
        .group_by(m.WorkEntry.employee_id).all()
    )
    today_map = {row.employee_id: row.amount for row in today_work}
    
    out = []
    eq = db.query(m.Employee).filter(m.Employee.active.is_(True))
    if firm:
        eq = eq.filter(m.Employee.firm.in_([firm, ""]))
    for e in eq.all():
        today_amount = today_map.get(e.id, Decimal(0))
        out.append({
            "id": e.id, "name": e.name, "position": e.position, "phone": e.phone,
            "rate_per_box": float(e.rate_per_box), "brigade": e.brigade, "firm": e.firm,
            "today_earned": float(today_amount),  # real vaqtda kunlik pul (TZ 3.1)
        })
    return out


@router.post("/employees")
def add_employee(data: EmployeeIn, db: Session = Depends(get_db),
                 user=Depends(require_roles("Sex boshlig'i", "Buxgalter"))):
    e = m.Employee(**{**data.model_dump(), "rate_per_box": Decimal(str(data.rate_per_box))})
    db.add(e)
    db.commit()
    return {"id": e.id}


@router.post("/work")
def add_work(data: WorkIn, db: Session = Depends(get_db),
             user=Depends(require_roles("Sex boshlig'i"))):
    """QC checkpoint: sifatdan o'tgan qutilar hisobga yoziladi."""
    e = db.get(m.Employee, data.employee_id)
    if not e:
        raise HTTPException(404, "Ходим топилмади")
    if data.qty <= 0:
        raise HTTPException(400, "Qutilar soni 0 dan katta bo'lsin")
    rate = Decimal(e.rate_per_box)
    amount = (rate * data.qty).quantize(Decimal("0.01")) if data.qc_passed else Decimal("0")
    w = m.WorkEntry(employee_id=e.id, order_id=data.order_id, qty=data.qty,
                    qc_passed=data.qc_passed, rate=rate, amount=amount)
    db.add(w)
    db.add(m.AuditLog(who=user.name, action="Ish qayd etildi",
                      detail=f"{e.name} · {data.qty} dona · QC {'✓' if data.qc_passed else '✗'}"))
    db.commit()
    return {"status": "ok", "amount": float(amount)}


@router.post("/salary")
def add_salary(data: SalaryIn, db: Session = Depends(get_db),
               user=Depends(require_roles("Sex boshlig'i", "Rahbar", "Buxgalter"))):
    """Xodimga qat'iy oylik (oklad) yozish (qutisiz)."""
    e = db.get(m.Employee, data.employee_id)
    if not e:
        raise HTTPException(404, "Ходим топилмади")
    amt = Decimal(str(data.amount))
    w = m.WorkEntry(employee_id=e.id, order_id=None, qty=0, qc_passed=True, rate=amt, amount=amt)
    db.add(w)
    db.add(m.AuditLog(who=user.name, action="Oklad yozildi",
                      detail=f"{e.name} ga {amt} so'm oklad yozildi"))
    db.commit()
    return {"status": "ok", "amount": float(amt)}


@router.get("/employees/{eid}/detalizatsiya")
def employee_detail(eid: int, db: Session = Depends(get_db), user=Depends(get_user)):
    """Xodim detalizatsiyasi — daftar ko'rinishi: chapda ishlagani (ishbay/oklad),
    o'ngda undan olgan pullari (avans). Pastida: hisoblandi − olindi = qo'lga tegadi."""
    e = db.get(m.Employee, eid)
    if not e:
        raise HTTPException(404, "Ходим топилмади")

    ishlar = []
    for w in (db.query(m.WorkEntry).filter(m.WorkEntry.employee_id == eid)
              .order_by(m.WorkEntry.worked_at, m.WorkEntry.id).all()):
        ishlar.append({
            "sana": w.worked_at.isoformat(),
            "turi": "Oklad" if w.qty == 0 else "Ishbay",
            "buyurtma": w.order_id,
            "dona": w.qty,
            "narxi": float(w.rate),
            "summa": float(w.amount),
            "sifat": w.qc_passed,     # brak bo'lsa pul yozilmaydi
        })

    olgan_pullari = []
    for c in (db.query(m.CashEntry)
              .filter(m.CashEntry.employee_id == eid, m.CashEntry.kind == "Avans")
              .order_by(m.CashEntry.entry_at, m.CashEntry.id).all()):
        olgan_pullari.append({
            "sana": c.entry_at.isoformat(),
            "summa": float(c.amount),
            "nimaga": c.note or "",
        })

    # brakdan o'tmagan ish haqi hisobga qo'shilmaydi
    hisoblandi = sum(Decimal(str(x["summa"])) for x in ishlar if x["sifat"])
    olindi = sum(Decimal(str(x["summa"])) for x in olgan_pullari)
    return {
        "employee_id": e.id, "name": e.name, "position": e.position,
        "brigade": e.brigade, "phone": e.phone, "firm": e.firm,
        "rate_per_box": float(e.rate_per_box),
        "ishlar": ishlar, "olgan_pullari": olgan_pullari,
        "jami_hisoblandi": float(hisoblandi),
        "jami_olindi": float(olindi),
        "qolgan": float(hisoblandi - olindi),
        "jami_qutilar": sum(x["dona"] for x in ishlar if x["sifat"]),
    }


@router.get("/work")
def work_list(firm: str | None = None, db: Session = Depends(get_db), user=Depends(get_user)):
    from sqlalchemy.orm import joinedload
    q = db.query(m.WorkEntry).options(joinedload(m.WorkEntry.employee))
    if firm:   # ish qaydida firma yo'q — xodimning firmasidan olinadi
        q = q.filter(m.WorkEntry.employee.has(m.Employee.firm.in_([firm, ""])))
    rows = q.order_by(m.WorkEntry.worked_at.desc(), m.WorkEntry.id.desc()).limit(100).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id, "employee": r.employee.name if r.employee else "?", "order_id": r.order_id,
            "qty": r.qty, "qc_passed": r.qc_passed, "rate": float(r.rate),
            "amount": float(r.amount), "worked_at": r.worked_at.isoformat(),
        })
    return out


@router.post("/cash")
def add_cash(data: CashIn, db: Session = Depends(get_db),
             user=Depends(require_roles("Buxgalter", "Sex boshlig'i"))):
    """Avans = xodimga berilgan pul (xodim majburiy, izoh ixtiyoriy).
    Xarajat = sex rasxodi (kley, skotch...) — xodimga bog'lanmaydi."""
    if data.kind not in ("Avans", "Xarajat"):
        raise HTTPException(400, "kind: Avans yoki Xarajat")
    if data.kind == "Avans" and not data.employee_id:
        raise HTTPException(400, "Pul berish uchun xodim tanlanishi shart")
    if data.kind == "Xarajat" and data.employee_id:
        raise HTTPException(400, "Sex xarajati xodimga yozilmaydi — "
                                 "xodimga pul berish uchun «Pul berish» ishlatiladi")
    if data.amount <= 0:
        raise HTTPException(400, "Сумма 0 дан катта бўлсин")
    c = m.CashEntry(employee_id=data.employee_id, kind=data.kind,
                    amount=Decimal(str(data.amount)), note=data.note, firm=data.firm)
    db.add(c)
    db.flush()
    who = db.get(m.Employee, data.employee_id).name if data.employee_id else "sex"

    # Sex xarajati ham, xodimga berilgan avans ham kassadan chiqqan puldir —
    # ikkisi ham kassa jurnaliga tushadi va cash_entries ga bog'lanadi. Bog'lanish
    # borligi uchun kassaga takror tushmaydi va yozuv o'chirilsa ikkalasi ham ketadi.
    if data.kind == "Xarajat":
        ks.sex_xarajati(db, c, user.name)
    else:
        ks.xodim_avansi(db, c, user.name)

    db.add(m.AuditLog(who=user.name,
                      action="Pul berildi" if data.kind == "Avans" else "Xarajat yozildi",
                      detail=f"{who} · {data.amount:,.0f} so'm · {data.note or 'izohsiz'}"))
    db.commit()
    return {"id": c.id}


@router.get("/cash")
def cash_list(firm: str | None = None, db: Session = Depends(get_db), user=Depends(get_user)):
    from sqlalchemy.orm import joinedload
    q = db.query(m.CashEntry).options(joinedload(m.CashEntry.employee))
    if firm:
        q = q.filter(m.CashEntry.firm.in_([firm, ""]))
    rows = q.order_by(m.CashEntry.entry_at.desc(),
                      m.CashEntry.id.desc()).limit(200).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id, "employee": r.employee.name if r.employee else "—", "kind": r.kind,
            "amount": float(r.amount), "note": r.note, "entry_at": r.entry_at.isoformat(),
        })
    return out


@router.get("/payroll")
def payroll(year: int | None = None, month: int | None = None, firm: str | None = None,
            db: Session = Depends(get_db), user=Depends(require_roles("Buxgalter", "Sex boshlig'i"))):
    """Yakuniy oylik: ishbay summa − avans/xarajat = toza qoldiq (TZ 3.3)."""
    today = date.today()
    return s.payroll(db, year or today.year, month or today.month, firm)


@router.get("/analytics")
def analytics(firm: str | None = None, db: Session = Depends(get_db),
              user=Depends(require_roles("Buxgalter", "Sex boshlig'i"))):
    """Xodimlar analitikasi: 6 oylik fond dinamikasi, kirdi-chiqdi, brak %.

    firm berilsa — barcha ko'rsatkich shu firma bo'yicha. Ish qaydida (work_entries)
    firma ustuni yo'q — u xodimning firmasidan olinadi. Firmasi belgilanmagan yozuv
    ikkala firmada ham ko'rinadi (boshqa ro'yxatlardagi qoida bilan bir xil)."""
    today = date.today()

    def fw(q):   # ish qaydlarini xodim firmasi bo'yicha
        return q.filter(m.WorkEntry.employee.has(m.Employee.firm.in_([firm, ""]))) if firm else q

    def fc(q):   # pul/xarajat yozuvlarini firma bo'yicha
        return q.filter(m.CashEntry.firm.in_([firm, ""])) if firm else q

    # --- 6 oylik dinamika: ishbay fond / avans / umumiy xarajat ---
    months = []
    for i in range(5, -1, -1):
        y, mo = today.year, today.month - i
        while mo <= 0:
            mo += 12
            y -= 1
        a = date(y, mo, 1)
        b = date(y + (mo == 12), (mo % 12) + 1, 1)
        earned = fw(db.query(func.coalesce(func.sum(m.WorkEntry.amount), 0)).filter(
            m.WorkEntry.qc_passed.is_(True),
            m.WorkEntry.worked_at >= a, m.WorkEntry.worked_at < b)).scalar()
        advances = fc(db.query(func.coalesce(func.sum(m.CashEntry.amount), 0)).filter(
            m.CashEntry.kind == "Avans",
            m.CashEntry.entry_at >= a, m.CashEntry.entry_at < b)).scalar()
        expenses = fc(db.query(func.coalesce(func.sum(m.CashEntry.amount), 0)).filter(
            m.CashEntry.kind == "Xarajat",
            m.CashEntry.entry_at >= a, m.CashEntry.entry_at < b)).scalar()
        boxes = fw(db.query(func.coalesce(func.sum(m.WorkEntry.qty), 0)).filter(
            m.WorkEntry.qc_passed.is_(True),
            m.WorkEntry.worked_at >= a, m.WorkEntry.worked_at < b)).scalar()
        months.append({"month": a.strftime("%Y-%m"), "earned": float(earned),
                       "advances": float(advances), "expenses": float(expenses),
                       "boxes": int(boxes)})

    # --- xodim kesimida butun davr kirdi-chiqdi + brak % ---
    per_employee = []
    
    work_stats = db.query(
        m.WorkEntry.employee_id,
        m.WorkEntry.qc_passed,
        func.coalesce(func.sum(m.WorkEntry.amount), 0).label("amount"),
        func.coalesce(func.sum(m.WorkEntry.qty), 0).label("qty")
    ).group_by(m.WorkEntry.employee_id, m.WorkEntry.qc_passed).all()
    
    earned_map = {}
    qty_ok_map = {}
    qty_bad_map = {}
    for row in work_stats:
        if row.qc_passed:
            earned_map[row.employee_id] = row.amount
            qty_ok_map[row.employee_id] = row.qty
        else:
            qty_bad_map[row.employee_id] = row.qty
            
    cash_stats = db.query(
        m.CashEntry.employee_id,
        func.coalesce(func.sum(m.CashEntry.amount), 0).label("amount")
    ).group_by(m.CashEntry.employee_id).all()
    taken_map = {row.employee_id: row.amount for row in cash_stats if row.employee_id}

    aq = db.query(m.Employee).filter(m.Employee.active.is_(True))
    if firm:
        aq = aq.filter(m.Employee.firm.in_([firm, ""]))
    for e in aq.all():
        total_earned = earned_map.get(e.id, Decimal(0))
        total_taken = taken_map.get(e.id, Decimal(0))
        qty_ok = qty_ok_map.get(e.id, 0)
        qty_bad = qty_bad_map.get(e.id, 0)
        
        total_qty = int(qty_ok) + int(qty_bad)
        per_employee.append({
            "id": e.id, "name": e.name, "position": e.position, "brigade": e.brigade,
            "boxes_ok": int(qty_ok), "boxes_bad": int(qty_bad),
            "brak_percent": round(int(qty_bad) / total_qty * 100, 1) if total_qty else 0,
            "earned_total": float(total_earned),   # kirdi (hisobiga yozildi)
            "taken_total": float(total_taken),     # chiqdi (avans+xarajat)
            "balance": float(Decimal(total_earned) - Decimal(total_taken)),
        })
    per_employee.sort(key=lambda x: -x["earned_total"])

    cur = months[-1] if months else {}
    return {
        "months": months,
        "per_employee": per_employee,
        "totals": {
            "fund_this_month": cur.get("earned", 0),
            "advances_this_month": cur.get("advances", 0),
            "expenses_this_month": cur.get("expenses", 0),
            "boxes_this_month": cur.get("boxes", 0),
            # 1 qutiga o'rtacha real ish haqi (unit-ekonomika uchun)
            "labor_per_box_fact": round(cur["earned"] / cur["boxes"], 2)
            if cur.get("boxes") else 0,
        },
    }
