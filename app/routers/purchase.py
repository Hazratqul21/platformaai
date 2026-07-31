"""Zakup (Xarid) moduli — Master Excel'ning o'zi.
Material olish (kg/dona/rulon), naqd yoki qarzga, yetkazib beruvchi qarzi bilan."""
from datetime import date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import get_user, require_roles
from .. import models as m
from .. import kassa_sync as ks

router = APIRouter(prefix="/api/purchase", tags=["Xarid (Zakup)"])
buyer = require_roles("Rahbar", "Sklad mudiri", "Buxgalter")


class PurchaseIn(BaseModel):
    material_name: str
    supplier_id: int
    qty: float
    unit: str = "kg"
    fmt: str = ""
    unit_price: float
    payment_type: str = "Naqd"       # Naqd / Qarz / Keyinroq to'lash
    paid_amount: float | None = None  # qisman to'langan bo'lsa
    due_days: int = 30                # qarz muddati
    note: str = ""
    firm: str = ""


def purchase_out(db: Session, p: m.Purchase) -> dict:
    paid = Decimal(p.paid_amount) + Decimal(
        db.query(func.coalesce(func.sum(m.PurchasePayment.amount), 0))
        .filter(m.PurchasePayment.purchase_id == p.id).scalar())
    debt = Decimal(p.total) - paid
    mat = p.material
    return {
        "id": p.id, "material": mat.name if mat else "?",
        "category": mat.category if mat else "", "grammaj": mat.grammaj if mat else "",
        "supplier_id": p.supplier_id, "qty": float(p.qty), "unit": p.unit,
        "fmt": p.fmt, "unit_price": float(p.unit_price), "total": float(p.total),
        "payment_type": p.payment_type, "paid": float(paid), "debt": float(debt),
        "due_date": p.due_date.isoformat() if p.due_date else None,
        "purchased_at": p.purchased_at.isoformat(), "note": p.note,
    }


@router.get("")
def list_purchases(firm: str | None = None, db: Session = Depends(get_db), user=Depends(get_user)):
    q = db.query(m.Purchase)
    if firm:
        q = q.filter(m.Purchase.firm.in_([firm, ""]))
    rows = q.order_by(m.Purchase.purchased_at.desc(),
                      m.Purchase.id.desc()).limit(500).all()
    out = [purchase_out(db, p) for p in rows]
    total = sum(x["total"] for x in out)
    debt = sum(x["debt"] for x in out)
    return {"purchases": out, "total_bought": total, "total_debt": debt}


@router.post("")
def create_purchase(d: PurchaseIn, db: Session = Depends(get_db), user=Depends(buyer)):
    mat_name = d.material_name.strip()
    if not mat_name:
        raise HTTPException(400, "Материал номи бўш бўлмасин")
        
    # Auto-find or create material. SQLite ilike kirillni tushunmaydi —
    # Python'da katta/kichik harfga qaramay solishtiramiz (dublikat bo'lmasin)
    nom_l = mat_name.lower()
    mat = next((x for x in db.query(m.Material).all() if x.name.lower() == nom_l), None)
    if not mat:
        mat = m.Material(name=mat_name, category="Boshqa", unit=d.unit)
        db.add(mat)
        db.flush()

    sup = db.get(m.Supplier, d.supplier_id)
    if not sup:
        raise HTTPException(404, "Етказиб берувчи топилмади")
    if d.qty <= 0 or d.unit_price <= 0:
        raise HTTPException(400, "Миқдор ва нарх 0 дан катта бўлсин")
    if d.payment_type not in m.PAYMENT_TYPES:
        raise HTTPException(400, f"To'lov turi: {m.PAYMENT_TYPES}")

    total = (Decimal(str(d.qty)) * Decimal(str(d.unit_price))).quantize(Decimal("0.01"))
    if d.payment_type == "Naqd":
        paid = total
        due = None
    else:
        paid = Decimal(str(d.paid_amount)) if d.paid_amount else Decimal("0")
        if paid > total:
            raise HTTPException(400, "Тўланган сумма жами суммадан катта бўла олмайди")
        due = date.today() + timedelta(days=d.due_days)

    p = m.Purchase(
        material_id=mat.id, supplier_id=sup.id, qty=Decimal(str(d.qty)),
        unit=d.unit or mat.unit, fmt=d.fmt.strip(),
        unit_price=Decimal(str(d.unit_price)), total=total,
        payment_type=d.payment_type, paid_amount=paid, due_date=due, note=d.note,
        firm=d.firm)
    db.add(p)
    db.flush()
    # material qoldig'i oshadi + tarix
    mat.stock_qty = Decimal(mat.stock_qty) + Decimal(str(d.qty))
    mat.last_price = Decimal(str(d.unit_price))
    db.add(m.MaterialMove(material_id=mat.id, qty=Decimal(str(d.qty)),
                          reason=f"Xarid #{p.id}"))
    if paid > 0:
        ks.naqd_xarid(db, p, user.name)
    db.add(m.AuditLog(who=user.name, action="Xarid (zakup)",
                      detail=f"{mat.name} · {d.qty} {d.unit or mat.unit} · "
                             f"{float(total):,.0f} so'm · {d.payment_type}".replace(",", " ")))
    db.commit()
    return purchase_out(db, p)


class PurchaseEditIn(BaseModel):
    qty: float | None = None
    unit_price: float | None = None
    fmt: str | None = None
    note: str | None = None
    payment_type: str | None = None    # Naqd / Qarz / Keyinroq to'lash
    paid_amount: float | None = None   # xarid paytida to'langan summa


@router.put("/{pid}")
def edit_purchase(pid: int, d: PurchaseEditIn, db: Session = Depends(get_db), user=Depends(buyer)):
    """Xatolik ketsa xaridni tuzatish — material qoldig'i ham mos tuzatiladi."""
    p = db.get(m.Purchase, pid)
    if not p:
        raise HTTPException(404, "Харид топилмади")
    mat = p.material
    old_qty = Decimal(p.qty)
    if d.qty is not None:
        if d.qty <= 0:
            raise HTTPException(400, "Миқдор 0 дан катта бўлсин")
        diff = Decimal(str(d.qty)) - old_qty
        p.qty = Decimal(str(d.qty))
        if mat:
            mat.stock_qty = Decimal(mat.stock_qty) + diff
            db.add(m.MaterialMove(material_id=mat.id, qty=diff,
                                  reason=f"Xarid #{p.id} tuzatildi"))
    if d.unit_price is not None:
        if d.unit_price <= 0:
            raise HTTPException(400, "Нарх 0 дан катта бўлсин")
        p.unit_price = Decimal(str(d.unit_price))
        if mat:
            mat.last_price = Decimal(str(d.unit_price))
    if d.fmt is not None:
        p.fmt = d.fmt.strip()
    if d.note is not None:
        p.note = d.note.strip()
    if d.payment_type is not None:
        if d.payment_type not in m.PAYMENT_TYPES:
            raise HTTPException(400, f"To'lov turi: {m.PAYMENT_TYPES}")
        p.payment_type = d.payment_type
    p.total = (Decimal(p.qty) * Decimal(p.unit_price)).quantize(Decimal("0.01"))
    if d.paid_amount is not None:
        # qo'lda ko'rsatilgan to'lov (xatoni tuzatish uchun)
        if d.paid_amount < 0:
            raise HTTPException(400, "Тўланган сумма манфий бўлмасин")
        if d.paid_amount > float(p.total):
            raise HTTPException(400, "Xaridda to'langan summa jamidan katta bo'lmaydi. "
                                     "Ortiqcha pul bergan bo'lsangiz — uni Ombor > "
                                     "Yetkazib beruvchi > «Pul berish» orqali yozing (avans bo'lib qoladi).")
        p.paid_amount = Decimal(str(d.paid_amount))
    elif p.payment_type == "Naqd":
        # naqd xaridda to'langan summa yangi jamiga tenglashadi
        p.paid_amount = p.total
    if p.payment_type != "Naqd" and p.due_date is None:
        p.due_date = date.today() + timedelta(days=30)
    ks.naqd_xarid(db, p, user.name)
    db.add(m.AuditLog(who=user.name, action="Xarid tuzatildi",
                      detail=f"Xarid #{p.id} · {float(p.qty):g} x {float(p.unit_price):,.0f}".replace(",", " ")))
    db.commit()
    return purchase_out(db, p)


@router.delete("/{pid}")
def delete_purchase(pid: int, db: Session = Depends(get_db), user=Depends(require_roles("Rahbar"))):
    """Xato kiritilgan xaridni butunlay o'chirish — qoldiq qaytariladi."""
    p = db.get(m.Purchase, pid)
    if not p:
        raise HTTPException(404, "Харид топилмади")
    mat = p.material
    if mat:
        mat.stock_qty = Decimal(mat.stock_qty) - Decimal(p.qty)
    # xaridga bog'langan to'lovlarning kassa nusxasi ham ketadi
    for pp in db.query(m.PurchasePayment).filter(m.PurchasePayment.purchase_id == pid).all():
        ks.ochir(db, "purchase_payment", pp.id)
    ks.ochir(db, "purchase", pid)
    db.query(m.PurchasePayment).filter(m.PurchasePayment.purchase_id == pid).delete()
    db.query(m.MaterialMove).filter(m.MaterialMove.reason == f"Xarid #{pid}").delete()
    db.add(m.AuditLog(who=user.name, action="Xarid o'chirildi",
                      detail=f"Xarid #{pid} · {mat.name if mat else '?'} · {float(p.total):,.0f} so'm".replace(",", " ")))
    db.delete(p)
    db.commit()
    return {"ok": True}


class PayIn(BaseModel):
    purchase_id: int
    amount: float
    method: str = "Naqd"
    note: str = ""


@router.post("/pay")
def pay_purchase(d: PayIn, db: Session = Depends(get_db), user=Depends(buyer)):
    p = db.get(m.Purchase, d.purchase_id)
    if not p:
        raise HTTPException(404, "Харид топилмади")
    if d.amount <= 0:
        raise HTTPException(400, "Тўлов 0 дан катта бўлсин")
    pp = m.PurchasePayment(purchase_id=p.id, amount=Decimal(str(d.amount)),
                           method=d.method, note=d.note)
    db.add(pp)
    db.flush()
    ks.xarid_qarziga_tolov(db, pp, user.name)
    db.add(m.AuditLog(who=user.name, action="Xarid qarziga to'lov",
                      detail=f"Xarid #{p.id} · {d.amount:,.0f} so'm".replace(",", " ")))
    db.commit()
    return purchase_out(db, p)


@router.get("/debts")
def supplier_debts(db: Session = Depends(get_db), user=Depends(get_user)):
    """Yetkazib beruvchilar bo'yicha qarzlar (kreditor) — Master Excel qarz qismi."""
    out = {}
    for p in db.query(m.Purchase).filter(m.Purchase.payment_type != "Naqd").all():
        paid = Decimal(p.paid_amount) + Decimal(
            db.query(func.coalesce(func.sum(m.PurchasePayment.amount), 0))
            .filter(m.PurchasePayment.purchase_id == p.id).scalar())
        debt = Decimal(p.total) - paid
        if debt <= 0:
            continue
        sup = db.get(m.Supplier, p.supplier_id)
        g = out.setdefault(p.supplier_id, {
            "supplier_id": p.supplier_id, "supplier": sup.name if sup else "?",
            "debt": 0.0, "overdue": False, "items": []})
        g["debt"] += float(debt)
        overdue = p.due_date and p.due_date < date.today()
        if overdue:
            g["overdue"] = True
        g["items"].append({
            "purchase_id": p.id, "material": p.material.name if p.material else "?",
            "debt": float(debt), "due_date": p.due_date.isoformat() if p.due_date else None,
            "overdue": bool(overdue)})
    res = list(out.values())
    res.sort(key=lambda x: -x["debt"])
    return {"suppliers": res, "total_debt": sum(x["debt"] for x in res)}
