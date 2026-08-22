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


# =====================================================================
# AGENT SHABLONI — biz HAMMA akkauntga ko'rsatma beramiz
#
# Nega: AI ni yaxshilash uchun kod qayta joylanmasin. Prompt tuzatildi ->
# shu yerga yozamiz -> hamma akkaunt darhol yangisini oladi. Akkauntning
# o'z sozlamasi bo'lsa, u ustun turadi (mijoz tanlovi buzilmaydi).
# =====================================================================

class ShablonIn(BaseModel):
    korsatma: str


@router.get("/agent-shablon")
def agent_shablon(_: pm.PlatformaUser = Depends(pa.joriy_admin),
                  db: Session = Depends(boshqaruv_db)):
    from ..agent import AGENTLAR
    from .. import korsatma as kors
    bor = {x.kalit: x for x in db.query(pm.AgentShablon).all()}
    return {"agentlar": [{
        "kalit": k, "nom": a["nom"],
        "kod_korsatmasi": a["korsatma"],
        "platforma_korsatmasi": bor[k].korsatma if k in bor else None,
        "ozgartirilgan": bor[k].ozgartirilgan.isoformat() if k in bor else None,
        "kim": bor[k].kim if k in bor else None,
        "chegara": kors.MAX_UZUNLIK,
    } for k, a in AGENTLAR.items()]}


@router.put("/agent-shablon/{kalit}")
def agent_shablon_saqla(kalit: str, data: ShablonIn,
                        admin: pm.PlatformaUser = Depends(pa.joriy_admin),
                        db: Session = Depends(boshqaruv_db)):
    from ..agent import AGENTLAR
    from .. import korsatma as kors
    if kalit not in AGENTLAR:
        raise HTTPException(404, "Bunday agent yo'q")
    try:
        matn = kors.tekshir(data.korsatma)
    except ValueError as e:
        raise HTTPException(400, str(e))
    y = db.query(pm.AgentShablon).filter(pm.AgentShablon.kalit == kalit).first()
    if y:
        y.korsatma, y.kim = matn, admin.login
        y.ozgartirilgan = datetime.utcnow()
    else:
        db.add(pm.AgentShablon(kalit=kalit, korsatma=matn, kim=admin.login))
    px.audit(db, "agent_shabloni_ozgardi", kim=admin.login,
             tafsilot=f"{kalit} · {len(matn)} belgi")
    db.commit()
    # HAMMA akkauntning keshi tozalanadi — o'zgarish darhol kuchga kirsin.
    kors.keshni_tozala(hammasi=True)
    return {"ok": True, "kalit": kalit, "uzunlik": len(matn)}


@router.delete("/agent-shablon/{kalit}")
def agent_shablon_ochir(kalit: str,
                        admin: pm.PlatformaUser = Depends(pa.joriy_admin),
                        db: Session = Depends(boshqaruv_db)):
    """Platforma shablonini olib tashlaydi — koddagi zaxiraga qaytadi."""
    from .. import korsatma as kors
    db.query(pm.AgentShablon).filter(pm.AgentShablon.kalit == kalit).delete()
    px.audit(db, "agent_shabloni_ochirildi", kim=admin.login, tafsilot=kalit)
    db.commit()
    kors.keshni_tozala(hammasi=True)
    return {"ok": True, "kalit": kalit}

# ---------------------------------------------------------------------
# SOZLAMALAR — INN provayderi va boshqalar
# ---------------------------------------------------------------------
class SozlamaIn(BaseModel):
    qiymat: str = ""


def _sir_korinishi(qiymat: str) -> str:
    """Sir qiymatning faqat oxirgi 4 belgisi. Bot tokeni bilan bir naqsh.

    To'liq kalit API orqali QAYTARILMAYDI: admin panelini ochgan har
    kim (yoki brauzer kengaytmasi, yoki ekran yozuvi) uni ko'rib
    qolmasin. Kalitni kim yozgan bo'lsa, o'zida bor.
    """
    q = qiymat or ""
    return ("…" + q[-4:]) if len(q) > 4 else ("…" if q else "")


@router.get("/sozlamalar")
def sozlamalar(_: pm.PlatformaUser = Depends(pa.joriy_admin),
               db: Session = Depends(boshqaruv_db)):
    """Admin panelidan o'zgaradigan sozlamalar.

    Hozircha INN qidiruvi provayderi. Kalitning o'zi qaytarilmaydi —
    faqat qo'yilgan-qo'yilmagani va oxirgi 4 belgisi.
    """
    from ..platforma.inn import SOZLAMALAR as INN_KALITLAR
    tavsif = {
        "inn_provayder": ("Provayder", "ihamkor / maxsus / bo'sh = o'chirilgan", False),
        "inn_manzil": ("So'rov manzili", "{inn} o'rniga raqam qo'yiladi", False),
        "inn_kalit": ("API kaliti", "Sir — faqat oxirgi 4 belgisi ko'rinadi", True),
        "inn_sarlavha": ("Kalit sarlavhasi", "Masalan X-API-Key. Bo'sh = Authorization: Bearer", False),
    }
    bor = {x.kalit: x for x in db.query(pm.PlatformaSozlama).all()}
    chiqish = []
    for k in INN_KALITLAR:
        nom, izoh, sirmi = tavsif[k]
        y = bor.get(k)
        chiqish.append({
            "kalit": k, "nom": nom, "izoh": izoh, "sirmi": sirmi,
            "qoyilgan": bool(y and y.qiymat),
            "qiymat": (_sir_korinishi(y.qiymat) if sirmi else (y.qiymat if y else "")),
            "ozgartirilgan": y.ozgartirilgan.isoformat() if y else None,
            "kim": y.kim if y else None,
        })
    return {"sozlamalar": chiqish, "guruh": "INN qidiruvi"}


@router.put("/sozlama/{kalit}")
def sozlama_saqla(kalit: str, data: SozlamaIn,
                  admin: pm.PlatformaUser = Depends(pa.joriy_admin),
                  db: Session = Depends(boshqaruv_db)):
    from ..platforma.inn import SOZLAMALAR as INN_KALITLAR
    if kalit not in INN_KALITLAR:
        raise HTTPException(404, "Bunday sozlama yo'q")
    qiymat = (data.qiymat or "").strip()
    if kalit == "inn_manzil" and qiymat:
        if not qiymat.startswith(("http://", "https://")):
            raise HTTPException(400, "Manzil http:// yoki https:// bilan boshlansin")
        if "{inn}" not in qiymat:
            raise HTTPException(400, "Manzilda {inn} o'rni bo'lishi shart")
    px.sozlama_yoz(db, kalit, qiymat, sirmi=(kalit == "inn_kalit"),
                   kim=admin.login)
    px.audit(db, "sozlama_ozgardi", kim=admin.login, izoh=kalit)
    db.commit()
    return {"kalit": kalit, "qoyilgan": bool(qiymat)}
