"""AKKAUNT KABINETI — egasi o'z obunasi va AI sarfini ko'radi.

«AI xarajati mijozdan ALOHIDA» qarorining KO'RINADIGAN qismi
(docs/07-TARQATISH.md §7.6). Shaffoflik majburiy: tushuntirishsiz
kelgan hisob ishonchni yo'qotadi.

Platforma tokeni bilan ishlaydi (ERP tokeni emas) — boshqaruv bazasi
bilan. ERP ma'lumotiga tegmaydi.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..platforma import auth as pa, models as pm, xizmat as px
from ..platforma.db import boshqaruv_db

router = APIRouter(prefix="/api/kabinet", tags=["Akkaunt kabineti"])


def _pul(x) -> float:
    return float(Decimal(str(x)))


@router.get("/mening")
def mening(user: pm.PlatformaUser = Depends(pa.joriy_user),
           db: Session = Depends(boshqaruv_db)):
    """Akkaunt haqida umumiy ma'lumot: tarif, obuna, AI sarfi."""
    akkaunt = db.get(pm.Akkaunt, user.akkaunt_id) if user.akkaunt_id else None
    if not akkaunt:
        raise HTTPException(404, "Akkaunt topilmadi")
    limit = px.limit_holati(db, akkaunt.id)
    return {
        "akkaunt": {"kod": akkaunt.kod, "nom": akkaunt.nom,
                    "holat": akkaunt.holat, "tarif": akkaunt.tarif,
                    "obuna_tugaydi": akkaunt.obuna_tugaydi.isoformat()
                    if akkaunt.obuna_tugaydi else None,
                    "yozish_mumkinmi": akkaunt.yozish_mumkinmi},
        "ai": {"oy": limit["oy"], "sorov": limit["sorov"],
               "token": limit["token"], "som": _pul(limit["som"]),
               "limit_som": _pul(limit["limit_som"]),
               "foiz": limit["foiz"], "ogoh": limit["ogoh"],
               "toxtatilgan": limit["toxtatilsin"]},
    }


@router.get("/ai-sarf")
def ai_sarf(oy: str | None = None,
            user: pm.PlatformaUser = Depends(pa.joriy_user),
            db: Session = Depends(boshqaruv_db)):
    """AI sarfining tafsiloti: agent bo'yicha, foydalanuvchi bo'yicha.

    Shaffoflik uchun: «186 000 so'm» qayerdan kelganini ko'rsatadi."""
    if not user.akkaunt_id:
        raise HTTPException(404, "Akkaunt topilmadi")
    oy = oy or px.joriy_oy()
    umumiy = px.oylik_sarf(db, user.akkaunt_id, oy)

    from datetime import datetime
    from sqlalchemy import func
    boshi = datetime.strptime(oy + "-01", "%Y-%m-%d")
    keyingi = datetime(boshi.year + (boshi.month == 12),
                       1 if boshi.month == 12 else boshi.month + 1, 1)

    def guruh(ustun):
        q = (db.query(ustun, func.coalesce(func.sum(pm.AiSarf.narx_som), 0),
                      func.count(pm.AiSarf.id))
             .filter(pm.AiSarf.akkaunt_id == user.akkaunt_id,
                     pm.AiSarf.vaqt >= boshi, pm.AiSarf.vaqt < keyingi)
             .group_by(ustun).order_by(func.sum(pm.AiSarf.narx_som).desc()))
        return [{"nom": r[0] or "—", "som": _pul(r[1]), "sorov": int(r[2])}
                for r in q.all()]

    return {"oy": oy, "jami_som": _pul(umumiy["som"]),
            "jami_sorov": umumiy["sorov"], "jami_token": umumiy["token"],
            "agent_boyicha": guruh(pm.AiSarf.agent),
            "foydalanuvchi_boyicha": guruh(pm.AiSarf.user_login)}


class LimitIn(BaseModel):
    limit_som: float          # 0 = cheklovsiz


@router.post("/ai-limit")
def ai_limit(data: LimitIn,
             user: pm.PlatformaUser = Depends(pa.joriy_user),
             db: Session = Depends(boshqaruv_db)):
    """Oylik AI limitini o'rnatadi. Egasi o'zi qo'yadi.

    QOIDA: limit tugasa AI to'xtaydi, ERP ISHLAYVERADI."""
    if user.platforma_roli not in ("egasi", "admin"):
        raise HTTPException(403, "Faqat akkaunt egasi limit qo'yadi")
    if data.limit_som < 0:
        raise HTTPException(400, "Limit manfiy bo'la olmaydi")
    oy = px.joriy_oy()
    yozuv = (db.query(pm.AiLimit)
             .filter(pm.AiLimit.akkaunt_id == user.akkaunt_id,
                     pm.AiLimit.oy == oy).first())
    if yozuv:
        yozuv.limit_som = Decimal(str(data.limit_som))
        yozuv.ogoh_yuborildi = False
    else:
        db.add(pm.AiLimit(akkaunt_id=user.akkaunt_id, oy=oy,
                          limit_som=Decimal(str(data.limit_som))))
    px.audit(db, "ai_limit_ozgardi", akkaunt_id=user.akkaunt_id,
             kim=user.login, tafsilot=f"{data.limit_som} so'm")
    db.commit()
    return {"ok": True, "limit_som": data.limit_som, "oy": oy}


# =====================================================================
# OBUNA — ERP ICHIDA (akkaunt egasi uchun)
#
# NEGA ALOHIDA ROUTER: yuqoridagi `/api/kabinet/*` PLATFORMA tokenini
# talab qiladi (ro'yxatdan o'tish oqimi, subdomensiz). Lekin akkaunt
# egasi ERP ga o'z subdomenida ERP paroli bilan kirgan — undan yana
# ikkinchi login so'rash noto'g'ri bo'lardi.
#
# Bu router ERP tokeni bilan ishlaydi va JORIY akkauntning (subdomendan
# aniqlangan) obunasini ko'rsatadi. Ya'ni: karton.innasoft.uz da Rahbar
# bo'lib kirgan odam — o'sha akkauntning egasi.
# =====================================================================
from ..auth import require_roles                       # noqa: E402
from ..db import get_db                                 # noqa: E402

obuna_router = APIRouter(prefix="/api/obuna", tags=["Obuna (ERP ichida)"])


def _joriy_akkaunt(bdb: Session) -> pm.Akkaunt:
    """Subdomendan aniqlangan akkauntni boshqaruv bazasidan oladi."""
    from .. import tenancy
    a = tenancy.joriy() if tenancy.yoqilganmi() else None
    if not a:
        raise HTTPException(404, "Bu o'rnatmada obuna boshqaruvi yo'q "
                                 "(yagona rejim)")
    akk = bdb.get(pm.Akkaunt, a.id)
    if not akk:
        raise HTTPException(404, "Akkaunt topilmadi")
    return akk


@obuna_router.get("/mening")
def obuna_mening(_erp=Depends(get_db), user=Depends(require_roles("Rahbar")),
                 bdb: Session = Depends(boshqaruv_db)):
    akk = _joriy_akkaunt(bdb)
    limit = px.limit_holati(bdb, akk.id)
    return {
        "akkaunt": {"kod": akk.kod, "nom": akk.nom, "holat": akk.holat,
                    "tarif": akk.tarif,
                    "obuna_tugaydi": akk.obuna_tugaydi.isoformat()
                    if akk.obuna_tugaydi else None,
                    "yozish_mumkinmi": akk.yozish_mumkinmi,
                    "manzil": f"{akk.kod}.{_domen()}"},
        "ai": {"oy": limit["oy"], "sorov": limit["sorov"],
               "token": limit["token"], "som": _pul(limit["som"]),
               "limit_som": _pul(limit["limit_som"]), "foiz": limit["foiz"],
               "ogoh": limit["ogoh"], "toxtatilgan": limit["toxtatilsin"]},
    }


def _domen() -> str:
    import os
    return os.getenv("ASOSIY_DOMEN", "innasoft.uz")


@obuna_router.get("/ai-sarf")
def obuna_ai_sarf(oy: str | None = None, _erp=Depends(get_db),
                  user=Depends(require_roles("Rahbar")),
                  bdb: Session = Depends(boshqaruv_db)):
    """Tafsilot: agent va foydalanuvchi bo'yicha — shaffoflik uchun."""
    akk = _joriy_akkaunt(bdb)
    oy = oy or px.joriy_oy()
    umumiy = px.oylik_sarf(bdb, akk.id, oy)

    from datetime import datetime
    from sqlalchemy import func
    boshi = datetime.strptime(oy + "-01", "%Y-%m-%d")
    keyingi = datetime(boshi.year + (boshi.month == 12),
                       1 if boshi.month == 12 else boshi.month + 1, 1)

    def guruh(ustun):
        q = (bdb.query(ustun, func.coalesce(func.sum(pm.AiSarf.narx_som), 0),
                       func.count(pm.AiSarf.id))
             .filter(pm.AiSarf.akkaunt_id == akk.id,
                     pm.AiSarf.vaqt >= boshi, pm.AiSarf.vaqt < keyingi)
             .group_by(ustun).order_by(func.sum(pm.AiSarf.narx_som).desc()))
        return [{"nom": r[0] or "—", "som": _pul(r[1]), "sorov": int(r[2])}
                for r in q.all()]

    return {"oy": oy, "jami_som": _pul(umumiy["som"]),
            "jami_sorov": umumiy["sorov"], "jami_token": umumiy["token"],
            "agent_boyicha": guruh(pm.AiSarf.agent),
            "foydalanuvchi_boyicha": guruh(pm.AiSarf.user_login)}


@obuna_router.post("/ai-limit")
def obuna_ai_limit(data: LimitIn, _erp=Depends(get_db),
                   user=Depends(require_roles("Rahbar")),
                   bdb: Session = Depends(boshqaruv_db)):
    """Oylik AI limitini egasi o'zi qo'yadi.

    QOIDA: limit tugasa AI to'xtaydi, ERP ISHLAYVERADI."""
    if data.limit_som < 0:
        raise HTTPException(400, "Limit manfiy bo'la olmaydi")
    akk = _joriy_akkaunt(bdb)
    oy = px.joriy_oy()
    yozuv = (bdb.query(pm.AiLimit)
             .filter(pm.AiLimit.akkaunt_id == akk.id, pm.AiLimit.oy == oy).first())
    if yozuv:
        yozuv.limit_som = Decimal(str(data.limit_som))
        yozuv.ogoh_yuborildi = False
    else:
        bdb.add(pm.AiLimit(akkaunt_id=akk.id, oy=oy,
                           limit_som=Decimal(str(data.limit_som))))
    px.audit(bdb, "ai_limit_ozgardi", akkaunt_id=akk.id, kim=user.name,
             tafsilot=f"{data.limit_som} so'm (ERP ichidan)")
    bdb.commit()
    return {"ok": True, "limit_som": data.limit_som, "oy": oy}
