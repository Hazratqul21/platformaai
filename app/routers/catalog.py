"""Kataloglar — bo'limlar, o'lchov birliklari, lavozimlar, materiallar,
xizmatlar, formulalar. Hammasi admin tomonidan sozlanadi."""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import get_user, require_roles
from .. import models as m

router = APIRouter(prefix="/api/catalog", tags=["Kataloglar"])
admin = require_roles("Rahbar", "Sklad mudiri")


# ---------------- Oddiy kataloglar: bo'lim / birlik / lavozim ----------------

class NameIn(BaseModel):
    name: str


def _simple_list(db, model):
    return [{"id": r.id, "name": r.name} for r in db.query(model).order_by(model.name).all()]


def _simple_add(db, model, name, user, label):
    name = name.strip()
    if not name:
        raise HTTPException(400, "Номи бўш бўлмасин")
    if db.query(model).filter(model.name == name).first():
        raise HTTPException(409, "Bunday nom allaqachon bor")
    r = model(name=name)
    db.add(r)
    db.add(m.AuditLog(who=user.name, action=f"{label} qo'shildi", detail=name))
    db.commit()
    return {"id": r.id, "name": r.name}


@router.get("/units")
def units(db: Session = Depends(get_db), user=Depends(get_user)):
    return _simple_list(db, m.Unit)


@router.post("/units")
def add_unit(d: NameIn, db: Session = Depends(get_db), user=Depends(admin)):
    return _simple_add(db, m.Unit, d.name, user, "O'lchov birligi")


@router.delete("/units/{uid}")
def del_unit(uid: int, db: Session = Depends(get_db), user=Depends(admin)):
    r = db.get(m.Unit, uid)
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}


@router.get("/positions")
def positions(db: Session = Depends(get_db), user=Depends(get_user)):
    return _simple_list(db, m.Position)


@router.post("/positions")
def add_position(d: NameIn, db: Session = Depends(get_db), user=Depends(require_roles("Rahbar", "Sex boshlig'i", "Buxgalter"))):
    return _simple_add(db, m.Position, d.name, user, "Lavozim")


@router.delete("/positions/{pid}")
def del_position(pid: int, db: Session = Depends(get_db), user=Depends(require_roles("Rahbar"))):
    r = db.get(m.Position, pid)
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}


@router.get("/categories")
def categories(db: Session = Depends(get_db), user=Depends(get_user)):
    return _simple_list(db, m.Category)


@router.post("/categories")
def add_category(d: NameIn, db: Session = Depends(get_db), user=Depends(admin)):
    return _simple_add(db, m.Category, d.name, user, "Bo'lim")


@router.delete("/categories/{cid}")
def del_category(cid: int, db: Session = Depends(get_db), user=Depends(require_roles("Rahbar"))):
    r = db.get(m.Category, cid)
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}


# ---------------- Materiallar katalogi ----------------

class MaterialIn(BaseModel):
    name: str
    category: str = "Qog'oz"
    marka: str = ""
    manufacturer: str = ""
    grammaj: str = ""
    unit: str = "kg"
    min_stock: float = 0


def material_out(mat: m.Material) -> dict:
    return {
        "id": mat.id, "name": mat.name, "category": mat.category, "marka": mat.marka,
        "manufacturer": mat.manufacturer, "grammaj": mat.grammaj, "unit": mat.unit,
        "last_price": float(mat.last_price), "stock_qty": float(mat.stock_qty),
        "min_stock": float(mat.min_stock), "active": mat.active,
        # ko'rsatish uchun: "Qog'oz · Силвер пак 140 гр"
        "display": f"{mat.category} · {mat.name}" + (f" {mat.grammaj}" if mat.grammaj else ""),
    }


@router.get("/materials")
def materials(category: str | None = None, db: Session = Depends(get_db), user=Depends(get_user)):
    q = db.query(m.Material).filter(m.Material.active.is_(True))
    if category:
        q = q.filter(m.Material.category == category)
    return [material_out(x) for x in q.order_by(m.Material.category, m.Material.name).all()]


@router.post("/materials")
def add_material(d: MaterialIn, db: Session = Depends(get_db), user=Depends(admin)):
    if not d.name.strip():
        raise HTTPException(400, "Материал номи бўш бўлмасин")
    mat = m.Material(
        name=d.name.strip(), category=d.category, marka=d.marka.strip(),
        manufacturer=d.manufacturer.strip(), grammaj=d.grammaj.strip(),
        unit=d.unit, min_stock=Decimal(str(d.min_stock)))
    db.add(mat)
    db.add(m.AuditLog(who=user.name, action="Material qo'shildi",
                      detail=f"{d.category} · {d.name}"))
    db.commit()
    return material_out(mat)


@router.put("/materials/{mid}")
def edit_material(mid: int, d: MaterialIn, db: Session = Depends(get_db), user=Depends(admin)):
    mat = db.get(m.Material, mid)
    if not mat:
        raise HTTPException(404, "Material topilmadi")
    mat.name = d.name.strip()
    mat.category = d.category
    mat.marka = d.marka.strip()
    mat.manufacturer = d.manufacturer.strip()
    mat.grammaj = d.grammaj.strip()
    mat.unit = d.unit
    mat.min_stock = Decimal(str(d.min_stock))
    db.commit()
    return material_out(mat)


@router.delete("/materials/{mid}")
def del_material(mid: int, db: Session = Depends(get_db), user=Depends(admin)):
    mat = db.get(m.Material, mid)
    if mat:
        mat.active = False  # o'chirmaymiz, arxivlaymiz (tarix saqlanadi)
        db.commit()
    return {"ok": True}


# ---------------- Xizmatlar katalogi ----------------

class ServiceIn(BaseModel):
    name: str
    price: float = 0
    unit: str = "m²"
    formula: str = "x*y*n"


def service_out(s: m.Service) -> dict:
    return {"id": s.id, "name": s.name, "price": float(s.price),
            "unit": s.unit, "formula": s.formula, "active": s.active}


@router.get("/services")
def services(db: Session = Depends(get_db), user=Depends(get_user)):
    return [service_out(x) for x in db.query(m.Service)
            .filter(m.Service.active.is_(True)).order_by(m.Service.name).all()]


@router.post("/services")
def add_service(d: ServiceIn, db: Session = Depends(get_db), user=Depends(require_roles("Rahbar"))):
    if not d.name.strip():
        raise HTTPException(400, "Xizmat nomi bo'sh bo'lmasin")
    s = m.Service(name=d.name.strip(), price=Decimal(str(d.price)),
                  unit=d.unit, formula=d.formula.strip() or "x*y*n")
    db.add(s)
    db.add(m.AuditLog(who=user.name, action="Xizmat qo'shildi", detail=d.name))
    db.commit()
    return service_out(s)


@router.put("/services/{sid}")
def edit_service(sid: int, d: ServiceIn, db: Session = Depends(get_db), user=Depends(require_roles("Rahbar"))):
    s = db.get(m.Service, sid)
    if not s:
        raise HTTPException(404, "Xizmat topilmadi")
    s.name = d.name.strip()
    s.price = Decimal(str(d.price))
    s.unit = d.unit
    s.formula = d.formula.strip() or "x*y*n"
    db.commit()
    return service_out(s)


@router.delete("/services/{sid}")
def del_service(sid: int, db: Session = Depends(get_db), user=Depends(require_roles("Rahbar"))):
    s = db.get(m.Service, sid)
    if s:
        s.active = False
        db.commit()
    return {"ok": True}


# ---------------- Formulalar (sozlanadigan) ----------------

class FormulaIn(BaseModel):
    name: str
    expression: str
    description: str = ""


def formula_out(fo: m.Formula) -> dict:
    return {"id": fo.id, "name": fo.name, "expression": fo.expression,
            "description": fo.description, "active": fo.active}


@router.get("/formulas")
def formulas(db: Session = Depends(get_db), user=Depends(get_user)):
    return [formula_out(x) for x in db.query(m.Formula).order_by(m.Formula.id).all()]


@router.put("/formulas/{fid}")
def edit_formula(fid: int, d: FormulaIn, db: Session = Depends(get_db), user=Depends(require_roles("Rahbar"))):
    fo = db.get(m.Formula, fid)
    if not fo:
        raise HTTPException(404, "Formula topilmadi")
    # xavfsizlik: faqat ruxsat etilgan belgilar
    from ..services import safe_formula_check
    if not safe_formula_check(d.expression):
        raise HTTPException(400, "Formulada faqat o'zgaruvchi, raqam va + - * / ( ) ishlatiladi")
    fo.expression = d.expression.strip()
    fo.description = d.description.strip()
    db.commit()
    return formula_out(fo)


@router.post("/formulas")
def add_formula(d: FormulaIn, db: Session = Depends(get_db), user=Depends(require_roles("Rahbar"))):
    from ..services import safe_formula_check
    if not safe_formula_check(d.expression):
        raise HTTPException(400, "Formula noto'g'ri")
    if db.query(m.Formula).filter(m.Formula.name == d.name.strip()).first():
        raise HTTPException(409, "Bunday formula bor")
    fo = m.Formula(name=d.name.strip(), expression=d.expression.strip(),
                   description=d.description.strip())
    db.add(fo)
    db.commit()
    return formula_out(fo)
