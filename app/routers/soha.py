"""Soha profili — konstruktorning o'zagi.

Bu yerda mijozning biznes turi ko'riladi, almashtiriladi va yangisi
qo'shiladi. Muhimi: profil qo'shish uchun **kod yozilmaydi** — JSON
ta'rif yuboriladi, xolos. 4-bosqichda AI agent aynan shu endpointga
suhbatdan chiqargan ta'rifni yuboradi.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth import get_user, require_roles
from .. import models as m
from .. import domain

router = APIRouter(prefix="/api/soha", tags=["Soha profili"])


def _chiqar(p: m.SohaProfil) -> dict:
    tarif = json.loads(p.tarif_json)
    return {
        "kalit": p.kalit, "nom": p.nom, "faol": p.faol,
        "izoh": tarif.get("izoh", ""),
        "maydonlar": tarif.get("maydonlar", []),
        "narx_usuli": tarif.get("narx", {}).get("usul", "qolda"),
    }


@router.get("/profillar")
def profillar(db: Session = Depends(get_db), user=Depends(get_user)):
    """Bazadagi hamma profil. Faoli `faol: true` bilan belgilangan."""
    return [_chiqar(p) for p in db.query(m.SohaProfil).order_by(m.SohaProfil.id)]


@router.get("/joriy")
def joriy(user=Depends(get_user)):
    """Hozir ishlayotgan profil — maydonlari bilan.

    Frontend shu ro'yxatdan buyurtma formasini yasashi mumkin: qaysi
    maydon, qanday turda, qanday variantlar. Shunda forma ham sohaga
    moslashadi va karton maydonlari kodda qotib qolmaydi.
    """
    p = domain.profil()
    return {
        "kalit": p.kalit, "nom": p.nom, "izoh": p.izoh,
        "narx_usuli": p.narx.get("usul", "qolda"),
        "xomashyo_hisobi": bool(p.xomashyo),
        # Retsept (BOM): 1 buyurtmaga qaysi material qancha ketadi.
        # Frontend shundan «ishlab chiqarishga yetadimi» ni ko'rsatishi mumkin.
        "retsept": p.retsept,
        "modul": {"kalit": p.modul.kalit, "nom": p.modul.nom, "izoh": p.modul.izoh},
        # Statuslar ham shu yerda: frontend treker bosqichlarini qattiq
        # yozmasdan, ish tartibidan chizishi kerak.
        "statuslar": [{"nom": st.nom, "mano": st.mano,
                       "keyingi": st.keyingi, "rollar": st.rollar}
                      for st in p.modul.statuslar],
        "maydonlar": [{
            "kalit": md.kalit, "nom": md.nom, "tur": md.tur,
            "birlik": md.birlik, "standart": md.standart,
            "min": md.min, "max": md.max, "variantlar": md.variantlar,
            "majburiy": md.majburiy, "hisoblanadi": md.hisoblanadi,
        } for md in p.maydonlar],
    }


class FaollashtirishIn(BaseModel):
    kalit: str


@router.post("/faollashtirish")
def faollashtirish(data: FaollashtirishIn, db: Session = Depends(get_db),
                   user=Depends(require_roles("Rahbar"))):
    """Faol profilni almashtiradi.

    DIQQAT: mavjud buyurtmalarning `attributes` i ESKI profil maydonlari
    bilan yozilgan — ular yangi profilda ko'rinmay qoladi (o'chmaydi,
    faqat ko'rsatilmaydi). Shuning uchun buyurtmalar bor bazada profil
    almashtirish real ish emas, sozlash bosqichidagi amaldir.
    """
    yangi = db.query(m.SohaProfil).filter(m.SohaProfil.kalit == data.kalit).first()
    if not yangi:
        raise HTTPException(404, f"'{data.kalit}' profili topilmadi")
    for p in db.query(m.SohaProfil).all():
        p.faol = (p.id == yangi.id)
    db.add(m.AuditLog(who=user.name, action="Soha profili almashtirildi",
                      detail=f"{yangi.nom} ({yangi.kalit})"))
    db.commit()
    domain.qayta_yukla(db)
    return {"ok": True, "faol": _chiqar(yangi),
            "ogohlantirish": "Eski buyurtmalar oldingi profil maydonlari "
                             "bilan yozilgan — ular ko'rinmay qolishi mumkin"}


class ProfilIn(BaseModel):
    tarif: dict


@router.post("/profillar")
def profil_qosh(data: ProfilIn, db: Session = Depends(get_db),
                user=Depends(require_roles("Rahbar"))):
    """Yangi soha profili qo'shadi yoki mavjudini yangilaydi — KOD YOZMASDAN.

    Ta'rif tuzilishi `app/profiles/*.json` bilan bir xil. Yuborilgan
    ta'rif darrov tekshiriladi: buzuq profil bazaga tushmaydi.
    """
    try:
        tekshirilgan = domain.Profil(data.tarif)
    except (KeyError, ValueError, TypeError) as e:
        raise HTTPException(400, f"Profil ta'rifi noto'g'ri: {e}")

    mavjud = db.query(m.SohaProfil).filter(
        m.SohaProfil.kalit == tekshirilgan.kalit).first()
    tarif_json = json.dumps(data.tarif, ensure_ascii=False)
    if mavjud:
        mavjud.nom, mavjud.tarif_json = tekshirilgan.nom, tarif_json
        harakat = "Soha profili yangilandi"
    else:
        db.add(m.SohaProfil(kalit=tekshirilgan.kalit, nom=tekshirilgan.nom,
                            tarif_json=tarif_json, faol=False))
        harakat = "Soha profili qo'shildi"
    db.add(m.AuditLog(who=user.name, action=harakat, detail=tekshirilgan.kalit))
    db.commit()
    if mavjud and mavjud.faol:
        domain.qayta_yukla(db)   # faol profil o'zgardi — keshni yangilaymiz
    return {"ok": True, "kalit": tekshirilgan.kalit,
            "maydonlar": len(tekshirilgan.maydonlar)}
