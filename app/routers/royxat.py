"""RO'YXATDAN O'TISH — yangi firma platformaga qo'shiladi.

Oqim (docs/A-IJARACHILIK.md §A.6):
  1. odam login/parol/firma beradi
  2. PlatformaUser + Firma yoziladi (boshqaruv bazasida)
  3. FON VAZIFASI firma bazasini tayyorlaydi (bir necha soniya)
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
from ..platforma.tayyorlash import firma_tayyorla

log = logging.getLogger("platforma.royxat")
router = APIRouter(prefix="/api/platforma", tags=["Ro'yxatdan o'tish"])


class RoyxatIn(BaseModel):
    login: str            # telefon yoki email
    parol: str
    firma_kod: str        # subdomen: mebelsex
    firma_nom: str
    inn: str = ""
    qqs_tolovchi: bool = False
    soha: str | None = None    # tanlangan profil kaliti (ixtiyoriy)


def _fon_tayyorla(firma_id: int, baza_nomi: str, parol: str,
                  ism: str, soha: str | None):
    """Fon vazifasi: baza yaratiladi va holat yangilanadi.

    Xato bo'lsa `Firma.tayyorlik = "xato"` — foydalanuvchi ko'radi va
    biz loglardan bilamiz. Yarim tayyor holat qolib ketmasin."""
    from ..platforma.db import BoshqaruvSession
    db = BoshqaruvSession()
    try:
        firma = db.get(pm.Firma, firma_id)
        try:
            firma_tayyorla(baza_nomi, admin_parol=parol, admin_ism=ism,
                           profil_kaliti=soha)
            firma.tayyorlik = "tayyor"
            firma.tayyorlik_izohi = ""
            px.audit(db, "baza_tayyorlandi", firma_id=firma_id)
        except Exception as e:            # noqa: BLE001 — holatni yozib qo'yamiz
            log.exception("Baza tayyorlanmadi: %s", baza_nomi)
            firma.tayyorlik = "xato"
            firma.tayyorlik_izohi = str(e)[:400]
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
        firma = px.firma_yarat(db, data.firma_kod, data.firma_nom,
                               inn=data.inn, qqs_tolovchi=data.qqs_tolovchi,
                               kim=login)
    except ValueError as e:
        raise HTTPException(400, str(e))

    user = pm.PlatformaUser(login=login, parol_hash=hash_pw(data.parol),
                            ism=data.firma_nom, firma_id=firma.id,
                            platforma_roli="egasi", tasdiqlangan=True)
    db.add(user)
    db.commit()

    # Baza tayyorlash — FON vazifasi. So'rov ichida qilinsa foydalanuvchi
    # bir necha soniya «osilib qolgan» ekranni ko'radi.
    fon.add_task(_fon_tayyorla, firma.id, firma.baza_nomi, data.parol,
                 data.firma_nom, data.soha)

    return {"firma_kod": firma.kod, "holat": firma.tayyorlik,
            "manzil": f"https://{firma.kod}.{_domen()}"}


def _domen() -> str:
    import os
    return os.getenv("ASOSIY_DOMEN", "innasoft.uz")


@router.get("/holat/{firma_kod}")
def holat(firma_kod: str, db: Session = Depends(boshqaruv_db)):
    firma = db.query(pm.Firma).filter(pm.Firma.kod == firma_kod.lower()).first()
    if not firma:
        raise HTTPException(404, "Firma topilmadi")
    return {"firma_kod": firma.kod, "nom": firma.nom,
            "tayyorlik": firma.tayyorlik, "izoh": firma.tayyorlik_izohi,
            "manzil": f"https://{firma.kod}.{_domen()}"}


class KirIn(BaseModel):
    login: str
    parol: str


@router.post("/kir")
def kir(data: KirIn, db: Session = Depends(boshqaruv_db)):
    """Platforma kabinetiga kirish (ERP kirishidan alohida).

    Bu — hisob-kitob, tarif, AI sarfi kabineti uchun. ERP ga kirish
    firma subdomenidagi mavjud `/api/auth/login` orqali."""
    login = (data.login or "").strip().lower()
    user = db.query(pm.PlatformaUser).filter(
        pm.PlatformaUser.login == login).first()
    if not user or not verify_pw(data.parol, user.parol_hash):
        raise HTTPException(400, "Login yoki parol xato")
    firma = db.get(pm.Firma, user.firma_id) if user.firma_id else None
    return {"login": user.login, "ism": user.ism,
            "firma_kod": firma.kod if firma else None,
            "tayyorlik": firma.tayyorlik if firma else None,
            "manzil": f"https://{firma.kod}.{_domen()}" if firma else None}
