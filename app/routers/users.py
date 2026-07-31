"""Foydalanuvchilar boshqaruvi — boshqaruvchi o'zi xodimlarga login yaratadi."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import hash_pw, require_roles
from .. import models as m

router = APIRouter(prefix="/api/users", tags=["Foydalanuvchilar"])

admin_only = require_roles("Rahbar")

# Xodimga berilishi mumkin bo'lgan huquq to'plamlari
ALLOWED_ROLES = ["Rahbar", "Menejer", "Sklad mudiri", "Sex boshlig'i", "Buxgalter"]


class UserIn(BaseModel):
    login: str
    password: str
    name: str
    role: str = "Menejer"


class PasswordIn(BaseModel):
    password: str


@router.get("")
def list_users(db: Session = Depends(get_db), user=Depends(admin_only)):
    return [{"id": u.id, "login": u.login, "name": u.name, "role": u.role,
             "is_me": u.id == user.id}
            for u in db.query(m.User).order_by(m.User.id).all()]


@router.post("")
def create_user(data: UserIn, db: Session = Depends(get_db), user=Depends(admin_only)):
    if data.role not in ALLOWED_ROLES:
        raise HTTPException(400, f"Huquq noto'g'ri. Ruxsat: {ALLOWED_ROLES}")
    if not data.login.strip() or len(data.password) < 4:
        raise HTTPException(400, "Login bo'sh bo'lmasin, parol kamida 4 belgi")
    if db.query(m.User).filter(m.User.login == data.login.strip()).first():
        raise HTTPException(409, "Bu login band")
    u = m.User(login=data.login.strip(), password_hash=hash_pw(data.password),
               name=data.name.strip() or data.login, role=data.role)
    db.add(u)
    db.add(m.AuditLog(who=user.name, action="Yangi foydalanuvchi",
                      detail=f"{u.login} · {u.role}"))
    db.commit()
    return {"id": u.id, "login": u.login}


@router.post("/{uid}/password")
def reset_password(uid: int, data: PasswordIn, db: Session = Depends(get_db),
                   user=Depends(admin_only)):
    u = db.get(m.User, uid)
    if not u:
        raise HTTPException(404, "Фойдаланувчи топилмади")
    if len(data.password) < 4:
        raise HTTPException(400, "Parol kamida 4 belgi")
    u.password_hash = hash_pw(data.password)
    db.add(m.AuditLog(who=user.name, action="Parol yangilandi", detail=u.login))
    db.commit()
    return {"ok": True}


@router.delete("/{uid}")
def delete_user(uid: int, db: Session = Depends(get_db), user=Depends(admin_only)):
    if uid == user.id:
        raise HTTPException(400, "O'zingizni o'chira olmaysiz")
    u = db.get(m.User, uid)
    if not u:
        raise HTTPException(404, "Фойдаланувчи топилмади")
    # o'chirilayotgan foydalanuvchining tokenlarini ham olib tashlaymiz
    db.query(m.AuthToken).filter(m.AuthToken.user_id == uid).delete()
    db.delete(u)
    db.add(m.AuditLog(who=user.name, action="Foydalanuvchi o'chirildi", detail=u.login))
    db.commit()
    return {"ok": True}
