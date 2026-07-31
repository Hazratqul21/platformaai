"""Kassa jurnalini pul harakatlari bilan bir joyda ushlab turish.

Muammo shu edi: pul beshta bo'limda yuritilardi (mijoz to'lovi, sex xarajati,
xodim avansi, xarid to'lovi, yetkazib beruvchiga to'lov), kassa jurnali esa
ularning faqat bir bo'lagini ko'rardi. Natijada kassa qoldig'i chiqimni to'liq,
kirimni yarim ko'rib manfiy chiqardi.

Yechim: har bir pul harakati o'z bo'limida yozilganda kassaga ham nusxasi
tushadi va manbaga bog'lanadi (linked_* ustunlari). Bog'lanish bir harakat
kassaga ikki marta tushishiga yo'l qo'ymaydi, manba o'chirilsa nusxasi ham ketadi.

Kassa yozuvi shu yerdan yaratiladi, boshqa joyda qo'lda yaratilmaydi — shunda
qoida bitta joyda turadi.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from . import models as m

# Manba turi -> kassa_entries dagi bog'lash ustuni
BOGLASH = {
    "cash": "linked_cash_id",
    "payment": "linked_payment_id",
    "purchase": "linked_purchase_id",
    "purchase_payment": "linked_purchase_payment_id",
    "supplier_payment": "linked_supplier_payment_id",
}


def _firma(qiymat: str | None) -> str:
    """Kassa yozuvining firmasi manbadan olinadi.

    Manbada firma ko'rsatilmagan bo'lsa bo'sh qoldiriladi — bo'sh firma
    ro'yxatlarda ikkala sex ostida ham ko'rinadi (mijoz va buyurtmadagi qoida
    bilan bir xil). "Asosiy" deb yozib qo'yilsa firma bo'yicha filtrda
    yo'qolib ketardi.
    """
    return (qiymat or "").strip()


def yozuv_top(db: Session, tur: str, manba_id: int) -> m.KassaEntry | None:
    """Shu manba uchun kassada yozuv bormi."""
    ustun = BOGLASH[tur]
    return (db.query(m.KassaEntry)
            .filter(getattr(m.KassaEntry, ustun) == manba_id).first())


def yoz(db: Session, *, tur: str, manba_id: int, direction: str, who: str,
        note: str, amount: Decimal | float | str, entry_at: date | None = None,
        firm: str | None = None, created_by: str = "") -> m.KassaEntry | None:
    """Kassaga yozuv qo'shadi. Shu manba uchun yozuv allaqachon bo'lsa —
    summa/sana yangilanadi, yangi nusxa yaratilmaydi."""
    summa = Decimal(str(amount))
    if summa <= 0:
        return None
    if direction not in ("Kirim", "Chiqim"):
        raise ValueError("direction: Kirim yoki Chiqim")

    bor = yozuv_top(db, tur, manba_id)
    if bor:
        bor.amount = summa
        bor.who = who[:120]
        bor.note = note[:200]
        if entry_at:
            bor.entry_at = entry_at
        if firm is not None:
            bor.firm = _firma(firm)
        return bor

    e = m.KassaEntry(firm=_firma(firm), direction=direction, who=who[:120],
                     note=note[:200], amount=summa, currency="so'm",
                     entry_at=entry_at or date.today(), created_by=created_by)
    setattr(e, BOGLASH[tur], manba_id)
    db.add(e)
    return e


def ochir(db: Session, tur: str, manba_id: int) -> int:
    """Manba o'chirilganda kassadagi nusxasini ham o'chiradi."""
    ustun = BOGLASH[tur]
    n = 0
    for e in db.query(m.KassaEntry).filter(getattr(m.KassaEntry, ustun) == manba_id).all():
        db.delete(e)
        n += 1
    return n


# ------------------------------------------------------------------ kirim

def mijoz_tolovi(db: Session, p: m.Payment, kim: str = "") -> m.KassaEntry | None:
    """Mijoz to'lovi — kassaga kirim."""
    c = db.get(m.Client, p.client_id)
    izoh = (p.note or "").strip()
    if p.order_id and f"#{p.order_id}" not in izoh:
        izoh = f"Буюртма #{p.order_id}" + (f" · {izoh}" if izoh else "")
    if p.method:
        izoh = f"{izoh} · {p.method}" if izoh else str(p.method)
    return yoz(db, tur="payment", manba_id=p.id, direction="Kirim",
               who=(c.company if c else "Мижоз"), note=izoh or "Мижоз тўлови",
               amount=p.amount, entry_at=p.paid_at,
               firm=(c.firm if c else ""), created_by=kim)


# ------------------------------------------------------------------ chiqim

def xodim_avansi(db: Session, c: m.CashEntry, kim: str = "") -> m.KassaEntry | None:
    """Xodimga berilgan pul — kassadan chiqim."""
    xod = db.get(m.Employee, c.employee_id) if c.employee_id else None
    izoh = (c.note or "").strip()
    return yoz(db, tur="cash", manba_id=c.id, direction="Chiqim",
               who=(xod.name if xod else "Ходим"),
               note=f"Аванс{' · ' + izoh if izoh else ''}",
               amount=c.amount, entry_at=c.entry_at, firm=c.firm, created_by=kim)


def sex_xarajati(db: Session, c: m.CashEntry, kim: str = "") -> m.KassaEntry | None:
    """Sex rasxodi (kley, skotch, yo'lkira...) — kassadan chiqim."""
    izoh = (c.note or "").strip()
    return yoz(db, tur="cash", manba_id=c.id, direction="Chiqim",
               who=(izoh or "Цех харажати"), note="Цех харажати",
               amount=c.amount, entry_at=c.entry_at, firm=c.firm, created_by=kim)


def naqd_xarid(db: Session, p: m.Purchase, kim: str = "") -> m.KassaEntry | None:
    """Xarid paytida naqd to'langan summa — kassadan chiqim.

    To'lanmagan (qarzga olingan) xarid kassaga tushmaydi: pul hali chiqmagan.
    """
    tolangan = Decimal(p.paid_amount or 0)
    if tolangan <= 0:
        ochir(db, "purchase", p.id)
        return None
    sup = db.get(m.Supplier, p.supplier_id)
    mat = db.get(m.Material, p.material_id)
    return yoz(db, tur="purchase", manba_id=p.id, direction="Chiqim",
               who=(sup.name if sup else "Етказиб берувчи"),
               note=f"Харид #{p.id}" + (f" · {mat.name}" if mat else ""),
               amount=tolangan, entry_at=p.purchased_at, firm=p.firm, created_by=kim)


def xarid_qarziga_tolov(db: Session, pp: m.PurchasePayment,
                        kim: str = "") -> m.KassaEntry | None:
    """Xarid qarzini yopish uchun berilgan pul — kassadan chiqim."""
    p = db.get(m.Purchase, pp.purchase_id)
    sup = db.get(m.Supplier, p.supplier_id) if p else None
    izoh = (pp.note or "").strip()
    return yoz(db, tur="purchase_payment", manba_id=pp.id, direction="Chiqim",
               who=(sup.name if sup else "Етказиб берувчи"),
               note=f"Харид #{pp.purchase_id} тўлови" + (f" · {izoh}" if izoh else ""),
               amount=pp.amount, entry_at=pp.paid_at,
               firm=(p.firm if p else ""), created_by=kim)


def yetkazib_beruvchiga_tolov(db: Session, sp: m.SupplierPayment,
                              kim: str = "") -> m.KassaEntry | None:
    """Yetkazib beruvchiga to'g'ridan-to'g'ri berilgan pul — kassadan chiqim."""
    sup = db.get(m.Supplier, sp.supplier_id)
    izoh = (sp.note or "").strip()
    return yoz(db, tur="supplier_payment", manba_id=sp.id, direction="Chiqim",
               who=(sup.name if sup else "Етказиб берувчи"),
               note="Етказиб берувчига тўлов" + (f" · {izoh}" if izoh else ""),
               amount=sp.amount, entry_at=sp.paid_at, firm="", created_by=kim)
