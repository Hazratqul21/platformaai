"""BUXGALTERIYA — hisoblar rejasi, provodkalar, hisobotlar.

Rollar: Buxgalter va Rahbar. Boshqalar ko'ra olmaydi — bu yerda
korxonaning butun moliyaviy manzarasi turadi.

⚠️ Bu bo'lim HOZIRCHA mavjud hisob-kitobga TA'SIR QILMAYDI. GL parallel
yoziladi va `tools/butunlik.py` ikkalasi mos kelayotganini tekshiradi.
Faqat shundan keyin hisobotlar GL ga o'tkaziladi (docs/06 bosqich B).
"""
import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import require_roles
from ..db import get_db
from .. import models as m
from ..hisob import xizmat as gl

router = APIRouter(prefix="/api/hisob", tags=["Buxgalteriya"])
buxgalter = require_roles("Rahbar", "Buxgalter")


def _f(x) -> float:
    return float(x or 0)


# --------------------------- HISOBLAR REJASI -------------------------
@router.get("/schetlar")
def schetlar(db: Session = Depends(get_db), user=Depends(buxgalter)):
    return {"schetlar": [
        {"kod": s.kod, "nom": s.nom, "tur": s.tur, "sinf": s.sinf,
         "faol": s.faol}
        for s in db.query(m.Schet).order_by(m.Schet.kod).all()],
        "asos": gl.reja_shabloni()["asos"],
        "ogohlantirish": gl.reja_shabloni()["ogohlantirish"]}


class SchetIn(BaseModel):
    kod: str
    nom: str
    tur: str          # aktiv / passiv / daromad / xarajat
    sinf: str = ""


@router.post("/schet")
def schet_saqla(data: SchetIn, db: Session = Depends(get_db),
                user=Depends(buxgalter)):
    """Yangi schet qo'shadi yoki mavjudini tahrirlaydi."""
    if data.tur not in ("aktiv", "passiv", "daromad", "xarajat"):
        raise HTTPException(400, "Tur: aktiv/passiv/daromad/xarajat")
    kod = (data.kod or "").strip()
    if not kod.isdigit():
        raise HTTPException(400, "Schet kodi raqamlardan iborat bo'lsin")
    s = db.query(m.Schet).filter(m.Schet.kod == kod).first()
    if s:
        s.nom, s.tur, s.sinf = data.nom, data.tur, data.sinf or kod[0]
    else:
        db.add(m.Schet(kod=kod, nom=data.nom, tur=data.tur,
                       sinf=data.sinf or kod[0]))
    db.add(m.AuditLog(who=user.name, action="Schet o'zgardi",
                      detail=f"{kod} · {data.nom}"))
    db.commit()
    return {"ok": True, "kod": kod}


# --------------------------- QOIDALAR --------------------------------
@router.get("/qoidalar")
def qoidalar(db: Session = Depends(get_db), user=Depends(buxgalter)):
    """Har hodisa qaysi provodkani yozishi — mijoz o'zgartira oladi."""
    shablon = gl.qoida_shabloni()
    bor = {q.hodisa: q for q in db.query(m.ProvodkaQoida).all()}
    natija = []
    for hodisa, tarif in shablon["qoidalar"].items():
        y = bor.get(hodisa)
        joriy = json.loads(y.tarif_json) if y else tarif
        natija.append({
            "hodisa": hodisa, "nom": joriy.get("nom", hodisa),
            "izoh": joriy.get("izoh", ""), "qatorlar": joriy.get("qatorlar", []),
            "ozgartirilgan": bool(y and json.loads(y.tarif_json) != tarif)})
    return {"qoidalar": natija, "summa_nomlari": shablon["summa_nomlari"]}


class QoidaIn(BaseModel):
    qatorlar: list[dict]


@router.put("/qoida/{hodisa}")
def qoida_saqla(hodisa: str, data: QoidaIn, db: Session = Depends(get_db),
                user=Depends(buxgalter)):
    shablon = gl.qoida_shabloni()["qoidalar"]
    if hodisa not in shablon:
        raise HTTPException(404, "Bunday hodisa yo'q")
    kodlar = {s.kod for s in db.query(m.Schet).all()}
    for q in data.qatorlar:
        if q.get("debet") not in kodlar or q.get("kredit") not in kodlar:
            raise HTTPException(
                400, f"Schet topilmadi: {q.get('debet')} yoki {q.get('kredit')}")
        if q.get("debet") == q.get("kredit"):
            raise HTTPException(400, "Debet va kredit bir xil bo'la olmaydi")

    tarif = dict(shablon[hodisa])
    tarif["qatorlar"] = data.qatorlar
    y = db.query(m.ProvodkaQoida).filter(m.ProvodkaQoida.hodisa == hodisa).first()
    if y:
        y.tarif_json = json.dumps(tarif, ensure_ascii=False)
        y.kim, y.ozgartirilgan = user.name, datetime.utcnow()
    else:
        db.add(m.ProvodkaQoida(hodisa=hodisa, nom=tarif.get("nom", hodisa),
                               tarif_json=json.dumps(tarif, ensure_ascii=False),
                               kim=user.name))
    db.add(m.AuditLog(who=user.name, action="Provodka qoidasi o'zgardi",
                      detail=hodisa))
    db.commit()
    return {"ok": True, "hodisa": hodisa}


# --------------------------- PROVODKALAR -----------------------------
@router.get("/provodkalar")
def provodkalar(boshi: str | None = None, oxiri: str | None = None,
                nechta: int = 100, db: Session = Depends(get_db),
                user=Depends(buxgalter)):
    q = db.query(m.Provodka).order_by(m.Provodka.sana.desc(), m.Provodka.id.desc())
    if boshi:
        q = q.filter(m.Provodka.sana >= date.fromisoformat(boshi))
    if oxiri:
        q = q.filter(m.Provodka.sana <= date.fromisoformat(oxiri))
    return {"provodkalar": [{
        "id": p.id, "sana": p.sana.isoformat(), "hodisa": p.hodisa,
        "izoh": p.izoh, "kim": p.kim, "storno_id": p.storno_id,
        "hujjat": f"{p.hujjat_turi}#{p.hujjat_id}" if p.hujjat_id else "",
        "qatorlar": [{"debet": x.debet, "kredit": x.kredit,
                      "summa": _f(x.summa), "izoh": x.izoh} for x in p.qatorlar],
        "jami": _f(sum(x.summa for x in p.qatorlar)),
    } for p in q.limit(min(nechta, 500)).all()]}


class ProvodkaIn(BaseModel):
    sana: str
    qatorlar: list[dict]
    izoh: str = ""


@router.post("/provodka")
def provodka_qolda(data: ProvodkaIn, db: Session = Depends(get_db),
                   user=Depends(buxgalter)):
    """Qo'lda provodka (buxgalter tuzatishi, boshlang'ich qoldiq)."""
    try:
        p = gl.provodka_yoz(db, "qolda", date.fromisoformat(data.sana),
                            data.qatorlar, hujjat_turi="qolda",
                            izoh=data.izoh, kim=user.name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "id": p.id}


class StornoIn(BaseModel):
    sabab: str


@router.post("/provodka/{provodka_id}/storno")
def provodka_storno(provodka_id: int, data: StornoIn,
                    db: Session = Depends(get_db), user=Depends(buxgalter)):
    """Provodkani bekor qiladi — O'CHIRMAYDI, teskarisini yozadi."""
    if not (data.sabab or "").strip():
        raise HTTPException(400, "Storno sababi yozilishi shart")
    try:
        p = gl.storno(db, provodka_id, data.sabab, kim=user.name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "storno_id": p.id}


# --------------------------- HISOBOTLAR ------------------------------
def _sana(x: str | None):
    return date.fromisoformat(x) if x else None


@router.get("/qaydnoma")
def qaydnoma(boshi: str | None = None, oxiri: str | None = None,
             db: Session = Depends(get_db), user=Depends(buxgalter)):
    """Aylanma qaydnoma — har schet bo'yicha oborot va qoldiq."""
    qatorlar = gl.aylanma_qaydnoma(db, _sana(boshi), _sana(oxiri))
    return {"qatorlar": [{**x, "debet": _f(x["debet"]),
                          "kredit": _f(x["kredit"]),
                          "qoldiq": _f(x["qoldiq"])} for x in qatorlar],
            "jami_debet": _f(sum(x["debet"] for x in qatorlar)),
            "jami_kredit": _f(sum(x["kredit"] for x in qatorlar))}


@router.get("/foyda-zarar")
def foyda_zarar(boshi: str | None = None, oxiri: str | None = None,
                db: Session = Depends(get_db), user=Depends(buxgalter)):
    r = gl.foyda_zarar(db, _sana(boshi), _sana(oxiri))
    return {"daromad": _f(r["daromad"]), "xarajat": _f(r["xarajat"]),
            "foyda": _f(r["foyda"]),
            "tafsilot": [{**x, "debet": _f(x["debet"]), "kredit": _f(x["kredit"]),
                          "qoldiq": _f(x["qoldiq"])} for x in r["tafsilot"]]}


@router.get("/balans-tekshiruvi")
def balans_tekshiruvi(db: Session = Depends(get_db), user=Depends(buxgalter)):
    r = gl.balans_tekshiruvi(db)
    return {**r, "jami_debet": _f(r["jami_debet"]),
            "jami_kredit": _f(r["jami_kredit"])}


# --------------------------- DAVR ------------------------------------
@router.get("/davrlar")
def davrlar(db: Session = Depends(get_db), user=Depends(buxgalter)):
    return {"yopilgan": [{"oy": d.oy, "kim": d.kim,
                          "yopilgan": d.yopilgan.isoformat()}
                         for d in db.query(m.YopilganDavr)
                         .order_by(m.YopilganDavr.oy.desc()).all()]}


class DavrIn(BaseModel):
    oy: str           # "2026-08"


@router.post("/davr/yop")
def davr_yop(data: DavrIn, db: Session = Depends(get_db),
             user=Depends(require_roles("Rahbar", "Buxgalter"))):
    try:
        gl.davrni_yop(db, data.oy, kim=user.name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.add(m.AuditLog(who=user.name, action="Davr yopildi", detail=data.oy))
    db.commit()
    return {"ok": True, "oy": data.oy}


@router.post("/davr/och")
def davr_och(data: DavrIn, db: Session = Depends(get_db),
             user=Depends(require_roles("Rahbar"))):
    """Yopilgan davrni qayta ochadi — faqat Rahbar, auditga yoziladi."""
    gl.davrni_och(db, data.oy)
    db.add(m.AuditLog(who=user.name, action="Davr QAYTA OCHILDI",
                      detail=f"{data.oy} — hisobot allaqachon topshirilgan "
                             f"bo'lishi mumkin"))
    db.commit()
    return {"ok": True, "oy": data.oy}


@router.get("/balans")
def balans(sana: str | None = None, db: Session = Depends(get_db),
           user=Depends(buxgalter)):
    """Balans — aktiv va passiv. Ikkalasi teng bo'lishi shart."""
    r = gl.balans(db, _sana(sana))
    return {
        "sana": r["sana"],
        "aktiv": [{**x, "qoldiq": _f(x["qoldiq"])} for x in r["aktiv"]],
        "passiv": [{**x, "qoldiq": _f(x["qoldiq"])} for x in r["passiv"]],
        "aktiv_jami": _f(r["aktiv_jami"]), "passiv_jami": _f(r["passiv_jami"]),
        "farq": _f(r["farq"]), "yigildimi": r["yigildimi"]}


@router.get("/boshlangich-qoldiq")
def boshlangich_qoldiq_korish(db: Session = Depends(get_db), user=Depends(buxgalter)):
    """Sehrgar ko'rsatishi uchun: hozirgi holat + kiritilganmi."""
    q = gl.boshlangich_qoldiq_hisobla(db)
    return {"bor": gl.boshlangich_qoldiq_bormi(db),
            "mijoz_qarzi": _f(q["mijoz_qarzi"]), "mijoz_avansi": _f(q["mijoz_avansi"]),
            "yetkazuvchi_qarzi": _f(q["yetkazuvchi_qarzi"]),
            "kassa": _f(q["kassa"]), "ombor": _f(q["ombor"])}


class BoshlangichIn(BaseModel):
    sana: str | None = None


@router.post("/boshlangich-qoldiq")
def boshlangich_qoldiq_kirit(data: BoshlangichIn, db: Session = Depends(get_db),
                             user=Depends(require_roles("Rahbar", "Buxgalter"))):
    """Ochilish provodkasini yozadi — balans haqiqiy raqam ko'rsatadi."""
    try:
        p = gl.boshlangich_qoldiq_yoz(db, _sana(data.sana), kim=user.name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.add(m.AuditLog(who=user.name, action="Boshlang'ich qoldiq kiritildi",
                      detail=f"provodka #{p.id}"))
    db.commit()
    return {"ok": True, "provodka_id": p.id}
