"""Yengil migratsiya — mavjud bazaga yetishmayotgan ustunlarni qo'shadi.

NEGA KERAK:
`Base.metadata.create_all()` faqat YANGI jadval yaratadi. Mavjud jadvalga
ustun qo'shilsa u indamay o'tkazib yuboradi va dastur ishga tushgandan keyin
"no such column" bilan yiqiladi. Alembic bu loyiha uchun og'irlik qiladi
(har mijozga alohida baza bo'ladi — 2-bosqich), shuning uchun mana shu
minimal, o'qish oson mexanizm.

QOIDA:
Har bosqichda ustun qo'shsangiz, uni MIGRATSIYALAR ro'yxatiga yozing.
Ro'yxat faqat O'SADI — yozilgan qator hech qachon o'zgartirilmaydi va
o'chirilmaydi, aks holda eski bazalar yangilanmay qoladi.

Bu yerda faqat USTUN QO'SHISH bor. Ustun o'chirish / nom almashtirish
ataylab qo'shilmagan: ular ma'lumot yo'qotadi va alohida, qo'lda yozilgan,
zaxira bilan bajariladigan ish. (1-bosqich 4-qadami aynan shunday bo'ladi.)
"""
import json
import logging

from sqlalchemy import inspect, text

log = logging.getLogger("gofra.migrate")

# (jadval, ustun, SQL turi + default)
#
# Default MAJBURIY: mavjud qatorlarga nima yozilishini aytadi. Aks holda
# eski qatorlarda NULL qoladi va kod `dict` kutgan joyda NULL topadi.
# Tur yozuvi ikkala bazaga ham to'g'ri kelishi kerak. Farqli joylari
# `_ddl_tur()` da tarjima qilinadi (PostgreSQL da JSON o'rniga JSONB va
# standart qiymatga aniq tur ko'rsatish shart: '{}'::jsonb).
MIGRATSIYALAR: list[tuple[str, str, str]] = [
    # 1-bosqich, 1-qadam: Order ga soha qatlami maydoni
    ("orders", "attributes", "JSON NOT NULL DEFAULT '{}'"),
    # Profil shablondan yangilanishi mumkinmi (foydalanuvchi tegmagan bo'lsa)
    ("soha_profillar", "ozgartirilgan", "BOOLEAN NOT NULL DEFAULT FALSE"),
    # QQS — stavka buyurtma paytida qotiriladi
    ("orders", "qqs_stavka", "NUMERIC(5,2) NOT NULL DEFAULT 0"),
    ("orders", "qqs_summa", "NUMERIC(18,2) NOT NULL DEFAULT 0"),
]


def _postgres(engine) -> bool:
    return engine.dialect.name == "postgresql"


def _ddl_tur(engine, tur: str) -> str:
    """Ustun turini bazaga mos yozuvga o'giradi.

    PostgreSQL da:
      JSON  -> JSONB  (indekslanadi, tezroq, taqqoslash mumkin)
      '{}'  -> '{}'::jsonb  (aniq tur ko'rsatilmasa «column has type
               jsonb but default expression has type text» xatosi)
    SQLite da o'zgarishsiz — u turlarga erkin qaraydi.
    """
    if not _postgres(engine):
        return tur
    return tur.replace("JSON", "JSONB").replace("'{}'", "'{}'::jsonb")


def run_migrations(engine) -> list[str]:
    """Yetishmayotgan ustunlarni qo'shadi. Qo'shilganlar ro'yxatini qaytaradi.

    Idempotent — necha marta chaqirilsa ham natija bir xil.
    """
    insp = inspect(engine)
    mavjud_jadvallar = set(insp.get_table_names())
    qoshildi: list[str] = []

    with engine.begin() as conn:
        for jadval, ustun, tur in MIGRATSIYALAR:
            if jadval not in mavjud_jadvallar:
                # Jadval hali yo'q — create_all uni to'liq, ustuni bilan
                # yaratadi. Migratsiya kerak emas.
                continue
            ustunlar = {c["name"] for c in insp.get_columns(jadval)}
            if ustun in ustunlar:
                continue
            conn.execute(text(f"ALTER TABLE {jadval} ADD COLUMN "
                              f"{ustun} {_ddl_tur(engine, tur)}"))
            qoshildi.append(f"{jadval}.{ustun}")
            log.info("Migratsiya: %s.%s ustuni qo'shildi", jadval, ustun)

    if not qoshildi:
        log.info("Migratsiya: baza allaqachon yangi — o'zgarish yo'q")
    return qoshildi


def jadvalni_qayta_qur(engine, jadval: str, modeldan) -> bool:
    """Jadvalni model ta'rifi bo'yicha QAYTA QURADI — ustun turini
    o'zgartirish yoki ustun o'chirish uchun.

    NEGA KERAK: SQLite da `ALTER TABLE ... ALTER COLUMN` yo'q.
    `qty` ni butun sondan kasrga o'tkazish (2.5 m³ beton) yoki karton
    ustunlarini o'chirish (1-bosqich 4-qadami) shusiz mumkin emas.

    Ishlash tartibi (SQLite qo'llanmasidagi xavfsiz usul):
      1. yangi nomdagi jadval model bo'yicha yaratiladi
      2. IKKALA jadvalda ham bor ustunlar ko'chiriladi
      3. eskisi o'chiriladi, yangisi nomlanadi
    Hammasi BITTA tranzaksiyada — yarim yo'lda uzilsa hech narsa
    o'zgarmaydi.

    `True` qaytadi — qayta qurildi; `False` — kerak bo'lmadi.
    """
    insp = inspect(engine)
    if jadval not in insp.get_table_names():
        return False

    bazadagi = [c["name"] for c in insp.get_columns(jadval)]
    modeldagi = [c.name for c in modeldan.__table__.columns]
    if bazadagi == modeldagi:
        # Ustunlar to'plami bir xil. Turini bu yerda solishtirmaymiz:
        # SQLite turlari erkin va noto'g'ri "farq bor" degan xulosa
        # keraksiz qayta qurishga olib kelardi. Tur o'zgarganda
        # chaqiruvchi `majbur=True` bilan chaqiradi.
        return False

    tashlanadi = [c for c in bazadagi if c not in modeldagi]

    if _postgres(engine):
        # PostgreSQL da jadvalni qayta qurish SHART EMAS — unda
        # `ALTER TABLE ... DROP COLUMN` bor va u chet el kalitlari,
        # indekslar, ketma-ketliklarni o'zi saqlaydi. Qayta qurish esa
        # ularni yo'qotardi. Yangi ustunlarni `run_migrations` qo'shadi.
        if not tashlanadi:
            return False
        with engine.begin() as conn:
            for ustun in tashlanadi:
                conn.execute(text(
                    f'ALTER TABLE "{jadval}" DROP COLUMN "{ustun}"'))
        log.info("Jadval tozalandi: %s (tashlandi: %s)",
                 jadval, ", ".join(tashlanadi))
        return True

    kochadi = [c for c in modeldagi if c in bazadagi]
    vaqtinchalik = f"{jadval}__yangi"

    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{vaqtinchalik}"'))
        eski_nom = modeldan.__table__.name
        try:
            modeldan.__table__.name = vaqtinchalik
            modeldan.__table__.create(conn)
        finally:
            modeldan.__table__.name = eski_nom
        ustunlar = ", ".join(f'"{c}"' for c in kochadi)
        conn.execute(text(f'INSERT INTO "{vaqtinchalik}" ({ustunlar}) '
                          f'SELECT {ustunlar} FROM "{jadval}"'))
        conn.execute(text(f'DROP TABLE "{jadval}"'))
        conn.execute(text(f'ALTER TABLE "{vaqtinchalik}" RENAME TO "{jadval}"'))

    log.info("Jadval qayta qurildi: %s (%d ustun ko'chdi%s)", jadval,
             len(kochadi),
             f", tashlandi: {', '.join(tashlanadi)}" if tashlanadi else "")
    return True


def profillarni_yukla(db) -> int:
    """`app/profiles/*.json` shablonlarini bazaga ko'chiradi.

    Shablon fayl — faqat BOSHLANG'ICH nusxa. Bazaga tushgach haqiqat
    bazada bo'ladi: foydalanuvchi (yoki AI agent) profilni o'zgartirsa,
    keyingi ishga tushishda fayl uni QAYTA YOZIB YUBORMASLIGI kerak.
    Shuning uchun faqat YO'Q profil qo'shiladi, mavjudiga tegilmaydi.

    Hech qaysi profil faol bo'lmasa — zaxira (karton) faollashtiriladi.
    Bu Rustam akaning tizimi ko'chganda xulq o'zgarmasligi uchun.
    """
    from . import models as m
    from .domain import shablonlar, retsept_ziddiyatlari, ZAXIRA_KALIT

    # Retseptlar bir-biriga zid emasmi — ishga tushishda bilinsin.
    # Aks holda xatoni faqat o'sha soha mijozi, ishlab chiqarish
    # bosqichida yiqilgandan keyin bilib qolardi.
    for ogoh in retsept_ziddiyatlari():
        log.warning("Retsept ziddiyati: %s", ogoh)

    bor = {p.kalit: p for p in db.query(m.SohaProfil).all()}
    qoshildi = yangilandi = 0
    for kalit, tarif in shablonlar().items():
        tarif_json = json.dumps(tarif, ensure_ascii=False)
        mavjud = bor.get(kalit)
        if mavjud is None:
            db.add(m.SohaProfil(kalit=kalit, nom=tarif.get("nom", kalit),
                                tarif_json=tarif_json, faol=False))
            qoshildi += 1
        elif not mavjud.ozgartirilgan and mavjud.tarif_json != tarif_json:
            # Foydalanuvchi tegmagan profil — dastur yangilanganda
            # shablondagi tuzatish (retsept, formula, chegara) unga ham
            # yetib borishi kerak. Tahrirlanganiga TEGILMAYDI.
            mavjud.nom = tarif.get("nom", kalit)
            mavjud.tarif_json = tarif_json
            yangilandi += 1

    if qoshildi or yangilandi:
        db.commit()
        log.info("Profil shabloni: %d ta qo'shildi, %d ta yangilandi",
                 qoshildi, yangilandi)

    if not db.query(m.SohaProfil).filter(m.SohaProfil.faol.is_(True)).first():
        zaxira = db.query(m.SohaProfil).filter(
            m.SohaProfil.kalit == ZAXIRA_KALIT).first()
        if zaxira:
            zaxira.faol = True
            db.commit()
            log.info("Faol profil belgilanmagan edi — '%s' yoqildi", ZAXIRA_KALIT)
    return qoshildi


def backfill_soha(db) -> int:
    """Eski buyurtmalarning `attributes` ini ustunlardan to'ldiradi.

    NEGA KERAK: 2-qadam faqat YANGI va TAHRIRLANGAN buyurtmalarni ikki
    joyga yozadi. Undan oldin yaratilganlarda `attributes` bo'sh `{}` bo'lib
    qoladi. 4-qadamda ustunlar o'chirilsa o'sha buyurtmalarning o'lchamlari
    butunlay yo'qolardi — qaytarib bo'lmaydigan ma'lumot yo'qotish.

    Idempotent: faqat BO'SH `attributes` to'ldiriladi. To'lgan yozuvga
    tegilmaydi — aks holda 4-qadamdan keyin (ustunlar yo'q paytda) bu
    funksiya to'g'ri ma'lumot ustiga bo'sh qiymat yozib yuborardi.
    """
    from . import models as m
    from .domain import soha_yoz

    orders = [o for o in db.query(m.Order).all() if not o.attributes]
    for o in orders:
        soha_yoz(o)
    if orders:
        db.commit()
        log.info("Backfill: %d buyurtmaning soha maydonlari to'ldirildi",
                 len(orders))
    return len(orders)
