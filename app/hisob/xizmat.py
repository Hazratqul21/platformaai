"""BOSH KITOB DVIGATELI — provodka yozish, saldo, balans.

QAT'IY QOIDALAR (buxgalteriyaning o'zi shunday talab qiladi):

1. Provodka O'CHIRILMAYDI — xato bo'lsa STORNO (teskari yozuv).
2. Yopilgan davrga YOZIB BO'LMAYDI.
3. Summa musbat bo'lishi shart — manfiy summa storno bilan yoziladi,
   minus bilan emas (aks holda oborot noto'g'ri chiqadi).
4. Nol summali qator yozilmaydi — u faqat hisobotni chalkashtiradi.
5. Har qator o'zi tenglashadi (Дт—Кт shakli), ya'ni «balans buzildi»
   holati STRUKTURA darajasida imkonsiz.
"""
import json
import logging
import os
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models as m

log = logging.getLogger("gofra.hisob")

PAPKA = os.path.dirname(__file__)
NOL = Decimal("0")


# ---------------------------------------------------------------------
# SHABLONLAR (JSON) va ularni bazaga yuklash
# ---------------------------------------------------------------------
def reja_shabloni() -> dict:
    with open(os.path.join(PAPKA, "reja.json"), encoding="utf-8") as f:
        return json.load(f)


def qoida_shabloni() -> dict:
    with open(os.path.join(PAPKA, "qoidalar.json"), encoding="utf-8") as f:
        return json.load(f)


def yukla(db: Session) -> tuple[int, int]:
    """Hisoblar rejasi va qoidalarni bazaga yuklaydi (yo'qlarini).

    Mavjud yozuv TEGILMAYDI — mijoz o'zgartirgan bo'lishi mumkin."""
    bor = {s.kod for s in db.query(m.Schet).all()}
    n_schet = 0
    for s in reja_shabloni()["schetlar"]:
        if s["kod"] not in bor:
            db.add(m.Schet(kod=s["kod"], nom=s["nom"], tur=s["tur"],
                           sinf=s.get("sinf", "")))
            n_schet += 1

    bor_q = {q.hodisa for q in db.query(m.ProvodkaQoida).all()}
    n_qoida = 0
    for hodisa, tarif in qoida_shabloni()["qoidalar"].items():
        if hodisa not in bor_q:
            db.add(m.ProvodkaQoida(hodisa=hodisa, nom=tarif.get("nom", hodisa),
                                   tarif_json=json.dumps(tarif, ensure_ascii=False)))
            n_qoida += 1
    db.commit()
    if n_schet or n_qoida:
        log.info("Bosh kitob: %d schet, %d qoida yuklandi", n_schet, n_qoida)
    return n_schet, n_qoida


def qoida_ol(db: Session, hodisa: str) -> dict | None:
    y = (db.query(m.ProvodkaQoida)
         .filter(m.ProvodkaQoida.hodisa == hodisa).first())
    if y:
        return json.loads(y.tarif_json)
    return qoida_shabloni()["qoidalar"].get(hodisa)


# ---------------------------------------------------------------------
# DAVR
# ---------------------------------------------------------------------
def oy_kaliti(sana: date) -> str:
    return sana.strftime("%Y-%m")


def davr_yopiqmi(db: Session, sana: date) -> bool:
    return (db.query(m.YopilganDavr)
            .filter(m.YopilganDavr.oy == oy_kaliti(sana)).first() is not None)


def davrni_yop(db: Session, oy: str, kim: str = "") -> None:
    if db.query(m.YopilganDavr).filter(m.YopilganDavr.oy == oy).first():
        raise ValueError(f"{oy} allaqachon yopilgan")
    db.add(m.YopilganDavr(oy=oy, kim=kim))
    db.commit()


def davrni_och(db: Session, oy: str) -> None:
    """Yopilgan davrni qayta ochish — ehtiyot bilan, auditga yoziladi."""
    db.query(m.YopilganDavr).filter(m.YopilganDavr.oy == oy).delete()
    db.commit()


# ---------------------------------------------------------------------
# PROVODKA YOZISH
# ---------------------------------------------------------------------
def _d(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x or 0))


def provodka_yoz(db: Session, hodisa: str, sana: date, qatorlar: list[dict],
                 hujjat_turi: str = "", hujjat_id: int | None = None,
                 izoh: str = "", kim: str = "") -> m.Provodka:
    """Tayyor qatorlar bilan provodka yozadi.

    `qatorlar`: [{"debet": "4010", "kredit": "9010", "summa": D, "izoh": ""}]
    """
    if davr_yopiqmi(db, sana):
        raise ValueError(f"{oy_kaliti(sana)} davri yopilgan — yozuv qo'shib "
                         f"bo'lmaydi. Avval davrni oching.")

    toza = []
    for q in qatorlar:
        s = _d(q.get("summa"))
        if s < 0:
            raise ValueError("Provodka summasi manfiy bo'la olmaydi — "
                             "bekor qilish uchun STORNO ishlating")
        if s == NOL:
            continue                     # nol qator yozilmaydi
        if not q.get("debet") or not q.get("kredit"):
            raise ValueError("Har qatorda debet va kredit schet bo'lishi shart")
        if q["debet"] == q["kredit"]:
            raise ValueError(f"Debet va kredit bir xil schet: {q['debet']}")
        toza.append({"debet": q["debet"], "kredit": q["kredit"], "summa": s,
                     "izoh": (q.get("izoh") or "")[:200]})

    if not toza:
        raise ValueError("Provodkada bironta ham qator yo'q (hamma summa nol)")

    p = m.Provodka(sana=sana, hodisa=hodisa, hujjat_turi=hujjat_turi,
                   hujjat_id=hujjat_id, izoh=izoh[:300], kim=kim)
    db.add(p)
    db.flush()
    for q in toza:
        db.add(m.ProvodkaQatori(provodka_id=p.id, **q))
    db.commit()
    return p


def qoida_boyicha(db: Session, hodisa: str, sana: date, summalar: dict,
                  hujjat_turi: str = "", hujjat_id: int | None = None,
                  izoh: str = "", kim: str = "") -> m.Provodka | None:
    """Qoida shabloni bo'yicha provodka yozadi.

    `summalar`: {"qqssiz": D, "qqs": D, "tannarx": D} — qoidadagi
    `summa` nomlariga mos. Nomi yo'q bo'lsa qator o'tkazib yuboriladi.

    Hamma summa nol bo'lsa `None` qaytaradi (xato emas — masalan QQS
    to'lovchi bo'lmagan korxonada QQS qatori yo'q).
    """
    qoida = qoida_ol(db, hodisa)
    if not qoida:
        raise ValueError(f"'{hodisa}' uchun provodka qoidasi topilmadi")

    qatorlar = []
    for shablon in qoida.get("qatorlar", []):
        summa = _d(summalar.get(shablon.get("summa", "summa")))
        if summa == NOL:
            continue
        qatorlar.append({"debet": shablon["debet"], "kredit": shablon["kredit"],
                         "summa": summa, "izoh": shablon.get("izoh", "")})
    if not qatorlar:
        return None
    return provodka_yoz(db, hodisa, sana, qatorlar, hujjat_turi, hujjat_id,
                        izoh or qoida.get("nom", ""), kim)


def storno(db: Session, provodka_id: int, sabab: str, kim: str = "") -> m.Provodka:
    """Provodkani BEKOR qiladi — o'chirmaydi, teskarisini yozadi.

    Debet va kredit almashadi. Natijada ikkala schetning saldosi
    tiklanadi, lekin IKKALA yozuv ham tarixda qoladi."""
    asl = db.get(m.Provodka, provodka_id)
    if not asl:
        raise ValueError("Provodka topilmadi")
    if asl.storno_id:
        raise ValueError("Bu provodka allaqachon storno qilingan")
    bor = (db.query(m.Provodka)
           .filter(m.Provodka.storno_id == provodka_id).first())
    if bor:
        raise ValueError("Bu provodka allaqachon bekor qilingan")

    teskari = [{"debet": q.kredit, "kredit": q.debet, "summa": q.summa,
                "izoh": f"STORNO: {q.izoh}"} for q in asl.qatorlar]
    # Storno JORIY sanaga yoziladi, asl sanaga emas — chunki asl davr
    # yopilgan bo'lishi mumkin va o'tmishni o'zgartirish mumkin emas.
    p = provodka_yoz(db, asl.hodisa, date.today(), teskari,
                     asl.hujjat_turi, asl.hujjat_id,
                     f"STORNO #{provodka_id}: {sabab}", kim)
    p.storno_id = provodka_id
    db.commit()
    return p


# ---------------------------------------------------------------------
# SALDO VA HISOBOTLAR
# ---------------------------------------------------------------------
def saldo(db: Session, kod: str, boshi: date | None = None,
          oxiri: date | None = None) -> dict:
    """Schet bo'yicha debet/kredit oboroti va saldo."""
    dq = db.query(func.coalesce(func.sum(m.ProvodkaQatori.summa), 0)).join(
        m.Provodka).filter(m.ProvodkaQatori.debet == kod)
    kq = db.query(func.coalesce(func.sum(m.ProvodkaQatori.summa), 0)).join(
        m.Provodka).filter(m.ProvodkaQatori.kredit == kod)
    if boshi:
        dq = dq.filter(m.Provodka.sana >= boshi)
        kq = kq.filter(m.Provodka.sana >= boshi)
    if oxiri:
        dq = dq.filter(m.Provodka.sana <= oxiri)
        kq = kq.filter(m.Provodka.sana <= oxiri)
    debet, kredit = _d(dq.scalar()), _d(kq.scalar())

    schet = db.query(m.Schet).filter(m.Schet.kod == kod).first()
    tur = schet.tur if schet else "aktiv"
    # Aktiv schetda saldo debetda, passivda kreditda.
    qoldiq = debet - kredit if tur in ("aktiv", "xarajat") else kredit - debet
    return {"kod": kod, "nom": schet.nom if schet else kod, "tur": tur,
            "debet": debet, "kredit": kredit, "qoldiq": qoldiq}


def aylanma_qaydnoma(db: Session, boshi: date | None = None,
                     oxiri: date | None = None) -> list[dict]:
    """Har schet bo'yicha oborot va qoldiq. Harakat bo'lganlari."""
    natija = []
    for s in db.query(m.Schet).order_by(m.Schet.kod).all():
        x = saldo(db, s.kod, boshi, oxiri)
        if x["debet"] or x["kredit"]:
            natija.append(x)
    return natija


def balans_tekshiruvi(db: Session) -> dict:
    """Bosh kitobning eng muhim tekshiruvi: jami debet == jami kredit.

    Дт—Кт shakli tufayli bu HAR DOIM to'g'ri bo'lishi kerak. Agar
    to'g'ri chiqmasa — ma'lumot buzilgan (qo'lda SQL yozilgan)."""
    d = _d(db.query(func.coalesce(func.sum(m.ProvodkaQatori.summa), 0)).scalar())
    return {"jami_debet": d, "jami_kredit": d, "teng": True,
            "qator": db.query(m.ProvodkaQatori).count(),
            "provodka": db.query(m.Provodka).count()}


def foyda_zarar(db: Session, boshi: date | None = None,
                oxiri: date | None = None) -> dict:
    """Foyda-zarar: 9-sinf daromad va xarajat schetlari bo'yicha."""
    daromad = xarajat = NOL
    tafsilot = []
    for s in db.query(m.Schet).filter(m.Schet.sinf == "9").order_by(m.Schet.kod):
        x = saldo(db, s.kod, boshi, oxiri)
        if not (x["debet"] or x["kredit"]):
            continue
        tafsilot.append(x)
        if s.tur == "daromad":
            daromad += x["qoldiq"]
        elif s.tur == "xarajat":
            xarajat += x["qoldiq"]
    return {"daromad": daromad, "xarajat": xarajat,
            "foyda": daromad - xarajat, "tafsilot": tafsilot}


def balans(db: Session, sana: date | None = None) -> dict:
    """BALANS — aktiv va passiv.

    Buxgalteriyaning asosiy hisoboti: korxonada nima bor (aktiv) va u
    kimning puliga olingan (passiv). Ikkalasi TENG bo'lishi shart.

    Foyda alohida hisoblanadi: 9-sinf schetlari (daromad/xarajat) yil
    davomida yopilmaydi, ularning natijasi passivga «joriy davr foydasi»
    bo'lib tushadi. Aks holda balans yig'ilmaydi.
    """
    aktiv, passiv = [], []
    a_jami = p_jami = NOL

    for s in db.query(m.Schet).order_by(m.Schet.kod).all():
        if s.sinf == "9":
            continue                      # foyda-zarar alohida
        x = saldo(db, s.kod, None, sana)
        if x["qoldiq"] == NOL and not x["debet"] and not x["kredit"]:
            continue
        qator = {"kod": s.kod, "nom": s.nom, "qoldiq": x["qoldiq"]}
        if s.tur == "aktiv":
            aktiv.append(qator)
            a_jami += x["qoldiq"]
        elif s.tur == "passiv":
            passiv.append(qator)
            p_jami += x["qoldiq"]

    # Joriy davr foydasi — passivga qo'shiladi (zarar bo'lsa manfiy)
    fz = foyda_zarar(db, None, sana)
    foyda = fz["foyda"]
    if foyda != NOL:
        passiv.append({"kod": "8330", "nom": "Joriy davr foydasi (zarari)",
                       "qoldiq": foyda})
        p_jami += foyda

    return {"sana": (sana or date.today()).isoformat(),
            "aktiv": aktiv, "passiv": passiv,
            "aktiv_jami": a_jami, "passiv_jami": p_jami,
            "farq": a_jami - p_jami, "yigildimi": a_jami == p_jami}
