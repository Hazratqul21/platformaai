"""GL NI MAVJUD AMALLARGA ULASH — PARALLEL rejim.

⚠️ ENG MUHIM QOIDA: GL XATOSI ASOSIY AMALNI TO'XTATMAYDI.

Sabab: bugungi hisob-kitob (`services.py`) ishlab turibdi va mijoz
unga tayanadi. Agar provodka yozishda xato bo'lsa va u buyurtma
topshirishni to'xtatsa — biz ishlayotgan narsani buzgan bo'lamiz.

Shuning uchun har ulash `try/except` ichida: xato bo'lsa LOGGA yoziladi
va amal davom etadi. `tools/butunlik.py` esa GL va eski usul mos
kelmayotganini ko'rsatadi — ya'ni xato yashirinmaydi, lekin ishni
buzmaydi.

Parallel davr tugagach (raqamlar mos kelgani isbotlangach) bu himoya
olib tashlanadi va GL asosiy manba bo'ladi.
"""
import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from .. import models as m
from . import xizmat as gl

log = logging.getLogger("gofra.hisob.ulash")

NOL = Decimal("0")


def _d(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x or 0))


def _xavfsiz(nom: str):
    """Dekorator: GL xatosi asosiy amalni to'xtatmasin."""
    def orab(fn):
        def ichki(*a, **kw):
            try:
                return fn(*a, **kw)
            except Exception as e:              # noqa: BLE001
                log.warning("GL yozilmadi (%s): %s", nom, e)
                return None
        return ichki
    return orab


@_xavfsiz("buyurtma_topshirildi")
def buyurtma_topshirildi(db: Session, o: m.Order, miqdor: Decimal,
                         sana: date, kim: str = "") -> m.Provodka | None:
    """Mahsulot mijozga berildi — daromad tan olinadi, qarz paydo bo'ladi.

    QISMAN topshirishda ham ishlaydi: summalar berilgan miqdor
    ULUSHIGA qarab hisoblanadi. Aks holda birinchi qismda butun
    summa yozilib, qarz ikki barobar chiqardi.
    """
    miqdor = _d(miqdor)
    qty = _d(o.qty)
    if miqdor <= NOL or qty <= NOL:
        return None
    ulush = miqdor / qty

    jami = _d(o.total) * ulush
    qqs = _d(o.qqs_summa) * ulush
    qqssiz = jami - qqs

    # Tannarx: `unit_cost` × berilgan miqdor (ulush emas — u allaqachon
    # dona hisobida). Nol bo'lsa tannarx qatori umuman tushmaydi.
    tannarx = _d(o.unit_cost) * miqdor

    return gl.qoida_boyicha(
        db, "buyurtma_topshirildi", sana,
        {"qqssiz": qqssiz, "qqs": qqs, "jami": jami, "tannarx": tannarx},
        hujjat_turi="buyurtma", hujjat_id=o.id, kim=kim,
        izoh=f"Buyurtma #{o.id} · {miqdor} dona")


@_xavfsiz("mijoz_tolovi")
def mijoz_tolovi(db: Session, tolov: m.Payment, kim: str = "") -> m.Provodka | None:
    summa = _d(tolov.amount)
    if summa <= NOL:
        return None
    return gl.qoida_boyicha(
        db, "mijoz_tolovi", tolov.paid_at or date.today(), {"summa": summa},
        hujjat_turi="tolov", hujjat_id=tolov.id, kim=kim,
        izoh=f"To'lov #{tolov.id}")


@_xavfsiz("material_kirim")
def material_kirim(db: Session, xarid: m.Purchase, kim: str = "") -> m.Provodka | None:
    """Xarid — ombor to'ladi, yetkazib beruvchiga qarz paydo bo'ladi."""
    jami = _d(xarid.total)
    if jami <= NOL:
        return None
    # Xaridda hozircha QQS ajratilmaydi (`Purchase` da maydon yo'q) —
    # butun summa material qiymatiga tushadi. QQS hisobga olish EHF
    # bilan birga qo'shiladi (docs/05-INTEGRATSIYALAR.md).
    qqs = NOL
    return gl.qoida_boyicha(
        db, "material_kirim", xarid.purchased_at or date.today(),
        {"qqssiz": jami - qqs, "qqs": qqs, "jami": jami},
        hujjat_turi="xarid", hujjat_id=xarid.id, kim=kim,
        izoh=f"Xarid #{xarid.id}")


@_xavfsiz("yetkazuvchiga_tolov")
def yetkazuvchiga_tolov(db: Session, summa, sana: date, hujjat_id: int | None = None,
                        kim: str = "") -> m.Provodka | None:
    summa = _d(summa)
    if summa <= NOL:
        return None
    return gl.qoida_boyicha(db, "yetkazuvchiga_tolov", sana or date.today(),
                            {"summa": summa}, hujjat_turi="yetkazuvchi_tolov",
                            hujjat_id=hujjat_id, kim=kim)


@_xavfsiz("ish_haqi_tolandi")
def ish_haqi_tolandi(db: Session, summa, sana: date, hujjat_id: int | None = None,
                     kim: str = "") -> m.Provodka | None:
    summa = _d(summa)
    if summa <= NOL:
        return None
    return gl.qoida_boyicha(db, "ish_haqi_tolandi", sana or date.today(),
                            {"summa": summa}, hujjat_turi="ish_haqi",
                            hujjat_id=hujjat_id, kim=kim)


@_xavfsiz("sex_xarajati")
def sex_xarajati(db: Session, summa, sana: date, hujjat_id: int | None = None,
                 izoh: str = "", kim: str = "") -> m.Provodka | None:
    summa = _d(summa)
    if summa <= NOL:
        return None
    return gl.qoida_boyicha(db, "sex_xarajati", sana or date.today(),
                            {"summa": summa}, hujjat_turi="xarajat",
                            hujjat_id=hujjat_id, izoh=izoh, kim=kim)
