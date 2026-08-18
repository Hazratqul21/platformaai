"""PLATFORMA AUTENTIFIKATSIYASI — kabinet va admin uchun.

Bu ERP autentifikatsiyasidan (`app/auth.py`) ALOHIDA:
- ERP token: mijoz bazasidagi `auth_tokens`, subdomen ichida ishlaydi
- Platforma token: BOSHQARUV bazasidagi `platforma_tokenlar`, hisob
  kabineti (tarif, AI sarfi) va admin paneli uchun

Nega ikkitasi: kabinet subdomengacha, ya'ni akkaunt bazasi tayyor
bo'lishidan OLDIN kerak bo'ladi. ERP token esa akkaunt bazasi ichida.
"""
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import models as pm
from .db import boshqaruv_db

TOKEN_KUN = 30


def token_yarat(db: Session, user: pm.PlatformaUser) -> str:
    """Platforma tokeni yaratadi (kabinetga kirish)."""
    db.query(pm.PlatformaToken).filter(
        pm.PlatformaToken.tugaydi < datetime.utcnow()).delete()
    token = secrets.token_hex(24)
    db.add(pm.PlatformaToken(token=token, user_id=user.id,
                             akkaunt_id=user.akkaunt_id,
                             tugaydi=datetime.utcnow() + timedelta(days=TOKEN_KUN)))
    db.commit()
    return token


def joriy_user(authorization: str = Header(default=""),
               db: Session = Depends(boshqaruv_db)) -> pm.PlatformaUser:
    """Platforma tokenidan foydalanuvchini oladi. `Depends` uchun."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Kirish talab qilinadi")
    yozuv = db.get(pm.PlatformaToken, token)
    if not yozuv or yozuv.tugaydi < datetime.utcnow():
        raise HTTPException(401, "Sessiya tugagan — qayta kiring")
    user = db.get(pm.PlatformaUser, yozuv.user_id)
    if not user:
        raise HTTPException(401, "Foydalanuvchi topilmadi")
    return user


def joriy_admin(user: pm.PlatformaUser = Depends(joriy_user)) -> pm.PlatformaUser:
    """Faqat platforma admini (biz). Akkaunt egasi bu yerga kira olmaydi."""
    if user.platforma_roli != "admin":
        raise HTTPException(403, "Faqat platforma administratori uchun")
    return user
