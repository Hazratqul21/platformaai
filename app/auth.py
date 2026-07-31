import secrets
import time
from datetime import datetime, timedelta
import bcrypt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .db import get_db
from . import models as m

TOKEN_TTL_HOURS = 24 * 365  # 1 yil (Telegram WebApp dan chiqib ketmasligi uchun)

# --- Login urinishlarini cheklash (parol terib topishga qarshi) ---
# Server bitta jarayonda ishlaydi, shuning uchun oddiy xotira yetarli.
# Cheklov IP bo'yicha, LOGIN bo'yicha emas: aks holda begona odam admin
# loginini ataylab bloklab, egasini tizimga kirita olmay qo'yishi mumkin edi.
XATO_CHEGARA = 5          # shuncha xato urinishdan keyin bloklanadi
OYNA_SEK = 15 * 60        # shuncha vaqt ichidagi urinishlar sanaladi
_XATO_URINISH: dict[str, list[float]] = {}


def ip_kaliti(request) -> str:
    """Haqiqiy mijoz IP'si. nginx X-Forwarded-For / X-Real-IP uzatadi."""
    xff = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if xff:
        return xff
    return (request.headers.get("x-real-ip")
            or (request.client.host if request.client else "noma'lum"))


def _urinishlar(ip: str, hozir: float) -> list[float]:
    return [t for t in _XATO_URINISH.get(ip, []) if hozir - t < OYNA_SEK]


def login_cheklovini_tekshir(ip: str) -> None:
    """Chegara oshgan bo'lsa kirishga yo'l qo'ymaydi."""
    hozir = time.time()
    urinishlar = _urinishlar(ip, hozir)
    _XATO_URINISH[ip] = urinishlar
    if len(urinishlar) >= XATO_CHEGARA:
        qolgan = int(OYNA_SEK - (hozir - urinishlar[0])) // 60 + 1
        raise HTTPException(
            429, f"Кўп марта нотўғри уриниш бўлди. {qolgan} дақиқадан сўнг қайта уриниб кўринг.")


def _xato_urinish_qayd(ip: str) -> None:
    hozir = time.time()
    _XATO_URINISH.setdefault(ip, []).append(hozir)
    # xotira cheksiz o'smasin — eskirgan IP'lar tozalanadi
    if len(_XATO_URINISH) > 500:
        for k in [k for k, v in _XATO_URINISH.items() if not _urinishlar(k, hozir)]:
            _XATO_URINISH.pop(k, None)


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def login(db: Session, login_: str, password: str, ip: str = "") -> dict:
    if ip:
        login_cheklovini_tekshir(ip)
    user = db.query(m.User).filter(m.User.login == login_).first()
    if not user or not verify_pw(password, user.password_hash):
        if ip:
            _xato_urinish_qayd(ip)
        raise HTTPException(401, "Логин ёки пароль нотўғри")
    _XATO_URINISH.pop(ip, None)   # to'g'ri kirdi — hisob nolga tushadi
    # muddati o'tgan tokenlarni tozalaymiz (bazada shishmasin)
    db.query(m.AuthToken).filter(m.AuthToken.expires < datetime.utcnow()).delete()
    token = secrets.token_hex(24)
    db.add(m.AuthToken(token=token, user_id=user.id,
                       expires=datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS)))
    db.commit()
    return {"token": token, "name": user.name, "role": user.role, "login": user.login}


def logout(token: str, db: Session):
    db.query(m.AuthToken).filter(m.AuthToken.token == token).delete()
    db.commit()


def get_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> m.User:
    token = authorization.removeprefix("Bearer ").strip()
    row = db.get(m.AuthToken, token) if token else None
    if not row or row.expires < datetime.utcnow():
        if row:
            db.delete(row)
            db.commit()
        raise HTTPException(401, "Авторизация талаб қилинади")
    user = db.get(m.User, row.user_id)
    if not user:
        db.delete(row)
        db.commit()
        raise HTTPException(401, "Фойдаланувчи топилмади")
    return user


def require_roles(*roles):
    def dep(user: m.User = Depends(get_user)) -> m.User:
        if user.role not in roles and user.role != "Rahbar":
            raise HTTPException(403, f"Bu bo'lim faqat: {', '.join(roles)} uchun")
        return user
    return dep
