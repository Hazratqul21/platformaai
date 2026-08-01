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
MIGRATSIYALAR: list[tuple[str, str, str]] = [
    # 1-bosqich, 1-qadam: Order ga soha qatlami maydoni
    ("orders", "attributes", "JSON NOT NULL DEFAULT '{}'"),
]


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
            conn.execute(text(f"ALTER TABLE {jadval} ADD COLUMN {ustun} {tur}"))
            qoshildi.append(f"{jadval}.{ustun}")
            log.info("Migratsiya: %s.%s ustuni qo'shildi", jadval, ustun)

    if not qoshildi:
        log.info("Migratsiya: baza allaqachon yangi — o'zgarish yo'q")
    return qoshildi


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
    from .domain import shablonlar, ZAXIRA_KALIT

    bor = {p.kalit for p in db.query(m.SohaProfil).all()}
    qoshildi = 0
    for kalit, tarif in shablonlar().items():
        if kalit in bor:
            continue
        db.add(m.SohaProfil(kalit=kalit, nom=tarif.get("nom", kalit),
                            tarif_json=json.dumps(tarif, ensure_ascii=False),
                            faol=False))
        qoshildi += 1

    if qoshildi:
        db.commit()
        log.info("Profil shabloni yuklandi: %d ta", qoshildi)

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
