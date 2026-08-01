from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import get_user, require_roles
from .. import models as m
from .. import services as s
from .. import domain
from ..domain import soha_oqi

router = APIRouter(prefix="/api/clients", tags=["CRM"])


class ClientIn(BaseModel):
    company: str
    contact: str = ""
    phone: str = ""
    inn: str = ""
    pay_type: str = "Naqd"
    category: str = "Yangi"
    credit_limit: float = 0
    blacklisted: bool = False
    firm: str = ""
    opening_balance: float = 0    # tizimdan oldingi qarz (manfiy — biz qarzdormiz)
    opening_date: str = ""        # "YYYY-MM-DD" (masalan 2026-07-01)


def _dekimal(k, v):
    return Decimal(str(v)) if k in ("credit_limit", "opening_balance") else v


def client_out(db: Session, c: m.Client) -> dict:
    bal = s.client_balance(db, c.id)
    return {
        "id": c.id, "company": c.company, "contact": c.contact, "phone": c.phone,
        "inn": c.inn, "pay_type": c.pay_type, "category": c.category,
        "credit_limit": float(c.credit_limit), "blacklisted": c.blacklisted, "firm": c.firm,
        "opening_balance": float(c.opening_balance or 0),
        "opening_date": c.opening_date.isoformat() if c.opening_date else None,
        "taken": float(bal["taken"]), "paid": float(bal["paid"]), "debt": float(bal["debt"]),
        "orders_count": len(c.orders),
    }


def _apply_client(c: m.Client, data: ClientIn):
    for k, v in data.model_dump().items():
        if k == "opening_date":
            c.opening_date = _parse_date(v)
        else:
            setattr(c, k, _dekimal(k, v))


def _parse_date(s: str):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


@router.get("")
def list_clients(firm: str | None = None, db: Session = Depends(get_db), user=Depends(get_user)):
    balances = s.client_balances_batch(db)
    res = []
    cq = db.query(m.Client)
    if firm:
        cq = cq.filter(m.Client.firm.in_([firm, ""]))
    for c in cq.order_by(m.Client.company).all():
        bal = balances.get(c.id, {"taken": Decimal(0), "paid": Decimal(0), "debt": Decimal(0)})
        res.append({
            "id": c.id, "company": c.company, "contact": c.contact, "phone": c.phone,
            "inn": c.inn, "pay_type": c.pay_type, "category": c.category,
            "credit_limit": float(c.credit_limit), "blacklisted": c.blacklisted, "firm": c.firm,
            "opening_balance": float(c.opening_balance or 0),
            "taken": float(bal["taken"]), "paid": float(bal["paid"]), "debt": float(bal["debt"]),
            "orders_count": len(c.orders),
        })
    return res


@router.post("")
def create_client(data: ClientIn, db: Session = Depends(get_db),
                  user=Depends(require_roles("Menejer"))):
    c = m.Client(company=data.company)
    _apply_client(c, data)
    db.add(c)
    db.add(m.AuditLog(who=user.name, action="Yangi mijoz", detail=data.company))
    db.commit()
    return client_out(db, c)


@router.put("/{cid}")
def update_client(cid: int, data: ClientIn, db: Session = Depends(get_db),
                  user=Depends(require_roles("Menejer", "Buxgalter"))):
    c = db.get(m.Client, cid)
    if not c:
        raise HTTPException(404, "Мижоз топилмади")
    _apply_client(c, data)
    db.commit()
    return client_out(db, c)


@router.get("/{cid}")
def get_client(cid: int, db: Session = Depends(get_db), user=Depends(get_user)):
    c = db.get(m.Client, cid)
    if not c:
        raise HTTPException(404, "Мижоз топилмади")
    out = client_out(db, c)
    out["orders"] = [{
        "id": o.id, "size": domain.olcham_matni(o, "x"),
        "product_name": o.product_name, "layers": soha_oqi(o, "layers"),
        "grade": soha_oqi(o, "grade"), "colors": soha_oqi(o, "colors"),
        "is_offset": soha_oqi(o, "is_offset"), "qty": o.qty,
        "unit_price": float(o.unit_price), "total": float(o.total), "status": o.status,
        "created_at": o.created_at.isoformat(),
        "due_date": o.due_date.isoformat() if o.due_date else None,
        "payment_due_date": o.payment_due_date.isoformat() if o.payment_due_date else None,
    } for o in sorted(c.orders, key=lambda o: o.created_at, reverse=True)]
    out["payments"] = [{
        "id": p.id, "amount": float(p.amount), "method": p.method,
        "paid_at": p.paid_at.isoformat(), "note": p.note, "order_id": p.order_id,
    } for p in sorted(c.payments, key=lambda p: p.paid_at, reverse=True)]
    return out


@router.get("/{cid}/detalizatsiya")
def client_detail_ledger(cid: int, db: Session = Depends(get_db), user=Depends(get_user)):
    """Mijoz detalizatsiyasi — Excel daftar ko'rinishi: chapda berilgan mollar,
    o'ngda kassa (kelgan pullar), pastida jami va qarz."""
    c = db.get(m.Client, cid)
    if not c:
        raise HTTPException(404, "Мижоз топилмади")

    # Faqat TOPSHIRILGAN mol qarzga kiradi (delivered_qty). Boshlang'ich qarz —
    # birinchi qator (tizimdan oldingi qarz).
    mollar = []
    if c.opening_balance and Decimal(c.opening_balance) != 0:
        mollar.append({
            "sana": c.opening_date.isoformat() if c.opening_date else "2026-07-01",
            "nakladnoy": "—",
            "mahsulot": "Бошланғич қарз (тизимдан олдин)",
            "olchov": "", "dona": "", "narxi": "",
            "jami": float(c.opening_balance),
            "status": "opening",
        })
    for o in sorted(c.orders, key=lambda o: o.created_at):
        berilgan = o.delivered_qty or 0
        if berilgan <= 0:      # topshirilmagan mol qarzga kirmaydi
            continue
        fmt = domain.olcham_matni(o, "x")
        qism = f" ({berilgan}/{o.qty})" if berilgan < o.qty else ""
        sana = o.delivered_at if o.delivered_at else o.created_at.date()
        mollar.append({
            "sana": sana.isoformat(),
            "nakladnoy": o.id,
            "mahsulot": (o.product_name or "") + qism,
            "olchov": f"{domain.tur_matni(o)} {fmt}",
            "dona": berilgan,
            "narxi": float(o.unit_price),
            "jami": float(Decimal(o.unit_price) * berilgan),
            "status": o.status,
        })

    kassa = [{
        "sana": p.paid_at.isoformat(),
        "summa": float(p.amount),
        "tolov_turi": p.method,
        "izoh": p.note,
    } for p in sorted(c.payments, key=lambda p: p.paid_at)]

    # topshirishga tayyor buyurtmalar (cex yoki omborda, hali to'liq berilmagan)
    tayyor = []
    for o in c.orders:
        if o.status in (m.ST_SEXDA, m.ST_OMBORDA):
            qolgan = o.qty - (o.delivered_qty or 0)
            if qolgan > 0:
                tayyor.append({
                    "id": o.id, "product_name": o.product_name,
                    "size": domain.olcham_matni(o, "x"),
                    "tur": domain.tur_matni(o),
                    "qolgan_qty": qolgan, "unit_price": float(o.unit_price),
                    "summa": float(Decimal(o.unit_price) * qolgan),
                    "status": o.status,
                })

    jami_mol = sum(Decimal(str(x["jami"])) for x in mollar)
    jami_tolov = sum(Decimal(str(x["summa"])) for x in kassa)
    return {
        "client_id": c.id, "company": c.company, "contact": c.contact,
        "phone": c.phone, "inn": c.inn,
        "mollar": mollar, "kassa": kassa, "tayyor": tayyor,
        "jami_mol": float(jami_mol),
        "jami_tolov": float(jami_tolov),
        "qarz": float(jami_mol - jami_tolov),
    }
