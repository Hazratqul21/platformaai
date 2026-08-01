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
from .. import domain
from ..domain import soha_oqi
from .. import kassa_sync as ks

router = APIRouter(prefix="/api/warehouse", tags=["Ombor"])


class LotIn(BaseModel):
    supplier_id: int
    grade: str
    grammage: int = 120
    qty_kg: float
    price_per_kg: float
    lot_no: str = ""


@router.get("/raw")
def raw_stock(db: Session = Depends(get_db), user=Depends(get_user)):
    from sqlalchemy.orm import joinedload
    """Xomashyo ombori: marka+grammaj kesimida qoldiq va lotlar."""
    groups = {}
    # minusga o'tgan (qarz) qoldiqlar ham ko'rinadi — foydalanuvchi bilishi shart
    for lot in db.query(m.RawLot).options(joinedload(m.RawLot.supplier)).filter(m.RawLot.remaining_kg != 0).all():
        key = f"{lot.grade}|{lot.grammage}"
        g = groups.setdefault(key, {
            "grade": lot.grade, "grammage": lot.grammage, "stock_kg": 0.0,
            "value": 0.0, "lots": [],
        })
        rem = float(lot.remaining_kg)
        g["stock_kg"] += rem
        g["value"] += rem * float(lot.price_per_kg)
        g["lots"].append({
            "id": lot.id, "lot_no": lot.lot_no, "supplier": lot.supplier.name,
            "qty_kg": float(lot.qty_kg), "remaining_kg": rem,
            "price_per_kg": float(lot.price_per_kg),
            "received_at": lot.received_at.isoformat(),
        })
    return {"groups": list(groups.values()), "alerts": s.low_stock_alerts(db)}


@router.post("/raw")
def add_lot(data: LotIn, db: Session = Depends(get_db),
            user=Depends(require_roles("Sklad mudiri"))):
    grade = (data.grade or "").strip()
    if not grade:
        raise HTTPException(400, "Қоғоз маркаси бўш бўлмасин")
    if data.qty_kg <= 0 or data.price_per_kg <= 0:
        raise HTTPException(400, "Миқдор ва нарх 0 дан катта бўлсин")
    if not (1 <= data.grammage <= 2000):
        raise HTTPException(400, "Граммаж 1–2000 г/м² оралиғида бўлсин")
    sup = db.get(m.Supplier, data.supplier_id)
    if not sup:
        raise HTTPException(404, "Етказиб берувчи топилмади")
    lot = m.RawLot(
        lot_no=data.lot_no or "",
        supplier_id=sup.id, grade=grade, grammage=data.grammage,
        qty_kg=Decimal(str(data.qty_kg)), remaining_kg=Decimal(str(data.qty_kg)),
        price_per_kg=Decimal(str(data.price_per_kg)),
    )
    db.add(lot)
    db.commit()
    if not data.lot_no:
        lot.lot_no = f"LOT-{lot.id:04d}"
        db.commit()
    db.add(m.AuditLog(who=user.name, action="Xomashyo kirimi",
                      detail=f"{grade} {data.grammage}g · {data.qty_kg} kg · {sup.name}"))
    db.commit()
    return {"id": lot.id, "lot_no": lot.lot_no}


@router.get("/finished")
def finished_stock(db: Session = Depends(get_db), user=Depends(get_user)):
    """Tayyor mahsulot ombori = statusi 'Omborga tushdi' buyurtmalar."""
    rows = db.query(m.Order).filter(m.Order.status.in_(domain.statuslar("tayyor"))).all()
    return [{
        "order_id": o.id, "company": o.client.company,
        "size": domain.olcham_matni(o), "layers": soha_oqi(o, "layers"),
        "grade": soha_oqi(o, "grade"), "qty": o.qty, "total": float(o.total),
    } for o in rows]


@router.get("/moves")
def stock_moves(db: Session = Depends(get_db), user=Depends(get_user)):
    rows = (db.query(m.StockMove).order_by(m.StockMove.moved_at.desc()).limit(100).all())
    out = []
    for r in rows:
        lot = db.get(m.RawLot, r.lot_id)
        out.append({
            "id": r.id, "lot_no": lot.lot_no if lot else "?",
            "grade": lot.grade if lot else "?", "order_id": r.order_id,
            "kg": float(r.kg), "cost": float(r.cost),
            "moved_at": r.moved_at.isoformat(), "note": r.note,
        })
    return out


class InvIn(BaseModel):
    grade: str
    grammage: int = 120
    actual_kg: float
    note: str = ""


@router.post("/inventory")
def inventory_check(data: InvIn, db: Session = Depends(get_db),
                    user=Depends(require_roles("Sklad mudiri"))):
    """Oylik sanoq: tizim qoldig'i vs haqiqiy o'lchov, farq aktlashtiriladi (TZ 2.2)."""
    system = s.raw_stock_for(db, data.grade, data.grammage)
    diff = Decimal(str(data.actual_kg)) - system
    chk = m.InventoryCheck(
        grade=data.grade, grammage=data.grammage, system_kg=system, actual_kg=Decimal(str(data.actual_kg)),
        diff_kg=diff, note=data.note,
    )
    db.add(chk)
    # farq lotlarga tarqatiladi: kamomad FIFO dan yechiladi, ortiqcha oxirgi lotga qo'shiladi
    if diff < 0:
        try:
            # Note: fifo_writeoff in services uses m2! So we might need a kg-based writeoff. 
            # Or we skip inventory check for now as it's complex with M2/KG.
            # wait, if diff is in kg, we can just deduct directly from the last lot.
            last = (db.query(m.RawLot)
                    .filter(m.RawLot.grade == data.grade, m.RawLot.grammage == data.grammage)
                    .order_by(m.RawLot.received_at.desc()).first())
            if last:
                last.remaining_kg = Decimal(last.remaining_kg) + diff
        except Exception as e:
            raise HTTPException(409, str(e))
    elif diff > 0:
        last = (db.query(m.RawLot)
                .filter(m.RawLot.grade == data.grade, m.RawLot.grammage == data.grammage)
                .order_by(m.RawLot.received_at.desc()).first())
        if last:
            last.remaining_kg = Decimal(last.remaining_kg) + diff
    db.add(m.AuditLog(who=user.name, action="Inventarizatsiya",
                      detail=f"{data.grade}: tizim {float(system):.1f} kg, fakt {data.actual_kg} kg, farq {float(diff):+.1f} kg"))
    db.commit()
    return {"system_kg": float(system), "actual_kg": data.actual_kg, "diff_kg": float(diff)}


@router.get("/inventory")
def inventory_list(db: Session = Depends(get_db), user=Depends(get_user)):
    rows = db.query(m.InventoryCheck).order_by(m.InventoryCheck.checked_at.desc()).limit(50).all()
    return [{
        "id": r.id, "grade": r.grade, "system_kg": float(r.system_kg),
        "actual_kg": float(r.actual_kg), "diff_kg": float(r.diff_kg),
        "checked_at": r.checked_at.isoformat(), "note": r.note,
    } for r in rows]


@router.get("/suppliers")
def suppliers(db: Session = Depends(get_db), user=Depends(get_user)):
    out = []
    for sup in db.query(m.Supplier).all():
        bal = s.supplier_balance(db, sup.id)
        sched = (db.query(m.PaymentSchedule)
                 .filter(m.PaymentSchedule.supplier_id == sup.id, m.PaymentSchedule.paid.is_(False))
                 .order_by(m.PaymentSchedule.due_date).all())
        out.append({
            "id": sup.id, "name": sup.name, "phone": sup.phone,
            "kind": getattr(sup, "kind", None) or "Qog'oz",
            "got": float(bal["got"]), "paid": float(bal["paid"]), "debt": float(bal["debt"]),
            "avans": float(bal["avans"]),
            "schedule": [{"id": p.id, "due_date": p.due_date.isoformat(),
                          "amount": float(p.amount)} for p in sched],
        })
    return out


SUPPLIER_KINDS = ["Qog'oz", "Pechat", "Boshqa"]


class SupplierIn(BaseModel):
    name: str
    phone: str = ""
    kind: str = "Qog'oz"


@router.post("/suppliers")
def add_supplier(data: SupplierIn, db: Session = Depends(get_db),
                 user=Depends(require_roles("Sklad mudiri", "Buxgalter"))):
    if not data.name.strip():
        raise HTTPException(400, "Номи бўш бўлмасин")
    kind = data.kind if data.kind in SUPPLIER_KINDS else "Qog'oz"
    sup = m.Supplier(name=data.name.strip(), phone=data.phone.strip(), kind=kind)
    db.add(sup)
    db.add(m.AuditLog(who=user.name, action="Yangi yetkazib beruvchi",
                      detail=f"{sup.name} ({kind})"))
    db.commit()
    return {"id": sup.id, "name": sup.name}


@router.put("/suppliers/{sid}")
def edit_supplier(sid: int, data: SupplierIn, db: Session = Depends(get_db),
                  user=Depends(require_roles("Sklad mudiri", "Buxgalter"))):
    sup = db.get(m.Supplier, sid)
    if not sup:
        raise HTTPException(404, "Етказиб берувчи топилмади")
    if data.name.strip():
        sup.name = data.name.strip()
    sup.phone = data.phone.strip()
    if data.kind in SUPPLIER_KINDS:
        sup.kind = data.kind
    db.commit()
    return {"id": sup.id, "name": sup.name}


class SupPayIn(BaseModel):
    supplier_id: int
    amount: float
    note: str = ""
    schedule_id: int | None = None


@router.post("/suppliers/pay")
def pay_supplier(data: SupPayIn, db: Session = Depends(get_db),
                 user=Depends(require_roles("Buxgalter", "Sklad mudiri"))):
    """Yetkazib beruvchiga pul berish. Qarzdan ko'p berilsa — ortiqchasi avans
    bo'lib qoladi va keyingi moldan chegiriladi (bloklanmaydi)."""
    sup = db.get(m.Supplier, data.supplier_id)
    if not sup:
        raise HTTPException(404, "Етказиб берувчи топилмади")
    if data.amount <= 0:
        raise HTTPException(400, "Сумма 0 дан катта бўлсин")
    sp = m.SupplierPayment(supplier_id=sup.id, amount=Decimal(str(data.amount)), note=data.note)
    db.add(sp)
    db.flush()
    ks.yetkazib_beruvchiga_tolov(db, sp, user.name)
    if data.schedule_id:
        sch = db.get(m.PaymentSchedule, data.schedule_id)
        if sch:
            sch.paid = True
    db.add(m.AuditLog(who=user.name, action="Yetkazib beruvchiga to'lov",
                      detail=f"{sup.name} · {data.amount:,.0f} so'm".replace(",", " ")))
    db.commit()
    bal = s.supplier_balance(db, sup.id)
    return {"ok": True, "debt": float(bal["debt"]), "avans": float(bal["avans"]),
            "got": float(bal["got"]), "paid": float(bal["paid"])}


# =====================================================================
# UMUMIY OMBOR — istalgan material kirimi (retsept shundan yechadi)
#
# `POST /raw` faqat QOG'OZ uchun (grade + grammaj + kg). Bu esa un,
# LDSP, mato, metall, bo'yoq — hammasi uchun.
# =====================================================================

class MaterialLotIn(BaseModel):
    material: str                       # nomi (yo'q bo'lsa yaratiladi)
    qty: float                          # kirim miqdori
    price_per_unit: float               # so'm / birlik
    unit: str = "kg"                    # material birligi
    category: str = "Xomashyo"
    lot_no: str = ""
    supplier_id: int | None = None
    konversiya: dict | None = None      # {"m²": 0.12} — 1 m² = 0.12 kg


@router.post("/material-lot")
def add_material_lot(data: MaterialLotIn, db: Session = Depends(get_db),
                     user=Depends(require_roles("Sklad mudiri", "Buxgalter"))):
    """Materialni omborga kiritadi (partiya sifatida, FIFO uchun).

    Material nomi bo'yicha topiladi — kirill/lotin va katta-kichik harf
    farqiga qaramay. Topilmasa yangisi yaratiladi: ombor kartochkasini
    oldindan ochishga majburlash amalda ishlamaydi, sklad mudiri qog'ozni
    olib kelganda darrov kiritadi.
    """
    if data.qty <= 0:
        raise HTTPException(400, "Miqdor 0 dan katta bo'lsin")
    if data.price_per_unit < 0:
        raise HTTPException(400, "Narx manfiy bo'lmasin")

    mat = s.material_top(db, data.material)
    if mat is None:
        mat = m.Material(name=data.material.strip(), category=data.category,
                         unit=data.unit, stock_qty=Decimal("0"),
                         konversiya=data.konversiya or {})
        db.add(mat)
        db.flush()
    elif data.konversiya:
        # kelgan o'girish koeffitsientlari qo'shiladi (mavjudi o'chmaydi)
        yangi = dict(mat.konversiya or {})
        yangi.update({k: str(v) for k, v in data.konversiya.items()})
        mat.konversiya = yangi

    miqdor = Decimal(str(data.qty))
    lot = m.MaterialLot(
        material_id=mat.id, lot_no=data.lot_no or f"L{date.today():%y%m%d}",
        supplier_id=data.supplier_id, qty=miqdor, remaining=miqdor,
        price_per_unit=Decimal(str(data.price_per_unit)), received_at=date.today())
    db.add(lot)
    mat.stock_qty = Decimal(str(mat.stock_qty or 0)) + miqdor
    mat.last_price = Decimal(str(data.price_per_unit))
    db.add(m.AuditLog(who=user.name, action="Material kirimi",
                      detail=f"{mat.name}: {miqdor} {mat.unit} × "
                             f"{data.price_per_unit:,.0f} so'm"))
    db.commit()
    return {"ok": True, "material_id": mat.id, "lot_id": lot.id,
            "material": mat.name, "unit": mat.unit,
            "stock_qty": float(mat.stock_qty)}


@router.get("/materials")
def material_stock(db: Session = Depends(get_db), user=Depends(get_user)):
    """Umumiy ombor qoldig'i — partiyalari bilan."""
    natija = []
    for mat in db.query(m.Material).filter(m.Material.active.is_(True)).all():
        lots = (db.query(m.MaterialLot)
                .filter(m.MaterialLot.material_id == mat.id,
                        m.MaterialLot.remaining > 0)
                .order_by(m.MaterialLot.received_at, m.MaterialLot.id).all())
        natija.append({
            "id": mat.id, "name": mat.name, "unit": mat.unit,
            "category": mat.category, "stock_qty": float(mat.stock_qty or 0),
            "min_stock": float(mat.min_stock or 0),
            "konversiya": mat.konversiya or {},
            "lots": [{"lot_no": l.lot_no, "remaining": float(l.remaining),
                      "price_per_unit": float(l.price_per_unit),
                      "received_at": l.received_at.isoformat()} for l in lots],
        })
    return natija
