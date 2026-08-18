"""Boshqaruv bazasining ulanishi.

MIJOZ bazasidan ALOHIDA baza. `app/db.py` dagi `Base` bilan
aralashtirilmaydi — u yerda `Base.metadata.create_all(engine)` mijoz
bazasiga chaqiriladi, va agar boshqaruv jadvallari o'sha `Base` da
bo'lsa, ular HAR MIJOZNING bazasida yaratilardi.

Ya'ni bu ajratish qulaylik uchun emas — ma'lumot sizishining oldini
oladi.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_standart = Path(__file__).resolve().parent.parent.parent / "platforma_boshqaruv.db"
BOSHQARUV_URL = os.getenv("BOSHQARUV_DATABASE_URL", f"sqlite:///{_standart}")

if BOSHQARUV_URL.startswith("postgres://"):
    BOSHQARUV_URL = BOSHQARUV_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif BOSHQARUV_URL.startswith("postgresql://"):
    BOSHQARUV_URL = BOSHQARUV_URL.replace("postgresql://", "postgresql+psycopg://", 1)

_SQLITE = BOSHQARUV_URL.startswith("sqlite")

if _SQLITE:
    boshqaruv_engine = create_engine(BOSHQARUV_URL,
                                     connect_args={"check_same_thread": False})
else:
    # Bu baza har so'rovda o'qiladi (token, firma, limit), lekin yozuv kam.
    # Hovuz mijoz bazalarinikidan kattaroq — u yagona, ular ko'p.
    boshqaruv_engine = create_engine(BOSHQARUV_URL, pool_size=10,
                                     max_overflow=20, pool_pre_ping=True,
                                     pool_recycle=1800)

BoshqaruvSession = sessionmaker(bind=boshqaruv_engine, autoflush=False,
                                expire_on_commit=False)


class BoshqaruvBase(DeclarativeBase):
    """Mijoz bazasidagi `Base` dan ALOHIDA. Aralashtirilmaydi."""


def boshqaruv_db():
    """FastAPI `Depends` uchun."""
    db = BoshqaruvSession()
    try:
        yield db
    finally:
        db.close()


def jadvallarni_yarat() -> None:
    from . import models  # noqa: F401 — modellar ro'yxatga tushsin
    BoshqaruvBase.metadata.create_all(boshqaruv_engine)
    _admin_boshlangich()


def _admin_boshlangich() -> None:
    """Birinchi platforma admini muhit o'zgaruvchisidan yaratiladi.

    `PLATFORMA_ADMIN_LOGIN` + `PLATFORMA_ADMIN_PAROL` berilgan bo'lsa va
    hali admin yo'q bo'lsa — yaratiladi. Admin akkauntga TEGISHLI EMAS
    (u bizning xodim, tenant emas), shuning uchun `akkaunt_id=None`.

    Nega env: admin — biz, kod ichida parol yozib qo'yilmasin. Berilmasa
    admin yaratilmaydi (masalan sinovda kerak emas).
    """
    import os
    login = (os.getenv("PLATFORMA_ADMIN_LOGIN") or "").strip().lower()
    parol = os.getenv("PLATFORMA_ADMIN_PAROL") or ""
    if not login or len(parol) < 8:
        return
    from . import models as pm
    from ..auth import hash_pw
    db = BoshqaruvSession()
    try:
        bor = db.query(pm.PlatformaUser).filter(
            pm.PlatformaUser.platforma_roli == "admin").first()
        if bor:
            return
        db.add(pm.PlatformaUser(login=login, parol_hash=hash_pw(parol),
                                ism="Platforma admini", akkaunt_id=None,
                                platforma_roli="admin", tasdiqlangan=True))
        db.commit()
    finally:
        db.close()
