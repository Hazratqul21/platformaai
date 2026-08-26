"""BO'LIMLAR — yon menyu MA'LUMOT, kod emas.

MUAMMO (foydalanuvchi ko'rsatdi). Yon menyu `static/js/core/router.js`
ichida QOTIRILGAN 15 ta bo'lim edi va u faqat ROLga qarab filtrlanardi.
Ya'ni har qanday biznes — bilyard klubi ham, non zavodi ham — Rustam
akaning karton sexi uchun yasalgan menyuni ko'rardi: «Ombor»,
«Materiallar», «Xomashyo xaridi».

Bu shunchaki ortiqcha bo'lim emas, ZIDDIYAT edi: `modules/xizmat.json`
ning o'zida «Ombor ishtirok etmaydi» deb yozilgan, lekin menyu buni
o'qimasdi. Tizim biladi, ekran esa bilmaydi.

YECHIM — uch qatlam, yuqoridagisi ustun turadi:

    1. AKKAUNT TANLOVI   `settings['bolimlar']` (mijoz yoki AI yozgan)
    2. MODUL STANDARTI   `app/modules/<modul>.json` -> `bolimlar`
    3. HAMMASI           yozuv yo'q bo'lsa — bugungi xatti-harakat

3-qatlam ATAYLAB: mavjud akkauntlarda (karton, mebel...) hech narsa
o'zgarmaydi. Yangi tanlov qilinmaguncha ular avvalgi menyuni ko'radi.

QO'SHISH/OLIB TASHLASH — kodsiz. Mijoz AI bilan gaplashadi, AI taklif
qiladi, odam tugmani bosadi va menyu o'zgaradi (`PUT /api/soha/bolimlar`).
"""
import json
import logging

log = logging.getLogger("gofra.bolimlar")

SOZLAMA_KALITI = "bolimlar"

# ---------------------------------------------------------------------
# KATALOG — tizimda MAVJUD bo'lgan hamma bo'lim.
#
# Bu ro'yxat frontenddagi `NAV` bilan bir xil bo'lishi SHART: nomi va
# ikonkasi shu yerdan beriladi, JS faqat chizadi. Ikki joyda ikki xil
# ro'yxat turgani uchun aynan shu nosozlik kelib chiqqan edi.
# ---------------------------------------------------------------------
KATALOG: dict[str, dict] = {
    "calc":   {"nom": "Смета", "ikonka": "calc",
               "rollar": ["Rahbar", "Menejer"]},
    "orders": {"nom": "Буюртмалар", "ikonka": "cart",
               "rollar": ["Rahbar", "Menejer", "Sex boshlig'i",
                          "Sklad mudiri", "Buxgalter"]},
    "crm":    {"nom": "Мижозлар", "ikonka": "users",
               "rollar": ["Rahbar", "Menejer", "Buxgalter"]},
    "dash":   {"nom": "Бошқарув панели", "ikonka": "dash",
               "rollar": ["Rahbar", "Menejer", "Buxgalter"]},
    "ai":     {"nom": "AI ёрдамчи", "ikonka": "ai",
               "rollar": ["Rahbar", "Menejer", "Sex boshlig'i",
                          "Sklad mudiri", "Buxgalter"]},
    "wh":     {"nom": "Омбор", "ikonka": "box",
               "rollar": ["Rahbar", "Sklad mudiri", "Sex boshlig'i"]},
    "mat":    {"nom": "Материаллар", "ikonka": "boxIn",
               "rollar": ["Rahbar", "Sklad mudiri"]},
    "zakup":  {"nom": "Хомашё харид", "ikonka": "boxIn",
               "rollar": ["Rahbar", "Sklad mudiri", "Buxgalter"]},
    "hr":     {"nom": "Ходимлар", "ikonka": "hr",
               "rollar": ["Rahbar", "Sex boshlig'i", "Buxgalter"]},
    "fin":    {"nom": "Молия", "ikonka": "wallet",
               "rollar": ["Rahbar", "Buxgalter", "Menejer"]},
    "kassa":  {"nom": "Касса", "ikonka": "wallet",
               "rollar": ["Rahbar", "Buxgalter"]},
    "hisob":  {"nom": "Бухгалтерия", "ikonka": "doc",
               "rollar": ["Rahbar", "Buxgalter"]},
    "exp":    {"nom": "Ҳисоботлар", "ikonka": "doc",
               "rollar": ["Rahbar", "Buxgalter", "Sex boshlig'i"]},
    "set":    {"nom": "Созламалар", "ikonka": "gear",
               "rollar": ["Rahbar"]},
    "help":   {"nom": "Йўриқнома", "ikonka": "doc",
               "rollar": ["Rahbar", "Menejer", "Sex boshlig'i",
                          "Sklad mudiri", "Buxgalter"]},
}

# O'CHIRIB BO'LMAYDIGANLAR. Bularsiz mijoz tizimga qaytib kira olmaydi
# yoki yordam so'ray olmaydi — shuning uchun AI ham, odam ham ularni
# olib tashlay olmaydi.
MAJBURIY = ("dash", "ai", "set", "help")

# Yozuv ham, modul standarti ham bo'lmaganda — BUGUNGI xatti-harakat.
HAMMASI = list(KATALOG.keys())


def _modul_standarti(modul_kaliti: str) -> list[str] | None:
    """`app/modules/<modul>.json` dagi `bolimlar` ro'yxati."""
    from . import domain
    try:
        tarif = domain.modullar().get(modul_kaliti) or {}
    except Exception:                                    # noqa: BLE001
        return None
    ro = tarif.get("bolimlar")
    if not isinstance(ro, list) or not ro:
        return None
    return [x for x in ro if x in KATALOG]


def joriy(db, modul_kaliti: str = "") -> list[str]:
    """Shu akkaunt uchun bo'limlar ro'yxati (kalitlar, tartibi bilan)."""
    from . import models as m
    yozuv = (db.query(m.Setting)
             .filter(m.Setting.key == SOZLAMA_KALITI).first())
    if yozuv and yozuv.value:
        try:
            tanlov = json.loads(yozuv.value)
            if isinstance(tanlov, list):
                kalitlar = [x for x in tanlov if x in KATALOG]
                # Majburiylar tushib qolmasin — yozuv qo'lda
                # tahrirlangan bo'lsa ham mijoz qulf ichida qolmaydi.
                for k in MAJBURIY:
                    if k not in kalitlar:
                        kalitlar.append(k)
                return kalitlar
        except (ValueError, TypeError):
            log.warning("bolimlar sozlamasi buzuq — standart olinadi")

    standart = _modul_standarti(modul_kaliti) if modul_kaliti else None
    return list(standart) if standart else list(HAMMASI)


def saqla(db, kalitlar: list[str]) -> list[str]:
    """Akkauntning bo'lim tanlovini yozadi. Qaytaradi: tozalangan ro'yxat."""
    from . import models as m
    tanlov = []
    for k in kalitlar or []:
        if k in KATALOG and k not in tanlov:
            tanlov.append(k)
    for k in MAJBURIY:
        if k not in tanlov:
            tanlov.append(k)

    yozuv = (db.query(m.Setting)
             .filter(m.Setting.key == SOZLAMA_KALITI).first())
    if yozuv is None:
        yozuv = m.Setting(key=SOZLAMA_KALITI, value="")
        db.add(yozuv)
    yozuv.value = json.dumps(tanlov, ensure_ascii=False)
    db.commit()
    return tanlov


def toliq(db, modul_kaliti: str = "", user_roli: str = "") -> list[dict]:
    """Frontend uchun: har bo'lim to'liq ta'rifi bilan.

    Faol bo'lmaganlari ham qaytariladi (`faol: false`) — sozlamalar
    ekranida mijoz ularni ko'rib, kerakligini belgilaydi.
    """
    faollar = joriy(db, modul_kaliti)

    # ROL NOMI MIJOZNIKI BO'LISHI MUMKIN. Katalogdagi `rollar` beshta
    # ASOS nomida yozilgan («Menejer»), mijozda esa «Barmen» bo'lishi
    # mumkin. Frontend nomlarni to'g'ridan-to'g'ri solishtiradi —
    # shuning uchun huquqi yetsa, foydalanuvchining O'Z nomi ro'yxatga
    # qo'shib yuboriladi. Aks holda menyu bo'm-bo'sh chiqardi.
    def _rollar(asl: list[str]) -> list[str]:
        if not user_roli or user_roli in asl:
            return asl
        from . import rollar as r
        a = r.asos(db, user_roli)
        if a in asl or a == r.ENG_YUQORI:
            return asl + [user_roli]
        return asl

    natija = []
    for kalit in faollar:
        t = KATALOG[kalit]
        natija.append({"kalit": kalit, "nom": t["nom"], "ikonka": t["ikonka"],
                       "rollar": _rollar(t["rollar"]), "faol": True,
                       "majburiy": kalit in MAJBURIY})
    for kalit, t in KATALOG.items():
        if kalit not in faollar:
            natija.append({"kalit": kalit, "nom": t["nom"],
                           "ikonka": t["ikonka"], "rollar": t["rollar"],
                           "faol": False, "majburiy": False})
    return natija
