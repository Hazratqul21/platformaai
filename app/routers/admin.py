"""ADMIN PANELI — biz hamma akkauntni ko'ramiz va boshqaramiz.

FAQAT platforma admini uchun (`joriy_admin`). Akkaunt egasi bu yerga
kira olmaydi. Boshqaruv bazasi bilan ishlaydi.

Nima uchun kerak: 3-4 akkauntdan keyin qo'lda kuzatib bo'lmaydi —
qaysi biri muzlatilgan, qaysi biri AI ni ko'p sarflaydi, qaysi
birida xato. Bir joydan ko'rinishi kerak.
"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..platforma import auth as pa, models as pm, xizmat as px
from ..platforma.db import boshqaruv_db
from .. import tenancy

router = APIRouter(prefix="/api/admin", tags=["Admin panel"])


def _pul(x) -> float:
    return float(Decimal(str(x)))


@router.get("/akkauntlar")
def akkauntlar(_: pm.PlatformaUser = Depends(pa.joriy_admin),
               db: Session = Depends(boshqaruv_db)):
    """Hamma akkaunt: holat, tarif, tayyorlik, shu oygi AI sarfi."""
    oy = px.joriy_oy()
    natija = []
    for a in db.query(pm.Akkaunt).order_by(pm.Akkaunt.yaratilgan.desc()).all():
        sarf = px.oylik_sarf(db, a.id, oy)
        natija.append({
            "id": a.id, "kod": a.kod, "nom": a.nom, "holat": a.holat,
            "tarif": a.tarif, "tayyorlik": a.tayyorlik,
            "yaratilgan": a.yaratilgan.isoformat() if a.yaratilgan else None,
            "ai_som": _pul(sarf["som"]), "ai_sorov": sarf["sorov"]})
    return {"jami": len(natija), "akkauntlar": natija}


@router.get("/akkaunt/{akkaunt_id}")
def akkaunt(akkaunt_id: int, _: pm.PlatformaUser = Depends(pa.joriy_admin),
            db: Session = Depends(boshqaruv_db)):
    a = db.get(pm.Akkaunt, akkaunt_id)
    if not a:
        raise HTTPException(404, "Akkaunt topilmadi")
    limit = px.limit_holati(db, a.id)
    userlar = db.query(pm.PlatformaUser).filter(
        pm.PlatformaUser.akkaunt_id == a.id).all()
    return {
        "id": a.id, "kod": a.kod, "nom": a.nom, "inn": a.inn,
        "holat": a.holat, "tarif": a.tarif, "tayyorlik": a.tayyorlik,
        "tayyorlik_izohi": a.tayyorlik_izohi, "baza_nomi": a.baza_nomi,
        "obuna_tugaydi": a.obuna_tugaydi.isoformat() if a.obuna_tugaydi else None,
        "ai": {"som": _pul(limit["som"]), "limit_som": _pul(limit["limit_som"]),
               "foiz": limit["foiz"], "sorov": limit["sorov"]},
        "userlar": [{"login": u.login, "ism": u.ism, "roli": u.platforma_roli}
                    for u in userlar]}


class HolatIn(BaseModel):
    holat: str                # faol / muzlatilgan / ochirilgan
    sabab: str = ""


@router.post("/akkaunt/{akkaunt_id}/holat")
def holat_ozgartir(akkaunt_id: int, data: HolatIn,
                   admin: pm.PlatformaUser = Depends(pa.joriy_admin),
                   db: Session = Depends(boshqaruv_db)):
    """Akkauntni muzlatish/ochish/o'chirish.

    Muzlatilsa: YOZISH to'xtaydi, O'QISH ochiq qoladi (ma'lumot
    garovga olinmaydi). O'chirish — ma'lumotni o'chirmaydi, faqat
    kirishni yopadi (haqiqiy o'chirish alohida, ehtiyot bilan)."""
    if data.holat not in pm.HOLATLAR:
        raise HTTPException(400, f"Holat: {', '.join(pm.HOLATLAR)} dan biri")
    a = db.get(pm.Akkaunt, akkaunt_id)
    if not a:
        raise HTTPException(404, "Akkaunt topilmadi")
    eski = a.holat
    a.holat = data.holat
    px.audit(db, "holat_ozgardi", akkaunt_id=a.id, kim=admin.login,
             tafsilot=f"{eski} -> {data.holat}" + (f" ({data.sabab})" if data.sabab else ""))
    db.commit()
    # Firma keshini tozalaymiz — middleware yangi holatni darhol ko'rsin
    # (muzlatilgan akkaunt darhol yoza olmaydigan bo'lsin).
    tenancy.akkaunt_keshini_tozala(a.kod)
    return {"ok": True, "kod": a.kod, "holat": a.holat}


@router.get("/sarf")
def sarf(oy: str | None = None,
         _: pm.PlatformaUser = Depends(pa.joriy_admin),
         db: Session = Depends(boshqaruv_db)):
    """Platforma bo'yicha jami AI sarfi va eng ko'p sarflagan akkauntlar."""
    oy = oy or px.joriy_oy()
    boshi = datetime.strptime(oy + "-01", "%Y-%m-%d")
    keyingi = datetime(boshi.year + (boshi.month == 12),
                       1 if boshi.month == 12 else boshi.month + 1, 1)
    umumiy = (db.query(func.coalesce(func.sum(pm.AiSarf.narx_som), 0),
                       func.count(pm.AiSarf.id))
              .filter(pm.AiSarf.vaqt >= boshi, pm.AiSarf.vaqt < keyingi).one())
    # Akkaunt bo'yicha
    q = (db.query(pm.AiSarf.akkaunt_id,
                  func.coalesce(func.sum(pm.AiSarf.narx_som), 0),
                  func.count(pm.AiSarf.id))
         .filter(pm.AiSarf.vaqt >= boshi, pm.AiSarf.vaqt < keyingi)
         .group_by(pm.AiSarf.akkaunt_id)
         .order_by(func.sum(pm.AiSarf.narx_som).desc()).limit(20))
    akkauntlar = []
    for aid, som, n in q.all():
        a = db.get(pm.Akkaunt, aid)
        akkauntlar.append({"kod": a.kod if a else "?", "som": _pul(som),
                           "sorov": int(n)})
    return {"oy": oy, "jami_som": _pul(umumiy[0]), "jami_sorov": int(umumiy[1]),
            "akkauntlar": akkauntlar}


@router.get("/audit")
def audit(limit: int = 50, _: pm.PlatformaUser = Depends(pa.joriy_admin),
          db: Session = Depends(boshqaruv_db)):
    """Oxirgi platforma amallari: akkaunt yaratildi, muzlatildi, limit."""
    q = (db.query(pm.PlatformaAudit)
         .order_by(pm.PlatformaAudit.vaqt.desc()).limit(min(limit, 200)))
    return {"amallar": [
        {"vaqt": x.vaqt.isoformat() if x.vaqt else None, "amal": x.amal,
         "akkaunt_id": x.akkaunt_id, "kim": x.kim, "tafsilot": x.tafsilot}
        for x in q.all()]}
