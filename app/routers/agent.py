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
from ..auth import require_roles
from .. import models as m
from .. import agent as ai

router = APIRouter(prefix="/api/agent", tags=["AI agent"])


def _bloklarni_soddalashtir(xabarlar: list) -> list[dict]:
    """Suhbatni frontend ko'rsatadigan sodda ko'rinishga keltiradi.

    Bazadagi tarix Anthropic formatida (thinking/tool_use bloklari bilan).
    Foydalanuvchiga faqat matn va «nima qildim» izi kerak — xom bloklarni
    ko'rsatish uni chalkashtiradi.
    """
    chiqish = []
    for x in xabarlar:
        content = x.get("content")
        if isinstance(content, str):
            chiqish.append({"rol": x["role"], "matn": content})
            continue
        matn = "".join(b.get("text", "") for b in content
                       if isinstance(b, dict) and b.get("type") == "text")
        asboblar = [b.get("name") for b in content
                    if isinstance(b, dict) and b.get("type") == "tool_use"]
        if matn or asboblar:
            chiqish.append({"rol": x["role"], "matn": matn,
                            "asboblar": asboblar})
    return chiqish


@router.get("/holat")
def holat(user=Depends(require_roles("Rahbar"))):
    """Agent ishlashga tayyormi — kalit qo'yilganmi."""
    return {
        "tayyor": ai.kalit_bormi(),
        "model": ai.MODEL,
        "izoh": ("Tayyor" if ai.kalit_bormi() else
                 "ANTHROPIC_API_KEY qo'yilmagan — .env ga yozing"),
    }


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


@router.post("/xabar")
def xabar(data: XabarIn, db: Session = Depends(get_db),
          user=Depends(require_roles("Rahbar"))):
    """Agentga xabar yuboradi va javobini qaytaradi.

    Rol cheklovi ATAYLAB «Rahbar»: agent butun tizim konfiguratsiyasini
    o'zgartira oladi (profil almashtirish hamma ekranga ta'sir qiladi),
    shuning uchun uni menejer yoki sklad mudiri ochmasligi kerak.
    """
    if not ai.kalit_bormi():
        raise HTTPException(400, "ANTHROPIC_API_KEY qo'yilmagan — "
                                 ".env fayliga yozing va tizimni qayta yuklang")
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

    tarix.append({"role": "user", "content": matn})

    try:
        natija = ai.suhbat(db, tarix)
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
            "izlar": natija["izlar"]}
