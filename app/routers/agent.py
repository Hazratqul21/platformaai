"""AI agent bilan suhbat — konstruktorning foydalanuvchi yuzi.

Chat oynasi o'ng tomonda turadi: mijoz biznesini aytadi, agent savol
beradi va tizimni yig'adi. Agent kod yozmaydi — konfiguratsiya
to'ldiradi (app/agent.py ga qarang).
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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

    Rol tekshiruvi ASBOB DARAJASIDA: yordamchi bitta, lekin unga
    beriladigan asboblar foydalanuvchi roliga qarab filtrlanadi.
    """
    # BITTA yordamchi: eski kalitlar («moliya», «ombor»…) ham qabul
    # qilinadi va hammasi shunga olib boradi. Rol cheklovi endi ASBOB
    # darajasida (`ai.rolga_asboblar`) — sklad mudiri qarzdorlar
    # asbobini umuman ko'rmaydi.
    if not ai.rolga_asboblar(user.role):
        raise HTTPException(403, "Sizning rolingizga AI yordamchi ochiq emas")

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
        natija = ai.suhbat(db, tarix, data.agent,
                           getattr(user, "login", ""), user.role)
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


@router.post("/oqim")
def oqim(data: XabarIn, db: Session = Depends(get_db), user=Depends(get_user)):
    """Agent javobini QADAMMA-QADAM oqim qilib beradi (NDJSON).

    `/xabar` bilan bir xil ish qiladi, lekin javobni kutib o'tirmaydi:
    har qadam sodir bo'lishi bilan bitta JSON qatori yuboriladi.
    Foydalanuvchi «qarzdorlar chaqirilmoqda…» ni JONLI ko'radi.

    Nega SSE emas, NDJSON: SSE odatda GET bilan ishlaydi, bizga esa
    xabar matni kerak (POST). Oddiy qatorli oqimni brauzer
    `response.body.getReader()` bilan hech qanday kutubxonasiz o'qiydi.
    """
    # BITTA yordamchi: eski kalitlar («moliya», «ombor»…) ham qabul
    # qilinadi va hammasi shunga olib boradi. Rol cheklovi endi ASBOB
    # darajasida (`ai.rolga_asboblar`) — sklad mudiri qarzdorlar
    # asbobini umuman ko'rmaydi.
    if not ai.rolga_asboblar(user.role):
        raise HTTPException(403, "Sizning rolingizga AI yordamchi ochiq emas")
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
    suhbat_id = s.id

    def qatorlar():
        yield json.dumps({"tur": "boshlandi", "suhbat_id": suhbat_id},
                         ensure_ascii=False) + "\n"
        yakuniy = None
        try:
            for hodisa in ai.suhbat_oqim(db, tarix, data.agent,
                                        getattr(user, "login", ""),
                                        user.role):
                if hodisa.get("tur") == "yakun":
                    yakuniy = hodisa
                    # Xom tarixni mijozga bermaymiz — u katta va kerak emas
                    chiqish = {k: v for k, v in hodisa.items() if k != "xabarlar"}
                    chiqish["suhbat_id"] = suhbat_id
                    yield json.dumps(chiqish, ensure_ascii=False, default=str) + "\n"
                else:
                    yield json.dumps(hodisa, ensure_ascii=False) + "\n"
        except Exception as e:                          # noqa: BLE001
            # Suhbatni yo'qotmaymiz: foydalanuvchi xabari saqlanadi
            s.xabarlar_json = json.dumps(tarix, ensure_ascii=False, default=str)
            s.updated_at = datetime.utcnow()
            db.commit()
            yield json.dumps({"tur": "xato", "matn": str(e)},
                             ensure_ascii=False) + "\n"
            return
        if yakuniy is not None:
            s.xabarlar_json = json.dumps(yakuniy["xabarlar"],
                                         ensure_ascii=False, default=str)
            s.updated_at = datetime.utcnow()
            db.commit()

    return StreamingResponse(qatorlar(), media_type="application/x-ndjson",
                             # nginx oqimni buferlamasin — aks holda
                             # hamma qadam oxirida birdan keladi
                             headers={"X-Accel-Buffering": "no",
                                      "Cache-Control": "no-cache"})


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


# =====================================================================
# AGENT KO'RSATMASI (prompt) — mijoz o'zi tahrirlaydi
#
# Nega kerak: har biznesning o'z atamasi, o'z qoidasi bor. «Sklad
# mudiri» birida «omborchi», ikkinchisida «zaveduyushiy». Kod qayta
# joylanmasdan moslash imkoni bo'lishi kerak.
#
# XAVFSIZLIK: tahrirlanadigan qism faqat ROL ta'rifi. «Raqamni o'ylab
# topma», «asbob chaqir», GenUI shartnomasi — bular har doim qo'shiladi
# va o'chirib bo'lmaydi (`app/korsatma.py`).
# =====================================================================

class KorsatmaIn(BaseModel):
    korsatma: str


@router.get("/korsatma")
def korsatma_royxati(user=Depends(require_roles("Rahbar"))):
    """Hamma agentning joriy ko'rsatmasi va u qayerdan kelayotgani."""
    from .. import korsatma as kors
    natija = []
    for kalit, a in ai.AGENTLAR.items():
        joriy = (kors._akkaunt_sozlamasi(kalit)
                 or kors._platforma_shabloni(kalit)
                 or kors.kod_korsatmasi(kalit))
        natija.append({
            "kalit": kalit, "nom": a["nom"], "izoh": a["izoh"],
            "rollar": a["rollar"], "asboblar": a["asboblar"],
            "korsatma": joriy,
            "kod_korsatmasi": kors.kod_korsatmasi(kalit),
            "manba": kors.manba(kalit),
            "uzunlik": len(joriy), "chegara": kors.MAX_UZUNLIK,
        })
    return {"agentlar": natija,
            "xavfsizlik_qismi": ai._UMUMIY_USLUB.strip(),
            "izoh": ("Xavfsizlik qismi har doim qo'shiladi va tahrirlanmaydi — "
                     "AI raqam o'ylab topmasligi uchun.")}


@router.put("/korsatma/{kalit}")
def korsatma_saqla(kalit: str, data: KorsatmaIn,
                   db: Session = Depends(get_db),
                   user=Depends(require_roles("Rahbar"))):
    """Agent ko'rsatmasini o'zgartiradi (shu akkaunt uchun)."""
    from .. import korsatma as kors
    if kalit not in ai.AGENTLAR:
        raise HTTPException(404, "Bunday agent yo'q")
    try:
        matn = kors.tekshir(data.korsatma)
    except ValueError as e:
        raise HTTPException(400, str(e))

    yozuv = db.query(m.AgentSozlama).filter(m.AgentSozlama.kalit == kalit).first()
    if yozuv:
        yozuv.korsatma = matn
        yozuv.kim = user.name
        yozuv.ozgartirilgan = datetime.utcnow()
    else:
        db.add(m.AgentSozlama(kalit=kalit, korsatma=matn, kim=user.name))
    # AI o'zgarishi ham auditga tushadi — kim, qachon.
    db.add(m.AuditLog(who=user.name, action="AI ko'rsatmasi o'zgardi",
                      detail=f"{kalit} · {len(matn)} belgi"))
    db.commit()
    kors.keshni_tozala()
    return {"ok": True, "kalit": kalit, "uzunlik": len(matn), "manba": "akkaunt"}


@router.delete("/korsatma/{kalit}")
def korsatma_tikla(kalit: str, db: Session = Depends(get_db),
                   user=Depends(require_roles("Rahbar"))):
    """Standart ko'rsatmani qaytaradi (o'z o'zgarishini o'chiradi)."""
    from .. import korsatma as kors
    db.query(m.AgentSozlama).filter(m.AgentSozlama.kalit == kalit).delete()
    db.add(m.AuditLog(who=user.name, action="AI ko'rsatmasi tiklandi",
                      detail=kalit))
    db.commit()
    kors.keshni_tozala()
    return {"ok": True, "kalit": kalit, "manba": kors.manba(kalit)}
