"""Boshqaruv bazasi ustidagi amallar: akkaunt yaratish, AI sarfini yozish, limit.

Bu yerda HISOB-KITOB bor, shuning uchun `services.py` dagi qoidalar
shu yerda ham amal qiladi: pul `Decimal` da, float aralashtirilmaydi.
"""
import os
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models as pm

# ---------------------------------------------------------------------
# NARX JADVALI — 1 mln token uchun USD, provayder e'lon qilgan narx.
#
# Bu jadval O'ZGARADI (provayder narxni o'zgartiradi). Shuning uchun
# sarf yozilganda narx `ai_sarf` ga KO'CHIRILADI — keyingi o'zgarish
# eski hisobni buzmasin. Jadvalning o'zi «bugungi narx» ni bildiradi.
# ---------------------------------------------------------------------
NARX_USD_MLN: dict[str, tuple[str, str]] = {
    # model: (kirish, chiqish)
    "gemini-2.5-flash":        ("0.30", "2.50"),
    "gemini-3.5-flash-lite":   ("0.10", "0.40"),
    "gemini-flash-latest":     ("0.30", "2.50"),
    "gpt-5-mini":              ("0.25", "2.00"),
    "gpt-4.1-mini":            ("0.40", "1.60"),
    "claude-sonnet-5":         ("3.00", "15.00"),
    "claude-haiku-4-5-20251001": ("1.00", "5.00"),
}
# Ro'yxatda yo'q model uchun — ehtiyot chorasi sifatida qimmatrog'i.
# Nol qo'yilsa mijozga bepul chiqib ketardi va buni hech kim sezmasdi.
NOMALUM_NARX = ("3.00", "15.00")


def _kurs() -> Decimal:
    """USD kursi. Sarf paytidagi qiymat sarf yozuviga qotiriladi."""
    return Decimal(os.getenv("USD_KURS", "12600"))


def _ustama() -> Decimal:
    """Ustama: valyuta tebranishi, qayta urinishlar, shlyuz xarajati."""
    return Decimal(os.getenv("AI_USTAMA", "1.30"))


def _som(qiymat: Decimal) -> Decimal:
    return qiymat.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def narx_mln_som(model: str) -> tuple[Decimal, Decimal]:
    """Model uchun 1 mln tokenning so'mdagi narxi (kirish, chiqish)."""
    kirish, chiqish = NARX_USD_MLN.get(model, NOMALUM_NARX)
    k = _kurs() * _ustama()
    return _som(Decimal(kirish) * k), _som(Decimal(chiqish) * k)


def sarf_yoz(db: Session, akkaunt_id: int, provayder: str, model: str,
             kirish_token: int, chiqish_token: int, agent: str = "",
             user_login: str = "", muvaffaqiyat: bool = True) -> pm.AiSarf:
    """Bitta AI so'rovini yozadi va narxini O'SHA PAYTDAGI stavkada qotiradi."""
    kirish_narx, chiqish_narx = narx_mln_som(model)
    mln = Decimal("1000000")
    summa = _som(Decimal(kirish_token) / mln * kirish_narx
                 + Decimal(chiqish_token) / mln * chiqish_narx)
    yozuv = pm.AiSarf(
        akkaunt_id=akkaunt_id, provayder=provayder, model=model,
        kirish_token=kirish_token, chiqish_token=chiqish_token,
        kirish_narx_mln=kirish_narx, chiqish_narx_mln=chiqish_narx,
        narx_som=summa, agent=agent, user_login=user_login,
        muvaffaqiyat=muvaffaqiyat)
    db.add(yozuv)
    db.commit()
    return yozuv


def joriy_oy(vaqt: datetime | None = None) -> str:
    return (vaqt or datetime.utcnow()).strftime("%Y-%m")


def oylik_sarf(db: Session, akkaunt_id: int, oy: str | None = None) -> dict:
    """Oy bo'yicha jami: so'rov soni, token, so'm."""
    oy = oy or joriy_oy()
    boshi = datetime.strptime(oy + "-01", "%Y-%m-%d")
    keyingi = datetime(boshi.year + (boshi.month == 12),
                       1 if boshi.month == 12 else boshi.month + 1, 1)
    q = (db.query(func.count(pm.AiSarf.id),
                  func.coalesce(func.sum(pm.AiSarf.kirish_token), 0),
                  func.coalesce(func.sum(pm.AiSarf.chiqish_token), 0),
                  func.coalesce(func.sum(pm.AiSarf.narx_som), 0))
         .filter(pm.AiSarf.akkaunt_id == akkaunt_id,
                 pm.AiSarf.vaqt >= boshi, pm.AiSarf.vaqt < keyingi).one())
    return {"oy": oy, "sorov": int(q[0]),
            "kirish_token": int(q[1]), "chiqish_token": int(q[2]),
            "token": int(q[1]) + int(q[2]), "som": Decimal(str(q[3]))}


def limit_holati(db: Session, akkaunt_id: int, oy: str | None = None) -> dict:
    """AI limiti holati.

    QOIDA: limit tugasa AI to'xtaydi, ERP ISHLAYVERADI. Shuning uchun
    bu funksiya faqat AI chaqiruvidan oldin tekshiriladi — boshqa
    joyda emas.
    """
    oy = oy or joriy_oy()
    sarf = oylik_sarf(db, akkaunt_id, oy)
    limit = (db.query(pm.AiLimit)
             .filter(pm.AiLimit.akkaunt_id == akkaunt_id, pm.AiLimit.oy == oy)
             .first())
    limit_som = Decimal(str(limit.limit_som)) if limit else Decimal("0")
    if limit_som <= 0:                      # 0 = cheklovsiz
        return {**sarf, "limit_som": Decimal("0"), "foiz": 0,
                "ogoh": False, "toxtatilsin": False}
    foiz = int(sarf["som"] / limit_som * 100)
    return {**sarf, "limit_som": limit_som, "foiz": foiz,
            "ogoh": foiz >= 80, "toxtatilsin": sarf["som"] >= limit_som}


# ---------------------------------------------------------------------
# AKKAUNT
# ---------------------------------------------------------------------
KOD_QOLIP = re.compile(r"^[a-z][a-z0-9-]{2,39}$")
# Subdomen sifatida ishlatib bo'lmaydigan yoki chalkashtiradigan nomlar.
BAND_KODLAR = {"www", "api", "app", "admin", "mail", "ftp", "ns", "static",
               "test", "tizim", "archive", "base", "diydor",
               "cdn", "test", "dev", "stage", "docs", "status", "innasoft"}


def kod_tekshir(kod: str) -> str:
    """Subdomen kodi. Xato bo'lsa `ValueError`."""
    kod = (kod or "").strip().lower()
    if not KOD_QOLIP.match(kod):
        raise ValueError("Kod: kichik harf bilan boshlanadi, 3–40 belgi, "
                         "faqat harf/raqam/tire")
    if kod in BAND_KODLAR:
        raise ValueError(f"'{kod}' — band nom, boshqasini tanlang")
    return kod


def baza_nomi_yasa(kod: str) -> str:
    """PostgreSQL baza nomi. Tire pastki chiziqqa aylanadi (tirega
    `CREATE DATABASE` da qo'shtirnoq kerak bo'lardi — chalkashlik)."""
    return "inna_" + kod.replace("-", "_")


def akkaunt_yarat(db: Session, kod: str, nom: str, inn: str = "",
                qqs_tolovchi: bool = False, kim: str = "") -> pm.Akkaunt:
    """Akkaunt YOZUVINI yaratadi. BAZANI yaratmaydi — u fon vazifasi.

    Ajratilgan, chunki `CREATE DATABASE` + migratsiya + profil yuklash
    bir necha soniya oladi va so'rov ichida qilinmaydi.
    """
    kod = kod_tekshir(kod)
    if db.query(pm.Akkaunt).filter(pm.Akkaunt.kod == kod).first():
        raise ValueError(f"'{kod}' allaqachon band")
    akkaunt = pm.Akkaunt(kod=kod, nom=(nom or "").strip() or kod,
                     inn=(inn or "").strip(), qqs_tolovchi=qqs_tolovchi,
                     baza_nomi=baza_nomi_yasa(kod))
    db.add(akkaunt)
    db.flush()
    audit(db, "akkaunt_yaratildi", akkaunt_id=akkaunt.id, kim=kim, tafsilot=kod)
    db.commit()
    return akkaunt


def audit(db: Session, amal: str, akkaunt_id: int | None = None,
          kim: str = "", tafsilot: str = "") -> None:
    db.add(pm.PlatformaAudit(amal=amal, akkaunt_id=akkaunt_id, kim=kim,
                             tafsilot=tafsilot))
