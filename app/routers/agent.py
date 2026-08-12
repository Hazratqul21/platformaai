"""AI agent bilan suhbat — konstruktorning foydalanuvchi yuzi.

Chat oynasi o'ng tomonda turadi: mijoz biznesini aytadi, agent savol
beradi va tizimni yig'adi. Agent kod yozmaydi — konfiguratsiya
to'ldiradi (app/agent.py ga qarang).
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth import get_user, require_roles
from .. import models as m
from .. import agent as ai
from .. import genui
from .. import llm
from .. import services as svc

router = APIRouter(prefix="/api/agent", tags=["AI agent"])


def _bloklarni_soddalashtir(xabarlar: list) -> list[dict]:
    """Suhbatni frontend ko'rsatadigan sodda ko'rinishga keltiradi.

    Bazadagi tarix Anthropic formatida (thinking/tool_use bloklari bilan).
    Foydalanuvchiga faqat matn va «nima qildim» izi kerak — xom bloklarni
    ko'rsatish uni chalkashtiradi.
    """
    chiqish = []
    for x in xabarlar:
        asboblar = [c["nom"] for c in (x.get("asbob_chaqiruvlari") or [])]
        if x.get("matn") or asboblar:
            chiqish.append({"rol": x["rol"], "matn": x.get("matn", ""),
                            "asboblar": asboblar})
    return chiqish


@router.get("/holat")
def holat(user=Depends(get_user)):
    """Agent tayyormi, qaysi provayder, va shu rolga qaysi agentlar ochiq."""
    h = llm.holat()
    h["agentlar"] = ai.agent_royxati(user.role)
    return h


@router.get("/suhbatlar")
def suhbatlar(db: Session = Depends(get_db), user=Depends(require_roles("Rahbar"))):
    return [{"id": s.id, "sarlavha": s.sarlavha,
             "updated_at": s.updated_at.isoformat()}
            for s in db.query(m.AgentSuhbat)
                       .order_by(m.AgentSuhbat.updated_at.desc()).limit(50)]


@router.get("/suhbatlar/{sid}")
def suhbat_oqi(sid: int, db: Session = Depends(get_db),
               user=Depends(require_roles("Rahbar"))):
    s = db.get(m.AgentSuhbat, sid)
    if not s:
        raise HTTPException(404, "Suhbat topilmadi")
    return {"id": s.id, "sarlavha": s.sarlavha,
            "xabarlar": _bloklarni_soddalashtir(json.loads(s.xabarlar_json))}


class XabarIn(BaseModel):
    matn: str
    suhbat_id: int | None = None   # bo'sh bo'lsa yangi suhbat boshlanadi
    agent: str = "sozlash"         # qaysi bo'lim agenti


@router.post("/xabar")
def xabar(data: XabarIn, db: Session = Depends(get_db),
          user=Depends(get_user)):
    """Agentga xabar yuboradi va javobini qaytaradi.

    Rol tekshiruvi AGENT DARAJASIDA: sozlash agenti faqat Rahbarga
    (u profil almashtira oladi — hamma ekranga ta'sir qiladi), ombor
    agenti sklad mudiriga ham ochiq. Har agentning o'z ro'yxati bor.
    """
    a = ai.AGENTLAR.get(data.agent)
    if not a:
        raise HTTPException(404, f"'{data.agent}' — bunday yordamchi yo'q")
    if user.role not in a["rollar"]:
        raise HTTPException(403, f"«{a['nom']}» sizning rolingizga ochiq emas")

    tayyor, izoh = llm.tayyormi()
    if not tayyor:
        raise HTTPException(400, izoh)
    matn = (data.matn or "").strip()
    if not matn:
        raise HTTPException(400, "Xabar bo'sh")

    if data.suhbat_id:
        s = db.get(m.AgentSuhbat, data.suhbat_id)
        if not s:
            raise HTTPException(404, "Suhbat topilmadi")
        tarix = json.loads(s.xabarlar_json)
    else:
        s = m.AgentSuhbat(sarlavha=matn[:60], xabarlar_json="[]")
        db.add(s)
        db.flush()
        tarix = []

    tarix.append({"rol": "user", "matn": matn})

    try:
        natija = ai.suhbat(db, tarix, data.agent)
    except llm.LLMBand as e:
        # Vaqtinchalik band — 503 va tushunarli xabar. 502 «server buzuq»
        # degani, bu esa «keyinroq urinib ko'ring» degani.
        s.xabarlar_json = json.dumps(tarix, ensure_ascii=False, default=str)
        s.updated_at = datetime.utcnow()
        db.commit()
        raise HTTPException(503, str(e))
    except Exception as e:                                # noqa: BLE001
        # Suhbatni yo'qotmaymiz: foydalanuvchi xabari saqlanadi, shunda
        # u qaytadan yozmaydi va nima yuborilgani ko'rinib turadi.
        s.xabarlar_json = json.dumps(tarix, ensure_ascii=False, default=str)
        s.updated_at = datetime.utcnow()
        db.commit()
        raise HTTPException(502, f"Agentga ulanib bo'lmadi: {e}")

    s.xabarlar_json = json.dumps(natija["xabarlar"], ensure_ascii=False,
                                 default=str)
    s.updated_at = datetime.utcnow()
    db.commit()
    return {"suhbat_id": s.id, "javob": natija["javob"],
            "izlar": natija["izlar"],
            # GenUI: frontend shularni haqiqiy UI qilib chizadi
            "komponentlar": natija.get("komponentlar") or [],
            "provayder": natija.get("provayder"), "model": natija.get("model")}


class AmalIn(BaseModel):
    amal: str
    kirish: dict = {}


@router.post("/amal")
def amal(data: AmalIn, db: Session = Depends(get_db), user=Depends(get_user)):
    """Foydalanuvchi TASDIQLAGAN amalni bajaradi.

    Agentning o'zi hech qachon bazaga yozmaydi — u faqat `tasdiq`
    komponentini ko'rsatadi. Tugma bosilganda so'rov shu yerga keladi,
    ya'ni harakatni FOYDALANUVCHI boshlaydi va audit jurnaliga ham
    uning nomi yoziladi.

    Amal nomi `genui.AMALLAR` ro'yxatidan bo'lishi shart va rol yana
    shu yerda tekshiriladi — tasdiq komponenti ko'rsatilgan bo'lsa ham
    huquqi yo'q odam bajara olmaydi.
    """
    natija = genui.amalni_bajar(db, user, data.amal, data.kirish)
    if natija.get("xato"):
        raise HTTPException(400, natija["xato"])
    return natija


@router.get("/faoliyat")
def faoliyat(db: Session = Depends(get_db), user=Depends(get_user)):
    """AI NIMA QILDI — foydalanuvchi shuni ko'rib turishi kerak.

    «Hozir AI boshqaryaptimi?» degan savolga javob beradigan yagona
    joy. Ikki manba birlashtiriladi:

      1. Suhbatlar — qachon, qaysi yordamchi bilan gaplashilgan
      2. Audit jurnali — AI TAKLIF QILGAN va odam TASDIQLAGAN amallar

    Ikkinchisi muhimroq: agent o'zi hech narsa yozmaydi, lekin uning
    taklifi bilan bajarilgan har bir o'zgarish shu yerda ko'rinadi.
    """
    suhbatlar = (db.query(m.AgentSuhbat)
                 .order_by(m.AgentSuhbat.updated_at.desc()).limit(10).all())
    # AI ishtirokidagi yozuvlar audit jurnalida shu belgi bilan qoladi
    amallar = (db.query(m.AuditLog)
               .filter(m.AuditLog.detail.like("%AI taklifi%"))
               .order_by(m.AuditLog.id.desc()).limit(20).all())
    return {
        "holat": llm.holat(),
        "suhbatlar": [
            {"id": x.id, "sarlavha": x.sarlavha,
             "vaqt": svc.mahalliy_vaqt(x.updated_at).isoformat()}
            for x in suhbatlar],
        "amallar": [
            {"kim": a.who, "amal": a.action, "tafsilot": a.detail,
             "vaqt": svc.mahalliy_vaqt(a.at).isoformat()}
            for a in amallar],
    }


@router.get("/amallar")
def amallar(user=Depends(get_user)):
    """Shu rolga ochiq tasdiqlanadigan amallar — sozlamalar ekrani uchun."""
    return [{"kalit": k, "izoh": t["izoh"], "tugma": t["tugma"],
             "xavfli": bool(t.get("xavfli"))}
            for k, t in genui.AMALLAR.items()
            if user.role in t["rollar"] or user.role == "Rahbar"]
