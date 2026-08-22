"""INN QIDIRUVI — soliq to'lovchi ma'lumotini raqami bo'yicha topish.

Ro'yxatdan o'tishning birinchi qadami: odam INN ni kiritadi va korxona
nomini o'zi yozmasdan DARROV ko'radi.

USTUVOR QOIDA — YO'L HECH QACHON BERKILMAYDI.
Provayder sozlanmagan, javob bermayapti yoki INN topilmadi — bularning
HECH BIRI xato emas. Formada qizil yozuv chiqmaydi; odam korxona nomini
o'zi yozadi va davom etadi. Ro'yxatdan o'tish tashqi xizmatga bog'lanib
qolmasligi kerak: xizmat yiqilsa, bizning sotuvimiz to'xtaydi.

PROVAYDER ADMIN PANELIDAN SOZLANADI (`platforma_sozlamalar`):
    inn_provayder   — `ihamkor` | `maxsus` | `` (o'chirilgan)
    inn_manzil      — so'rov manzili, `{inn}` o'rni qo'yiladi
    inn_kalit       — API kaliti (SIR — API orqali to'liq qaytarilmaydi)
    inn_sarlavha    — qo'shimcha sarlavha nomi (masalan `X-API-Key`)

Kalit KODDA yozilmaydi va git ga tushmaydi.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

log = logging.getLogger("platforma.inn")

KUTISH = 6          # soniya — odam formada kutib turibdi, uzoq bo'lmasin
SOZLAMALAR = ("inn_provayder", "inn_manzil", "inn_kalit", "inn_sarlavha")

# SO'ROV CHEKLOVI — kvotani himoya qiladi.
#
# Bu endpoint OCHIQ bo'lishi shart: odam hali ro'yxatdan o'tmagan,
# tokeni yo'q. Lekin u PULLIK tashqi xizmatga so'rov yuboradi. Cheklovsiz
# qoldirilsa, oddiy skript bir kechada butun kvotani yoqib yuboradi va
# ertalab haqiqiy mijoz ro'yxatdan o'ta olmaydi.
#
# Xotirada, jarayonga xos. Bir nechta ishchi bo'lsa cheklov shunga
# ko'paytiriladi — bu yerda maqsad aniq suiiste'molni to'xtatish, ideal
# hisob emas. Redis kerak bo'lsa keyin qo'yiladi.
OYNA = 3600         # soniya
CHEK = 30           # bitta IP dan soatiga
_TARIX: dict[str, list[float]] = {}


def chek_oshdimi(ip: str) -> bool:
    import time
    hozir = time.time()
    tarix = [t for t in _TARIX.get(ip, []) if hozir - t < OYNA]
    # Xotira cheksiz o'smasin — eskirgan IP lar tozalanadi.
    if len(_TARIX) > 5000:
        for k in [k for k, v in _TARIX.items() if not v or hozir - v[-1] > OYNA]:
            _TARIX.pop(k, None)
    if len(tarix) >= CHEK:
        _TARIX[ip] = tarix
        return True
    tarix.append(hozir)
    _TARIX[ip] = tarix
    return False


def sozlama(db, kalit: str, zaxira: str = "") -> str:
    from . import models as pm
    y = db.query(pm.PlatformaSozlama).filter(
        pm.PlatformaSozlama.kalit == kalit).first()
    return (y.qiymat if y else "") or zaxira


def _javobdan_olish(xom: dict) -> dict:
    """Turli provayderlarning javobini BITTA ko'rinishga keltiradi.

    Har xizmat maydonini o'zicha nomlaydi (`name`, `shortName`,
    `companyName`, `nomi`...). Bu yerda ehtimoliy nomlar bo'yicha
    qidiriladi — provayder almashganda kod o'zgarmasin.
    """
    def ol(*nomlar):
        for n in nomlar:
            v = xom.get(n)
            if isinstance(v, (str, int)) and str(v).strip():
                return str(v).strip()
        return ""

    # Ba'zi xizmatlar ma'lumotni ichki obyektga o'raydi
    for orov in ("data", "result", "company", "taxpayer", "natija"):
        ichki = xom.get(orov)
        if isinstance(ichki, dict):
            ichki_natija = _javobdan_olish(ichki)
            if ichki_natija.get("nom"):
                return ichki_natija
        if isinstance(ichki, list) and ichki and isinstance(ichki[0], dict):
            return _javobdan_olish(ichki[0])

    return {
        "nom": ol("name", "shortName", "companyName", "nomi", "nom",
                  "full_name", "fullName", "short_name"),
        "inn": ol("tin", "inn", "taxId", "stir"),
        "manzil": ol("address", "manzil", "addr", "legalAddress"),
        "rahbar": ol("director", "rahbar", "ceo", "head"),
        "faoliyat": ol("activity", "faoliyat", "oked", "okedName"),
        "qqs": ol("vat", "qqs", "vatCode", "nds"),
    }


def qidir(db, inn: str) -> dict:
    """INN bo'yicha korxona ma'lumoti.

    Qaytaradi: `{"topildi": bool, "sabab": str, ...maydonlar}`
    `topildi=False` — bu XATO EMAS, qo'lda kiritishga o'tiladi.
    """
    inn = "".join(ch for ch in (inn or "") if ch.isdigit())
    if len(inn) != 9:
        return {"topildi": False, "sabab": "INN 9 raqamdan iborat bo'lsin",
                "qolda": True}

    provayder = sozlama(db, "inn_provayder")
    manzil = sozlama(db, "inn_manzil")
    if not provayder or not manzil:
        # Hali ulanmagan — bu ham normal holat.
        return {"topildi": False, "qolda": True,
                "sabab": "INN qidiruvi hali ulanmagan — nomini o'zingiz yozing"}

    url = manzil.replace("{inn}", inn)
    sarlavhalar = {"Accept": "application/json",
                   "User-Agent": "INNASOFT-Platforma/1.0"}
    kalit = sozlama(db, "inn_kalit")
    if kalit:
        nom = sozlama(db, "inn_sarlavha", "Authorization")
        sarlavhalar[nom] = kalit if nom != "Authorization" else f"Bearer {kalit}"

    try:
        r = urllib.request.Request(url, headers=sarlavhalar)
        with urllib.request.urlopen(r, timeout=KUTISH) as x:
            xom = json.loads(x.read().decode() or "{}")
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        # Tashqi xizmat yiqildi — biz yiqilmaymiz.
        log.warning("INN qidiruvi ishlamadi (%s): %s", url.split("?")[0], e)
        return {"topildi": False, "qolda": True,
                "sabab": "Qidiruv xizmati javob bermadi — nomini o'zingiz yozing"}

    if not isinstance(xom, dict):
        xom = {"data": xom}
    natija = _javobdan_olish(xom)
    if not natija.get("nom"):
        return {"topildi": False, "qolda": True,
                "sabab": "Bu INN bo'yicha korxona topilmadi — nomini o'zingiz yozing"}
    natija["topildi"] = True
    natija["qolda"] = False
    natija.setdefault("inn", inn)
    return natija
