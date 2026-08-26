"""Soha profili — konstruktorning o'zagi.

Bu yerda mijozning biznes turi ko'riladi, almashtiriladi va yangisi
qo'shiladi. Muhimi: profil qo'shish uchun **kod yozilmaydi** — JSON
ta'rif yuboriladi, xolos. 4-bosqichda AI agent aynan shu endpointga
suhbatdan chiqargan ta'rifni yuboradi.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..auth import get_user, require_roles
from .. import models as m
from .. import domain

router = APIRouter(prefix="/api/soha", tags=["Soha profili"])


def _chiqar(p: m.SohaProfil) -> dict:
    tarif = json.loads(p.tarif_json)
    return {
        "kalit": p.kalit, "nom": p.nom, "faol": p.faol,
        "izoh": tarif.get("izoh", ""),
        "maydonlar": tarif.get("maydonlar", []),
        "narx_usuli": tarif.get("narx", {}).get("usul", "qolda"),
    }


def _shablondan(kalit: str, tarif: dict) -> dict:
    """Fayldagi shablonni ro'yxat uchun bir xil ko'rinishga keltiradi."""
    return {
        "kalit": kalit, "nom": tarif.get("nom", kalit), "faol": False,
        "izoh": tarif.get("izoh", ""),
        "maydonlar": tarif.get("maydonlar", []),
        "narx_usuli": tarif.get("narx", {}).get("usul", "qolda"),
        # Bazada YO'Q — hali ishlatilmagan platforma shabloni.
        # Faollashtirilganda bazaga ko'chiriladi.
        "shablon": True,
    }


@router.get("/profillar")
def profillar(db: Session = Depends(get_db), user=Depends(get_user)):
    """Mijozning profillari + platforma shablonlari.

    NEGA IKKI MANBA. Ilgari yangi akkaunt ochilganda 30 ta soha
    profili ham uning bazasiga ko'chirilardi — bilyard klubining
    bazasida «Beton zavodi» va «Poyabzal sexi» yotardi. Endi bazaga
    faqat mijoz ISHLATGANI tushadi, qolgani fayllarda turadi va shu
    yerda ro'yxatga qo'shiladi. Ya'ni tanlov kamaymadi, faqat begona
    ma'lumot mijoz bazasiga yozilmaydi.
    """
    oz = [_chiqar(p) for p in db.query(m.SohaProfil).order_by(m.SohaProfil.id)]
    bor = {x["kalit"] for x in oz}
    shablonlar = [_shablondan(k, t)
                  for k, t in sorted(domain.shablonlar().items(),
                                     key=lambda x: x[1].get("nom", x[0]))
                  if k not in bor]
    return oz + shablonlar


@router.get("/bolimlar")
def bolimlar_royxati(db: Session = Depends(get_db), user=Depends(get_user)):
    """Yon menyu — SHU akkaunt uchun.

    Ilgari menyu frontendda qotirilgan edi va har biznes karton sexining
    bo'limlarini ko'rardi. Endi ro'yxat shu yerdan keladi: akkaunt
    tanlovi -> modul standarti -> hammasi (eski xatti-harakat).

    Faol bo'lmagan bo'limlar ham qaytariladi (`faol: false`) — mijoz
    sozlamalarda ularni ko'rib, kerakligini belgilaydi.
    """
    from .. import bolimlar as b
    return {"bolimlar": b.toliq(db, domain.profil().modul.kalit, user.role),
            "modul": domain.profil().modul.kalit}


class BolimlarIn(BaseModel):
    kalitlar: list[str]


@router.put("/bolimlar")
def bolimlar_saqla(data: BolimlarIn, db: Session = Depends(get_db),
                   user=Depends(require_roles("Rahbar"))):
    """Mijoz o'z menyusini yig'adi — kod yozilmaydi.

    AI sozlash yordamchisi ham SHU endpointga yuboradi: suhbatdan
    chiqqan ro'yxat taklif qilinadi, tugmani ODAM bosadi.

    `dash`, `ai`, `set`, `help` olib tashlanmaydi — ularsiz mijoz
    tizimga qaytib kira olmaydi (`bolimlar.MAJBURIY`).
    """
    from .. import bolimlar as b
    tanlov = b.saqla(db, data.kalitlar)
    db.add(m.AuditLog(who=user.name, action="Bo'limlar o'zgartirildi",
                      detail=", ".join(tanlov)))
    db.commit()
    return {"ok": True, "bolimlar": tanlov}


@router.get("/rollar")
def rollar_royxati(db: Session = Depends(get_db), user=Depends(get_user)):
    """Shu akkauntdagi lavozimlar va ularning huquq asosi.

    Mijoz o'z atamasini ishlatadi («Barmen», «Administrator»), huquq
    esa beshta asosdan biriga bog'lanadi. Ro'yxat yo'q bo'lsa beshta
    asos nomining o'zi qaytadi — bugungi xatti-harakat.
    """
    from .. import rollar as r
    return {"rollar": r.royxat(db), "asoslar": r.ASOSLAR}


class RollarIn(BaseModel):
    rollar: list[dict]          # [{"nom": "Barmen", "asos": "Menejer"}]


@router.put("/rollar")
def rollar_saqla(data: RollarIn, db: Session = Depends(get_db),
                 user=Depends(require_roles("Rahbar"))):
    """Mijoz o'z lavozim nomlarini belgilaydi.

    HUQUQ O'YLAB TOPILMAYDI: har nom beshta asosdan biriga bog'lanadi.
    Rahbar asosidagi rol har doim qoldiriladi — aks holda akkauntni
    boshqaradigan odam qolmaydi.
    """
    from .. import rollar as r
    tanlov = r.saqla(db, data.rollar)
    db.add(m.AuditLog(who=user.name, action="Rollar o'zgartirildi",
                      detail=", ".join(f"{x['nom']}<-{x['asos']}" for x in tanlov)))
    db.commit()
    return {"ok": True, "rollar": tanlov}


@router.get("/joriy")
def joriy(user=Depends(get_user)):
    """Hozir ishlayotgan profil — maydonlari bilan.

    Frontend shu ro'yxatdan buyurtma formasini yasashi mumkin: qaysi
    maydon, qanday turda, qanday variantlar. Shunda forma ham sohaga
    moslashadi va karton maydonlari kodda qotib qolmaydi.
    """
    p = domain.profil()
    return {
        "kalit": p.kalit, "nom": p.nom, "izoh": p.izoh,
        "narx_usuli": p.narx.get("usul", "qolda"),
        "xomashyo_hisobi": bool(p.xomashyo),
        # Miqdor o'lchovi: karton «dona», beton «m³», montaj «m²».
        # Formadagi «Тираж, дона» yozuvi shundan chiqadi.
        "birlik": p.birlik,
        "kasrli": p.kasrli,
        "min_miqdor": float(p.min_miqdor),
        "max_miqdor": float(p.max_miqdor),
        # Retsept (BOM): 1 buyurtmaga qaysi material qancha ketadi.
        # Frontend shundan «ishlab chiqarishga yetadimi» ni ko'rsatishi mumkin.
        "retsept": p.retsept,
        "modul": {"kalit": p.modul.kalit, "nom": p.modul.nom, "izoh": p.modul.izoh},
        # Statuslar ham shu yerda: frontend treker bosqichlarini qattiq
        # yozmasdan, ish tartibidan chizishi kerak.
        "statuslar": [{"nom": st.nom, "mano": st.mano,
                       "keyingi": st.keyingi, "rollar": st.rollar}
                      for st in p.modul.statuslar],
        "maydonlar": [{
            "kalit": md.kalit, "nom": md.nom, "tur": md.tur,
            "birlik": md.birlik, "standart": md.standart,
            "min": md.min, "max": md.max, "variantlar": md.variantlar,
            "majburiy": md.majburiy, "hisoblanadi": md.hisoblanadi,
        } for md in p.maydonlar],
    }


class FaollashtirishIn(BaseModel):
    kalit: str


@router.post("/faollashtirish")
def faollashtirish(data: FaollashtirishIn, db: Session = Depends(get_db),
                   user=Depends(require_roles("Rahbar"))):
    """Faol profilni almashtiradi.

    DIQQAT: mavjud buyurtmalarning `attributes` i ESKI profil maydonlari
    bilan yozilgan — ular yangi profilda ko'rinmay qoladi (o'chmaydi,
    faqat ko'rsatilmaydi). Shuning uchun buyurtmalar bor bazada profil
    almashtirish real ish emas, sozlash bosqichidagi amaldir.
    """
    yangi = db.query(m.SohaProfil).filter(m.SohaProfil.kalit == data.kalit).first()
    if not yangi:
        # Bazada yo'q, lekin platforma shabloni bo'lishi mumkin —
        # o'sha paytda bazaga ko'chiriladi («kerak bo'lganda yuklash»).
        tarif = domain.shablonlar().get(data.kalit)
        if not tarif:
            raise HTTPException(404, f"'{data.kalit}' profili topilmadi")
        yangi = m.SohaProfil(kalit=data.kalit, nom=tarif.get("nom", data.kalit),
                             tarif_json=json.dumps(tarif, ensure_ascii=False),
                             faol=False)
        db.add(yangi)
        db.flush()
    for p in db.query(m.SohaProfil).all():
        p.faol = (p.id == yangi.id)
    db.add(m.AuditLog(who=user.name, action="Soha profili almashtirildi",
                      detail=f"{yangi.nom} ({yangi.kalit})"))
    db.commit()
    domain.qayta_yukla(db)
    return {"ok": True, "faol": _chiqar(yangi),
            "ogohlantirish": "Eski buyurtmalar oldingi profil maydonlari "
                             "bilan yozilgan — ular ko'rinmay qolishi mumkin"}


class ProfilIn(BaseModel):
    tarif: dict


@router.post("/profillar")
def profil_qosh(data: ProfilIn, db: Session = Depends(get_db),
                user=Depends(require_roles("Rahbar"))):
    """Yangi soha profili qo'shadi yoki mavjudini yangilaydi — KOD YOZMASDAN.

    Ta'rif tuzilishi `app/profiles/*.json` bilan bir xil. Yuborilgan
    ta'rif darrov tekshiriladi: buzuq profil bazaga tushmaydi.
    """
    try:
        tekshirilgan = domain.Profil(data.tarif)
    except (KeyError, ValueError, TypeError) as e:
        raise HTTPException(400, f"Profil ta'rifi noto'g'ri: {e}")

    mavjud = db.query(m.SohaProfil).filter(
        m.SohaProfil.kalit == tekshirilgan.kalit).first()
    tarif_json = json.dumps(data.tarif, ensure_ascii=False)
    if mavjud:
        mavjud.nom, mavjud.tarif_json = tekshirilgan.nom, tarif_json
        # Belgilaymiz: bundan keyin dastur yangilanganda shablon buni
        # ustidan yozmaydi — mijozning sozlamasi saqlanib qoladi.
        mavjud.ozgartirilgan = True
        harakat = "Soha profili yangilandi"
    else:
        db.add(m.SohaProfil(kalit=tekshirilgan.kalit, nom=tekshirilgan.nom,
                            tarif_json=tarif_json, faol=False,
                            ozgartirilgan=True))
        harakat = "Soha profili qo'shildi"
    db.add(m.AuditLog(who=user.name, action=harakat, detail=tekshirilgan.kalit))
    db.commit()
    if mavjud and mavjud.faol:
        domain.qayta_yukla(db)   # faol profil o'zgardi — keshni yangilaymiz
    return {"ok": True, "kalit": tekshirilgan.kalit,
            "maydonlar": len(tekshirilgan.maydonlar)}
