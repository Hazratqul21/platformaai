"""Baza ulanishi. PostgreSQL — asosiy; SQLite — faqat test/demo uchun.

NEGA POSTGRESQL:
SQLite bitta faylga yozadi va yozish paytida butun bazani qulflaydi.
Bir sexda 10 kishi bir vaqtda ishlaganda «database is locked» chiqadi.
Bundan tashqari platformada har mijozga ALOHIDA BAZA bo'ladi
(2-bosqich) — buni boshqarish, zaxiralash va tiklash PostgreSQL da
oddiy `CREATE DATABASE` / `pg_dump`, SQLite da esa fayl ko'chirish
bilan qo'lda qilinadi.

SQLite qoldirildi: testlar bir soniyada toza bazadan boshlashi kerak,
buning uchun u qulay. Kod ikkalasida ham ishlaydi.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

_default_db = Path(__file__).resolve().parent.parent / "gofra_erp.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_default_db}")

# `postgres://` — eski shakl, SQLAlchemy 2 uni tanimaydi. Ko'p hosting
# (Heroku, Railway) aynan shunday beradi, shuning uchun jimgina to'g'rilaymiz.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

SQLITE = DATABASE_URL.startswith("sqlite")

if SQLITE:
    # check_same_thread: FastAPI so'rovlarni boshqa oqimda bajaradi
    engine = create_engine(DATABASE_URL,
                           connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,          # bir vaqtda ochiq ulanishlar
        max_overflow=20,       # tig'iz paytda qo'shimcha
        pool_pre_ping=True,    # uzilgan ulanishni so'rovdan oldin tekshiradi
        pool_recycle=1800,     # 30 daqiqada yangilanadi (NAT/proxy uzmasin)
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """So'rov uchun sessiya.

    IJARACHILIK yoqilgan bo'lsa — so'rovga bog'langan MIJOZNING bazasi
    (`tenancy` contextvar dan). Aks holda — yagona baza, avvalgidek.

    125 endpointning hech biriga tegilmagani shu tufayli: hammasi
    `Depends(get_db)` ishlatadi, almashtirish faqat shu yerda.
    """
    from . import tenancy
    akkaunt = tenancy.joriy() if tenancy.yoqilganmi() else None
    db = tenancy.akkaunt_sessiya(akkaunt.baza_nomi) if akkaunt else SessionLocal()
    try:
        yield db
    finally:
        db.close()


def sessiya():
    """`Depends` siz kerak bo'lganda (fon vazifasi, vosita, test).

    Diqqat: fon vazifasi o'zi akkauntni `tenancy.ornat()` bilan
    belgilashi SHART — aks holda yagona bazaga yozadi."""
    from . import tenancy
    akkaunt = tenancy.joriy() if tenancy.yoqilganmi() else None
    return tenancy.akkaunt_sessiya(akkaunt.baza_nomi) if akkaunt else SessionLocal()
