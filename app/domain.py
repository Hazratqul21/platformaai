"""SOHA QATLAMI — biznes turiga xos maydonlar ta'rifi.

YADRO (Order, Client, Payment, kassa, ombor...) bu maydonlarning MA'NOSINI
bilmaydi. U shunchaki `order.attributes` ni saqlaydi, ko'rsatadi va eksport
qiladi. «Uzunlik 300 mm» nimani anglatishini faqat shu fayl biladi.

HOZIRCHA karton profili kodda yozilgan. 1-bosqichning 5-qadamida u bazaga
(`Setting` / `Formula`) ko'chiriladi va shunda yangi soha qo'shish uchun
KOD YOZISH KERAK BO'LMAYDI — konfiguratsiya yetarli. Ayni shu narsa AI
agent (4-bosqich) to'ldiradigan qatlam.

Fayl ataylab yadro modullariga bog'lanmagan (`models` import qilmaydi) —
soha qatlami yadroga tobe, teskarisi emas.
"""
from decimal import Decimal

# Maydon turlari va ularning JSON dagi ko'rinishi:
#
#   "butun"  -> int      JSON: son
#   "matn"   -> str      JSON: satr
#   "mantiq" -> bool     JSON: true/false
#   "kasr"   -> Decimal  JSON: SATR ("12.3400")
#
# Nega `kasr` satr sifatida saqlanadi: JSON da faqat float bor, float esa
# aniqlikni yo'qotadi. Bu loyihada pul va o'lchov ataylab `Decimal` —
# `models.py` da "barcha pul summalari uchun DECIMAL — float ishlatilmaydi"
# deb yozilgan. JSON ga float qilib tashlasak o'sha qoida buzilardi.


class Maydon:
    """Bitta soha maydonining ta'rifi."""

    def __init__(self, kalit: str, nom: str, tur: str, birlik: str = ""):
        self.kalit = kalit      # attributes dagi kalit (= eski ustun nomi)
        self.nom = nom          # foydalanuvchiga ko'rinadigan nom
        self.tur = tur          # butun | matn | mantiq | kasr
        self.birlik = birlik    # mm, m², dona... (bo'sh bo'lishi mumkin)


# --- KARTON / GOFRA profili (Rustam akaning sexi) ---------------------
# Kalitlar ataylab eski ustun nomlari bilan bir xil: 3-qadamda o'qishni
# ko'chirganda `o.length_mm` -> `soha_oqi(o, "length_mm")` deb almashtirish
# mexanik bo'ladi, nom moslashtirish bilan ovora bo'linmaydi.
KARTON = [
    Maydon("length_mm",  "Uzunlik",        "butun",  "mm"),
    Maydon("width_mm",   "Kenglik",        "butun",  "mm"),
    Maydon("height_mm",  "Balandlik",      "butun",  "mm"),
    Maydon("tur",        "Buyurtma turi",  "matn"),
    Maydon("layers",     "Qavatlar",       "butun"),
    Maydon("grade",      "Qog'oz markasi", "matn"),
    Maydon("colors",     "Ranglar soni",   "butun"),
    Maydon("is_offset",  "Ofset",          "mantiq"),
    Maydon("m2_per_box", "1 dona m²",      "kasr",   "m²"),
]

# Hozircha bitta profil. 5-qadamda bu bazadan o'qiladi.
PROFIL = KARTON
KALITLAR = [maydon.kalit for maydon in PROFIL]
_MAYDON = {maydon.kalit: maydon for maydon in PROFIL}


def _json_ga(maydon: Maydon, qiymat):
    """Python qiymatini JSON saqlashga yaroqli holga keltiradi."""
    if qiymat is None:
        return None
    if maydon.tur == "kasr":
        return str(Decimal(str(qiymat)))
    if maydon.tur == "butun":
        return int(qiymat)
    if maydon.tur == "mantiq":
        return bool(qiymat)
    return str(qiymat)


def _json_dan(maydon: Maydon, qiymat):
    """JSON dagi qiymatni Python turiga qaytaradi."""
    if qiymat is None:
        return None
    if maydon.tur == "kasr":
        return Decimal(str(qiymat))
    if maydon.tur == "butun":
        return int(qiymat)
    if maydon.tur == "mantiq":
        return bool(qiymat)
    return str(qiymat)


def soha_yoz(order) -> None:
    """Order ustunlaridagi soha qiymatlarini `attributes` ga ko'chiradi.

    2-qadam «ikki joyga yozish» shu funksiya orqali ishlaydi: buyurtma
    yaratilgandan yoki tahrirlangandan keyin bir marta chaqiriladi.

    4-qadamda ustunlar o'chirilganda bu funksiya ham ketadi — o'shanda
    qiymatlar to'g'ridan-to'g'ri `attributes` ga yoziladi.
    """
    if order.attributes is None:
        order.attributes = {}
    for maydon in PROFIL:
        order.attributes[maydon.kalit] = _json_ga(
            maydon, getattr(order, maydon.kalit, None))


def soha_oqi(order, kalit: str, standart=None):
    """Soha maydonini `attributes` dan o'qiydi, to'g'ri Python turida.

    3-qadamda `order.length_mm` o'rniga shu ishlatiladi.
    """
    maydon = _MAYDON.get(kalit)
    if maydon is None:
        raise KeyError(f"'{kalit}' — profilda yo'q soha maydoni")
    xom = (order.attributes or {}).get(kalit)
    if xom is None:
        return standart
    return _json_dan(maydon, xom)


def soha_hammasi(order) -> dict:
    """Hamma soha maydonlari, Python turlarida. Hisobot/eksport uchun."""
    return {maydon.kalit: soha_oqi(order, maydon.kalit) for maydon in PROFIL}


# ---------------------------------------------------------------------
# Mahsulotni SO'Z bilan tasvirlash
#
# Bu ham soha bilimi: «300×200×150» karton uchun ma'noli, non zavodi uchun
# esa yo'q — u «bug'doy noni, 600 g» deb yozadi. Shuning uchun yadro
# (hisobot, chek, bot xabari, ombor ro'yxati) matnni O'ZI YIG'MAYDI,
# shu funksiyalardan so'raydi.
#
# Ilgari `f"{o.length_mm}×{o.width_mm}×{o.height_mm}"` naqshi kod bo'ylab
# 8 joyda takrorlangan edi — har biri kartonni bilishga majbur edi.
# ---------------------------------------------------------------------

def olcham_matni(order, ajratgich: str = "×") -> str:
    """«300×200×150». Ajratgich turlicha: hisobotlarda × , eksportda x."""
    o = soha_hammasi(order)
    return ajratgich.join(
        str(o[k] or 0) for k in ("length_mm", "width_mm", "height_mm"))


def tur_matni(order) -> str:
    """Buyurtma turi. Eski yozuvlarda `tur` bo'sh — qavatdan tiklanadi."""
    o = soha_hammasi(order)
    return o["tur"] or f"{o['layers']} слой"


def tarkib_matni(order) -> str:
    """«3-қават, K1, 2 рангли босма» — hujjat/chek uchun."""
    o = soha_hammasi(order)
    matn = f"{o['layers']}-қават, {o['grade']}"
    if o["colors"]:
        matn += f", {o['colors']} рангли босма"
    return matn
