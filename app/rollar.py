"""ROLLAR — mijoz o'z lavozim nomlarini ishlatadi.

MUAMMO. `models.ROLES` da beshta nom QOTIRILGAN: «Rahbar», «Menejer»,
«Sklad mudiri», «Sex boshlig'i», «Buxgalter». Bular karton sexining
lavozimlari. Bilyard klubida «Sex boshlig'i» yo'q — u yerda
«Administrator», «Barmen», «Kassir» ishlaydi.

Lekin rol shunchaki yorliq emas: `require_roles(...)` 24 dan ortiq
endpointda AYNAN shu nomlar bilan yozilgan, AI asboblari ham shu
nomlarga bog'langan. Nomlarni erkin o'zgartirsak butun ruxsat tizimi
qulaydi.

YECHIM — NOM va HUQUQ ajratiladi:

    «Barmen»  →  asos: «Menejer»      (Menejer nima qila olsa, shu)
    «Administrator» → asos: «Rahbar»

Mijoz O'Z NOMINI qo'yadi, huquq esa beshta ASOS dan biriga bog'lanadi.
Kodda hech narsa o'zgarmaydi: `require_roles("Menejer")` tekshiruvi
«Barmen» ni ham o'tkazadi, chunki uning asosi Menejer.

Yozuv bo'lmasa — beshta asos nomi o'zi ishlatiladi, ya'ni bugungi
xatti-harakat (karton, mebel va boshqalar tegilmaydi).
"""
import json
import logging

log = logging.getLogger("gofra.rollar")

SOZLAMA_KALITI = "rollar"

# HUQUQ ARXETIPLARI — kodda shu beshtasi bor va shu beshtasi qoladi.
# Mijoz yangi HUQUQ o'ylab topa olmaydi, faqat yangi NOM qo'ya oladi.
ASOSLAR = ["Rahbar", "Menejer", "Sklad mudiri", "Sex boshlig'i", "Buxgalter"]

# Rahbar — har doim hamma joyga kiradi (kodda ham shunday tekshiriladi).
ENG_YUQORI = "Rahbar"


def _xom(db) -> list[dict]:
    from . import models as m
    y = (db.query(m.Setting)
         .filter(m.Setting.key == SOZLAMA_KALITI).first())
    if not y or not y.value:
        return []
    try:
        tanlov = json.loads(y.value)
    except (ValueError, TypeError):
        log.warning("rollar sozlamasi buzuq — standart ishlatiladi")
        return []
    if not isinstance(tanlov, list):
        return []
    toza = []
    for x in tanlov:
        if not isinstance(x, dict):
            continue
        nom = (x.get("nom") or "").strip()
        asos = (x.get("asos") or "").strip()
        if nom and asos in ASOSLAR:
            toza.append({"nom": nom, "asos": asos})
    return toza


def royxat(db) -> list[dict]:
    """Shu akkauntda ishlatiladigan rollar: nomi va huquq asosi.

    Mijoz o'z rollarini belgilamagan bo'lsa — beshta asos qaytadi.
    """
    oz = _xom(db)
    if not oz:
        return [{"nom": a, "asos": a, "standart": True} for a in ASOSLAR]
    # Rahbar HAR DOIM bo'lishi kerak, aks holda akkauntni boshqarib
    # bo'lmaydi (foydalanuvchi qo'shish, sozlama — hammasi Rahbarda).
    if not any(x["asos"] == ENG_YUQORI for x in oz):
        oz.insert(0, {"nom": ENG_YUQORI, "asos": ENG_YUQORI})
    return [{**x, "standart": False} for x in oz]


def nomlar(db) -> list[str]:
    """Foydalanuvchi yaratishda tanlanadigan nomlar."""
    return [x["nom"] for x in royxat(db)]


def asos(db, rol: str) -> str:
    """Rol nomini HUQUQ asosiga aylantiradi.

    Nom topilmasa — o'zini qaytaradi. Shunda eski xatti-harakat
    saqlanadi va noma'lum rol hech qanday qo'shimcha huquq olmaydi.
    """
    rol = (rol or "").strip()
    if rol in ASOSLAR:
        return rol
    for x in royxat(db):
        if x["nom"] == rol:
            return x["asos"]
    return rol


def saqla(db, royxat_: list[dict]) -> list[dict]:
    """Akkauntning rol ro'yxatini yozadi."""
    from . import models as m
    toza, korilgan = [], set()
    for x in royxat_ or []:
        nom = (x.get("nom") or "").strip()
        a = (x.get("asos") or "").strip()
        if not nom or a not in ASOSLAR or nom.lower() in korilgan:
            continue
        korilgan.add(nom.lower())
        toza.append({"nom": nom[:30], "asos": a})
    if not any(x["asos"] == ENG_YUQORI for x in toza):
        toza.insert(0, {"nom": ENG_YUQORI, "asos": ENG_YUQORI})

    y = (db.query(m.Setting)
         .filter(m.Setting.key == SOZLAMA_KALITI).first())
    if y is None:
        y = m.Setting(key=SOZLAMA_KALITI, value="")
        db.add(y)
    y.value = json.dumps(toza, ensure_ascii=False)
    db.commit()
    return toza


def joriy_asos(db, user) -> str:
    """`user.role` ning huquq asosi — tekshiruvlarda shu ishlatiladi."""
    return asos(db, getattr(user, "role", "") or "")
