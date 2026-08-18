"""RO'YXATDAN O'TISH — yangi akkaunt platformaga qo'shiladi.

Oqim (docs/A-IJARACHILIK.md §A.6):
  1. odam login/parol/akkaunt beradi
  2. PlatformaUser + Akkaunt yoziladi (boshqaruv bazasida)
  3. FON VAZIFASI akkaunt bazasini tayyorlaydi (bir necha soniya)
  4. odam `/holat` ni kuzatadi: tayyorlanmoqda -> tayyor
  5. tayyor bo'lgach o'z subdomeniga kirib ishlaydi

Bu endpointlar boshqaruv bazasi bilan ishlaydi, MIJOZ bazasi bilan
emas — shuning uchun `get_db` EMAS, `boshqaruv_db` ishlatiladi.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import hash_pw, verify_pw
from ..platforma import models as pm, xizmat as px
from ..platforma.db import boshqaruv_db
from ..platforma.tayyorlash import akkaunt_tayyorla

log = logging.getLogger("platforma.royxat")
router = APIRouter(prefix="/api/platforma", tags=["Ro'yxatdan o'tish"])


class RoyxatIn(BaseModel):
    login: str            # telefon yoki email
    parol: str
    akkaunt_kod: str        # subdomen: mebelsex
    akkaunt_nom: str
    inn: str = ""
    qqs_tolovchi: bool = False
    soha: str | None = None    # tanlangan profil kaliti (ixtiyoriy)


def _fon_tayyorla(akkaunt_id: int, baza_nomi: str, parol: str,
                  ism: str, soha: str | None):
    """Fon vazifasi: baza yaratiladi va holat yangilanadi.

    Xato bo'lsa `Akkaunt.tayyorlik = "xato"` — foydalanuvchi ko'radi va
    biz loglardan bilamiz. Yarim tayyor holat qolib ketmasin."""
    from ..platforma.db import BoshqaruvSession
    db = BoshqaruvSession()
    try:
        akkaunt = db.get(pm.Akkaunt, akkaunt_id)
        try:
            akkaunt_tayyorla(baza_nomi, admin_parol=parol, admin_ism=ism,
                           profil_kaliti=soha)
            akkaunt.tayyorlik = "tayyor"
            akkaunt.tayyorlik_izohi = ""
            px.audit(db, "baza_tayyorlandi", akkaunt_id=akkaunt_id)
        except Exception as e:            # noqa: BLE001 — holatni yozib qo'yamiz
            log.exception("Baza tayyorlanmadi: %s", baza_nomi)
            akkaunt.tayyorlik = "xato"
            akkaunt.tayyorlik_izohi = str(e)[:400]
        db.commit()
    finally:
        db.close()


@router.post("/royxat")
def royxat(data: RoyxatIn, fon: BackgroundTasks,
           db: Session = Depends(boshqaruv_db)):
    login = (data.login or "").strip().lower()
    if len(login) < 5:
        raise HTTPException(400, "Login juda qisqa")
    if len((data.parol or "")) < 8:
        raise HTTPException(400, "Parol kamida 8 belgidan iborat bo'lsin")
    if db.query(pm.PlatformaUser).filter(pm.PlatformaUser.login == login).first():
        raise HTTPException(400, "Bu login allaqachon ro'yxatdan o'tgan")

    try:
        akkaunt = px.akkaunt_yarat(db, data.akkaunt_kod, data.akkaunt_nom,
                               inn=data.inn, qqs_tolovchi=data.qqs_tolovchi,
                               kim=login)
    except ValueError as e:
        raise HTTPException(400, str(e))

    user = pm.PlatformaUser(login=login, parol_hash=hash_pw(data.parol),
                            ism=data.akkaunt_nom, akkaunt_id=akkaunt.id,
                            platforma_roli="egasi", tasdiqlangan=True)
    db.add(user)
    db.commit()

    # Baza tayyorlash — FON vazifasi. So'rov ichida qilinsa foydalanuvchi
    # bir necha soniya «osilib qolgan» ekranni ko'radi.
    fon.add_task(_fon_tayyorla, akkaunt.id, akkaunt.baza_nomi, data.parol,
                 data.akkaunt_nom, data.soha)

    return {"akkaunt_kod": akkaunt.kod, "holat": akkaunt.tayyorlik,
            "manzil": f"https://{akkaunt.kod}.{_domen()}"}


def _domen() -> str:
    import os
    return os.getenv("ASOSIY_DOMEN", "innasoft.uz")


@router.get("/holat/{akkaunt_kod}")
def holat(akkaunt_kod: str, db: Session = Depends(boshqaruv_db)):
    akkaunt = db.query(pm.Akkaunt).filter(pm.Akkaunt.kod == akkaunt_kod.lower()).first()
    if not akkaunt:
        raise HTTPException(404, "Akkaunt topilmadi")
    return {"akkaunt_kod": akkaunt.kod, "nom": akkaunt.nom,
            "tayyorlik": akkaunt.tayyorlik, "izoh": akkaunt.tayyorlik_izohi,
            "manzil": f"https://{akkaunt.kod}.{_domen()}"}


class KirIn(BaseModel):
    login: str
    parol: str


@router.post("/kir")
def kir(data: KirIn, db: Session = Depends(boshqaruv_db)):
    """Platforma kabinetiga kirish (ERP kirishidan alohida).

    Bu — hisob-kitob, tarif, AI sarfi kabineti uchun. ERP ga kirish
    akkaunt subdomenidagi mavjud `/api/auth/login` orqali."""
    login = (data.login or "").strip().lower()
    user = db.query(pm.PlatformaUser).filter(
        pm.PlatformaUser.login == login).first()
    if not user or not verify_pw(data.parol, user.parol_hash):
        raise HTTPException(400, "Login yoki parol xato")
    akkaunt = db.get(pm.Akkaunt, user.akkaunt_id) if user.akkaunt_id else None
    return {"login": user.login, "ism": user.ism,
            "akkaunt_kod": akkaunt.kod if akkaunt else None,
            "tayyorlik": akkaunt.tayyorlik if akkaunt else None,
            "manzil": f"https://{akkaunt.kod}.{_domen()}" if akkaunt else None}
