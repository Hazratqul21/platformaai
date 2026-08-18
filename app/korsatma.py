"""AGENT KO'RSATMALARI — koddan bazaga chiqarilgan.

Loyihaning asosiy tamoyili: SOHA koddan JSON'ga chiqarilgan edi
(`domain.py`). Bu yerda AI ning ko'rsatmasi ham shunday chiqadi —
prompt o'zgartirish uchun kod yozish va qayta joylash kerak emas.

UCH DARAJA — ustuvorlik pastdan yuqoriga:

    1. KOD          `agent.AGENTLAR[k]["korsatma"]` — zaxira, hech qachon
                    yo'qolmaydi
    2. PLATFORMA    biz hamma akkauntga yangi ko'rsatma beramiz
                    (boshqaruv bazasi, `agent_shablon`)
    3. AKKAUNT      mijoz o'ziga moslaydi (mijoz bazasi, `agent_sozlama`)

Akkaunt darajasi platformanikini, platforma esa kodnikini bosadi.

⚠️ XAVFSIZLIK QISMI TAHRIRLANMAYDI. Ko'rsatmaning oxiriga har doim
`_UMUMIY_USLUB` (raqamni o'ylab topma, bilmasang asbob chaqir) va
GenUI shartnomasi qo'shiladi. Mijoz ularni o'chira olmaydi — aks holda
AI raqam to'qib chiqarishi mumkin bo'lardi va bu bir marta yetadi
(docs/00-STRATEGIYA.md §0.5).
"""
import logging

from .tenancy import kalit as _kesh_kaliti

log = logging.getLogger("gofra.korsatma")

MAX_UZUNLIK = 8000     # har so'rovda yuboriladi — uzun prompt = qimmat AI
MIN_UZUNLIK = 40       # bo'sh ko'rsatma = ishlamaydigan agent

# Kesh MIJOZ BO'YICHA. `domain._KESH` bilan bir xil naqsh va bir xil
# sabab: global bo'lsa bir akkauntning ko'rsatmasi boshqasiga ko'rinadi.
_KESH: dict[str, dict[str, str]] = {}


def keshni_tozala(hammasi: bool = False) -> None:
    if hammasi:
        _KESH.clear()
    else:
        _KESH.pop(_kesh_kaliti(), None)


def tekshir(matn: str) -> str:
    """Saqlashdan oldin. Xato bo'lsa `ValueError`."""
    matn = (matn or "").strip()
    if len(matn) < MIN_UZUNLIK:
        raise ValueError(f"Ko'rsatma juda qisqa — kamida {MIN_UZUNLIK} belgi")
    if len(matn) > MAX_UZUNLIK:
        raise ValueError(
            f"Ko'rsatma {len(matn)} belgi — chegara {MAX_UZUNLIK}. "
            f"Ko'rsatma HAR so'rovda yuboriladi, uzunligi to'g'ridan-to'g'ri "
            f"AI xarajatiga aylanadi.")
    return matn


def _platforma_shabloni(kalit: str) -> str | None:
    """Biz bergan ko'rsatma (hamma akkaunt uchun)."""
    try:
        from .platforma.db import BoshqaruvSession
        from .platforma import models as pm
        db = BoshqaruvSession()
        try:
            y = (db.query(pm.AgentShablon)
                 .filter(pm.AgentShablon.kalit == kalit).first())
            return y.korsatma if y else None
        finally:
            db.close()
    except Exception:            # noqa: BLE001
        # Boshqaruv bazasi yo'q (yagona rejim) — bu xato emas.
        return None


def _akkaunt_sozlamasi(kalit: str) -> str | None:
    """Mijoz o'zgartirgan ko'rsatma."""
    try:
        from .db import sessiya
        from . import models as m
        db = sessiya()
        try:
            y = (db.query(m.AgentSozlama)
                 .filter(m.AgentSozlama.kalit == kalit).first())
            return y.korsatma if y else None
        finally:
            db.close()
    except Exception:            # noqa: BLE001
        return None


def manba(kalit: str) -> str:
    """Joriy ko'rsatma qayerdan kelyapti: `akkaunt` / `platforma` / `kod`."""
    if _akkaunt_sozlamasi(kalit):
        return "akkaunt"
    if _platforma_shabloni(kalit):
        return "platforma"
    return "kod"


def kod_korsatmasi(kalit: str) -> str:
    """Kodadagi zaxira — hech qachon yo'qolmaydi."""
    from .agent import AGENTLAR
    a = AGENTLAR.get(kalit)
    return a["korsatma"] if a else ""


def ol(kalit: str) -> str:
    """Agentning TO'LIQ ko'rsatmasi: tahrirlangan qism + xavfsizlik.

    Agent halqasi shu funksiyani chaqiradi.
    """
    k = _kesh_kaliti()
    kesh = _KESH.setdefault(k, {})
    if kalit in kesh:
        return kesh[kalit]

    asos = (_akkaunt_sozlamasi(kalit) or _platforma_shabloni(kalit)
            or kod_korsatmasi(kalit))
    # XAVFSIZLIK — har doim qo'shiladi, tahrirlab bo'lmaydi.
    from .agent import _UMUMIY_USLUB
    toliq = asos + _UMUMIY_USLUB
    kesh[kalit] = toliq
    return toliq
