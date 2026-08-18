"""AKKAUNT BAZASINI TAYYORLASH — noldan ishlaydigan bo'sh ERP bazasi.

Bir necha soniya oladigan ish: PostgreSQL da `CREATE DATABASE`, jadvallar,
migratsiya, 22 profil, admin foydalanuvchi. So'rov ICHIDA qilinmaydi —
fon vazifasi sifatida chaqiriladi, foydalanuvchi `Akkaunt.tayyorlik` ni
kuzatadi.

MUHIM FARQ — bu YANGI mijoz uchun BO'SH baza. `app/seed.py` dagi `seed()`
esa dev bazasiga Rustam akaning namuna ma'lumotini ham yuklaydi. Bu yerda
faqat: admin + kataloglar + profillar. Mijozning haqiqiy ma'lumoti yo'q —
u AI bilan yig'adi yoki qo'lda kiritadi.
"""
import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from .. import tenancy

log = logging.getLogger("platforma.tayyorlash")


def _postgresmi(url: str) -> bool:
    return url.startswith("postgresql") or url.startswith("postgres")


def baza_yarat(baza_nomi: str) -> bool:
    """PostgreSQL da `CREATE DATABASE`. SQLite da hech nima — fayl o'zi
    yaratiladi. Baza allaqachon bor bo'lsa `False` qaytaradi (xato emas).

    Ulanish `MIJOZ_DB_SHABLON` dan olinadi, lekin `CREATE DATABASE`
    ni maqsad bazada bajarib bo'lmaydi (u hali yo'q) — shuning uchun
    `MIJOZ_ADMIN_DB` (odatda `postgres`) ga ulanamiz.
    """
    url = tenancy.baza_url(baza_nomi)
    if not _postgresmi(url):
        return False        # SQLite: fayl birinchi ulanishda paydo bo'ladi

    admin_baza = os.getenv("MIJOZ_ADMIN_DB", "postgres")
    admin_url = make_url(url).set(database=admin_baza)
    # `AUTOCOMMIT` — `CREATE DATABASE` tranzaksiya ichida ishlamaydi.
    eng = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with eng.connect() as conn:
            bor = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": baza_nomi}).first()
            if bor:
                log.info("Baza allaqachon bor: %s", baza_nomi)
                return False
            # baza_nomi ichki manba (kod_tekshir dan o'tgan), lekin baribir
            # identifikatorni qo'shtirnoq bilan o'raymiz — SQL in'ektsiya yo'q.
            conn.execute(text(f'CREATE DATABASE "{baza_nomi}"'))
            log.info("Baza yaratildi: %s", baza_nomi)
            return True
    finally:
        eng.dispose()


def sxema_tayyorla(engine: Engine) -> None:
    """Jadvallar + migratsiya. Startup va yangi akkaunt uchun BIR XIL yo'l.

    `main.py` lifespan ham shu funksiyani chaqiradi — tayyorlash mantiqi
    ikki joyda takrorlanmasin (biri eskirmasin)."""
    from ..db import Base
    from .. import models as m
    from ..migrate import run_migrations, jadvalni_qayta_qur

    Base.metadata.create_all(engine)
    run_migrations(engine)
    jadvalni_qayta_qur(engine, "orders", m.Order)


def bazani_toldir(sess, admin_parol: str = "", admin_ism: str = "Boshqaruvchi",
                  profil_kaliti: str | None = None) -> None:
    """Bo'sh bazaga: 22 profil, kataloglar, admin.

    `seed()` dan farqi — namuna/demo ma'lumot YO'Q. Yangi mijoz o'z
    ma'lumotini o'zi kiritadi.
    """
    from .. import models as m, domain
    from ..migrate import profillarni_yukla
    from ..seed import seed_catalogs
    from ..auth import hash_pw

    profillarni_yukla(sess)

    # Bosh kitob: hisoblar rejasi va provodka qoidalari (BHMS №21)
    from ..hisob import xizmat as gl
    gl.yukla(sess)

    # Agar ro'yxatdan o'tishda soha tanlangan bo'lsa — o'shani faollashtir.
    if profil_kaliti:
        sess.query(m.SohaProfil).update({m.SohaProfil.faol: False})
        yozuv = (sess.query(m.SohaProfil)
                 .filter(m.SohaProfil.kalit == profil_kaliti).first())
        if yozuv:
            yozuv.faol = True
        sess.commit()

    domain.qayta_yukla(sess)

    if not sess.query(m.User).first():
        parol = (admin_parol or "").strip()
        sess.add(m.User(
            login="admin", password_hash=hash_pw(parol or "1234"),
            name=admin_ism, role="Rahbar",
            # Parol berilmagan bo'lsa — 1234 va majburiy almashtirish.
            parol_almashtirilsin=not parol))
        seed_catalogs(sess)
        sess.commit()


def akkaunt_tayyorla(baza_nomi: str, admin_parol: str = "",
                   admin_ism: str = "Boshqaruvchi",
                   profil_kaliti: str | None = None) -> None:
    """To'liq zanjir: baza + sxema + to'ldirish. Fon vazifasi chaqiradi.

    Idempotent: qayta chaqirilsa mavjud narsani buzmaydi (baza bor bo'lsa
    o'tkazadi, admin bor bo'lsa qo'shmaydi)."""
    baza_yarat(baza_nomi)
    engine = tenancy.akkaunt_engine(baza_nomi)
    sxema_tayyorla(engine)
    sess = tenancy.akkaunt_sessiya(baza_nomi)
    try:
        bazani_toldir(sess, admin_parol, admin_ism, profil_kaliti)
    finally:
        sess.close()
