"""GenUI — AI matn emas, KO'RINISH qaytaradi.

MUAMMO: agent «Sizda 28 qarzdor bor, eng kattasi 50 mln» deb yozadi.
Foydalanuvchi buni o'qib, keyin Moliya bo'limiga o'tib, qidirib topishi
kerak. Ya'ni AI bilgan narsani ko'rsata olmaydi.

YECHIM: agent javobiga KOMPONENT qo'shadi — jadval, ko'rsatkich, diagramma.
Frontend ularni haqiqiy UI qilib chizadi.

╔══════════════════════════════════════════════════════════════════════╗
║  NEGA 8 TA PRIMITIV, HAR BO'LIMGA ALOHIDA KARTA EMAS                 ║
║                                                                       ║
║  Tizimda 11 bo'lim bor: buyurtma, mijoz, ombor, xarid, xodim,        ║
║  moliya, kassa, hisobot, katalog, konstruktor, soha profili.          ║
║  Har biriga «karta» yasalsa — 11 ta komponent, va yangi bo'lim        ║
║  qo'shilganda YANA kod yozish kerak. Bu platformaning butun           ║
║  g'oyasiga («yangi soha — kodga tegilmaydi») zid.                     ║
║                                                                       ║
║  Aslida bu 11 bo'lim ekranda atigi bir necha SHAKLDA ko'rinadi:       ║
║  ro'yxat, ko'rsatkich, tafsilot, taqsimot. Shuning uchun primitivlar  ║
║  MA'LUMOT SHAKLI bo'yicha ajratilgan, BO'LIM bo'yicha emas. Yangi     ║
║  bo'lim qo'shilsa — o'sha primitivlar qayta ishlatiladi.              ║
╚══════════════════════════════════════════════════════════════════════╝

XAVFSIZLIK: komponentlar MODELDAN keladi, ya'ni ishonchsiz manba.
Shuning uchun har biri shu yerda TEKSHIRILADI — noma'lum tur, ortiqcha
maydon yoki juda katta ro'yxat frontendga umuman yetib bormaydi.
Frontend esa matnni faqat `textContent` bilan qo'yadi (HTML sifatida
talqin qilinmaydi).
"""
from decimal import Decimal

# Bitta javobda nechta komponent va har birida nechta qator bo'lishi
# mumkin. Model «hamma buyurtmani ko'rsat» deb 10 000 qator yuborsa
# brauzer qotib qoladi.
MAX_KOMPONENT = 6
MAX_QATOR = 60
MAX_USTUN = 8
MAX_MATN = 300


class KomponentXato(ValueError):
    """Model noto'g'ri komponent yubordi — javob rad etiladi."""


# =====================================================================
#  PRIMITIVLAR
# =====================================================================

TURLAR = {
    # 1. Har qanday RO'YXAT: buyurtmalar, mijozlar, qarzdorlar, ombor,
    #    xaridlar, xodimlar, kassa, harakatlar, katalog... Tizimning
    #    aksariyat ekrani aslida shu.
    "jadval": {
        "izoh": "Ustunli ro'yxat. Har qatorda ixtiyoriy holat belgisi va amal.",
        "maydonlar": {"sarlavha", "ustunlar", "qatorlar", "izoh"},
    },
    # 2. KPI plitalari: kassa qoldig'i, oylik tushum, qarz, buyurtma soni
    "korsatkichlar": {
        "izoh": "Katta raqamlar qatori. Har biri: nom, qiymat, ixtiyoriy o'zgarish %.",
        "maydonlar": {"sarlavha", "elementlar"},
    },
    # 3. Bitta obyektning tafsiloti: mijoz kartochkasi, buyurtma ichi,
    #    sozlamalar, xodim ma'lumoti
    "tafsilot": {
        "izoh": "Nom–qiymat juftliklari. Bitta narsaning to'liq ma'lumoti.",
        "maydonlar": {"sarlavha", "qatorlar", "izoh"},
    },
    # 4. Taqsimot: qarz yoshi (0-15/15-30/...), oylik sotuv, soha ulushi
    "taqsimot": {
        "izoh": "Ustunli diagramma. Nisbatni ko'rsatish uchun (qarz yoshi, oylik sotuv).",
        "maydonlar": {"sarlavha", "elementlar", "birlik"},
    },
    # 5. Soha profili — konstruktorning YURAGI. Oddiy odam AI bilan
    #    gaplashib tizim yasaganda, natijani AYNAN shu ko'rsatadi.
    "profil_oynasi": {
        "izoh": ("Taklif qilingan soha profili: maydonlar, retsept, bosqichlar. "
                 "Mijozga «tizimingiz shunday bo'ladi» deb ko'rsatish uchun."),
        "maydonlar": {"sarlavha", "nom", "maydonlar_royxati", "retsept",
                      "bosqichlar", "izoh"},
    },
    # 6. TASDIQ — Genkit tilida «interrupt». Agent harakatni TAKLIF
    #    qiladi, bajarmaydi. Tugmani odam bosadi.
    "tasdiq": {
        "izoh": ("Harakat taklifi va tasdiq tugmasi. Agent O'ZI bajarmaydi — "
                 "foydalanuvchi bosgandagina bajariladi."),
        "maydonlar": {"sarlavha", "matn", "amal", "kirish", "tugma", "xavfli"},
    },
    # 7. Hujjatlar — akt, nakladnoy, hisobot
    "hujjat": {
        "izoh": "Yuklab olinadigan hujjatlar ro'yxati (PDF/Excel/Word).",
        "maydonlar": {"sarlavha", "havolalar"},
    },
    # 8. Ogohlantirish / xulosa
    "ogoh": {
        "izoh": "Diqqat qaratadigan qisqa xabar: xavf, xato yoki muhim xulosa.",
        "maydonlar": {"daraja", "sarlavha", "matn"},
    },
}


def _matn(qiymat, uzunlik: int = MAX_MATN) -> str:
    """Har qanday qiymatni xavfsiz qisqa matnga aylantiradi."""
    if qiymat is None:
        return ""
    if isinstance(qiymat, bool):
        return "Ha" if qiymat else "Yo'q"
    if isinstance(qiymat, (int, float, Decimal)):
        return str(qiymat)
    return str(qiymat)[:uzunlik]


def _royxat(qiymat, nechta: int) -> list:
    if not isinstance(qiymat, list):
        raise KomponentXato("ro'yxat kutilgan edi")
    return qiymat[:nechta]


def tekshir(k: dict) -> dict:
    """Bitta komponentni tekshiradi va TOZALANGAN nusxasini qaytaradi.

    Modelning javobiga ishonmaymiz: noma'lum tur, ortiqcha maydon va
    haddan tashqari uzun ro'yxat shu yerda to'xtaydi.
    """
    if not isinstance(k, dict):
        raise KomponentXato("komponent lug'at bo'lishi kerak")
    tur = k.get("tur")
    if tur not in TURLAR:
        raise KomponentXato(f"noma'lum komponent turi: {tur}")

    toza = {"tur": tur, "sarlavha": _matn(k.get("sarlavha"), 120)}

    if tur == "jadval":
        ustunlar = [_matn(u, 40) for u in _royxat(k.get("ustunlar", []), MAX_USTUN)]
        qatorlar = []
        for q in _royxat(k.get("qatorlar", []), MAX_QATOR):
            if isinstance(q, dict):      # {"hujayralar": [...], "holat": "ok"}
                hujayralar = [_matn(x, 80) for x in
                              _royxat(q.get("hujayralar", []), MAX_USTUN)]
                qatorlar.append({"hujayralar": hujayralar,
                                 "holat": _matn(q.get("holat"), 20)})
            else:                        # oddiy ro'yxat
                qatorlar.append({"hujayralar": [_matn(x, 80) for x in
                                                _royxat(q, MAX_USTUN)],
                                 "holat": ""})
        toza.update({"ustunlar": ustunlar, "qatorlar": qatorlar,
                     "izoh": _matn(k.get("izoh"), 200)})

    elif tur == "korsatkichlar":
        toza["elementlar"] = [
            {"nom": _matn(e.get("nom"), 40), "qiymat": _matn(e.get("qiymat"), 40),
             "ozgarish": _matn(e.get("ozgarish"), 20),
             "holat": _matn(e.get("holat"), 20)}
            for e in _royxat(k.get("elementlar", []), 8) if isinstance(e, dict)]

    elif tur == "tafsilot":
        toza["qatorlar"] = [
            {"nom": _matn(q.get("nom"), 60), "qiymat": _matn(q.get("qiymat"), 120),
             "holat": _matn(q.get("holat"), 20)}
            for q in _royxat(k.get("qatorlar", []), 30) if isinstance(q, dict)]
        toza["izoh"] = _matn(k.get("izoh"), 200)

    elif tur == "taqsimot":
        elementlar = []
        for e in _royxat(k.get("elementlar", []), 12):
            if not isinstance(e, dict):
                continue
            try:
                qiymat = float(e.get("qiymat") or 0)
            except (TypeError, ValueError):
                qiymat = 0.0
            elementlar.append({"nom": _matn(e.get("nom"), 40), "qiymat": qiymat,
                               "holat": _matn(e.get("holat"), 20)})
        toza.update({"elementlar": elementlar, "birlik": _matn(k.get("birlik"), 20)})

    elif tur == "profil_oynasi":
        toza.update({
            "nom": _matn(k.get("nom"), 80),
            "maydonlar_royxati": [
                {"nom": _matn(md.get("nom"), 60), "tur": _matn(md.get("tur"), 20),
                 "birlik": _matn(md.get("birlik"), 20),
                 "majburiy": bool(md.get("majburiy"))}
                for md in _royxat(k.get("maydonlar_royxati", []), 25)
                if isinstance(md, dict)],
            "retsept": [
                {"material": _matn(r.get("material"), 60),
                 "birlik": _matn(r.get("birlik"), 20),
                 "miqdor": _matn(r.get("miqdor"), 80)}
                for r in _royxat(k.get("retsept", []), 20) if isinstance(r, dict)],
            "bosqichlar": [_matn(b, 40) for b in _royxat(k.get("bosqichlar", []), 12)],
            "izoh": _matn(k.get("izoh"), 300),
        })

    elif tur == "tasdiq":
        amal = _matn(k.get("amal"), 60)
        if amal not in AMALLAR:
            raise KomponentXato(f"noma'lum amal: {amal}")
        kirish = k.get("kirish") or {}
        if not isinstance(kirish, dict):
            raise KomponentXato("«kirish» lug'at bo'lishi kerak")
        toza.update({
            "matn": _matn(k.get("matn"), 400), "amal": amal,
            "kirish": {str(x)[:40]: kirish[x] for x in list(kirish)[:10]},
            "tugma": _matn(k.get("tugma"), 40) or AMALLAR[amal]["tugma"],
            "xavfli": bool(AMALLAR[amal].get("xavfli")),
        })

    elif tur == "hujjat":
        toza["havolalar"] = [
            {"nom": _matn(h.get("nom"), 40), "havola": _matn(h.get("havola"), 200)}
            for h in _royxat(k.get("havolalar", []), 8)
            # Faqat ichki manzil: model tashqi saytga havola berib
            # foydalanuvchini olib chiqib ketmasin.
            if isinstance(h, dict) and str(h.get("havola", "")).startswith("/api/")]

    elif tur == "ogoh":
        daraja = _matn(k.get("daraja"), 10)
        toza.update({"daraja": daraja if daraja in ("xavf", "ogoh", "ok") else "ogoh",
                     "matn": _matn(k.get("matn"), 400)})

    return toza


def tekshir_royxat(komponentlar) -> list[dict]:
    """Ro'yxatni tekshiradi. Buzuq komponent BUTUN javobni yiqitmaydi —
    u tashlab yuboriladi va qolganlari ko'rsatiladi."""
    if not isinstance(komponentlar, list):
        return []
    natija = []
    for k in komponentlar[:MAX_KOMPONENT]:
        try:
            natija.append(tekshir(k))
        except KomponentXato:
            continue
    return natija


# =====================================================================
#  TASDIQLANADIGAN AMALLAR (Genkit tilida — «interrupt»)
#
#  Agentlar ataylab FAQAT O'QIYDI. Yozish kerak bo'lganda agent amalni
#  TAKLIF qiladi, foydalanuvchi tugmani bosadi va amal SHU YERDAGI
#  ro'yxat bo'yicha bajariladi. Model amal nomini o'ylab topa olmaydi —
#  ro'yxatda yo'q nom `tekshir()` da rad etiladi.
#
#  Audit jurnaliga «AI agent» emas, TUGMANI BOSGAN ODAM yoziladi:
#  javobgarlik odamda qoladi.
# =====================================================================

def _profilni_faollashtir(db, user, kirish):
    from . import models as m, domain
    kalit = str(kirish.get("kalit", ""))
    yangi = db.query(m.SohaProfil).filter(m.SohaProfil.kalit == kalit).first()
    if not yangi:
        return {"xato": f"'{kalit}' profili topilmadi"}
    for p in db.query(m.SohaProfil).all():
        p.faol = (p.id == yangi.id)
    db.add(m.AuditLog(who=user.name, action="Soha profili faollashtirildi",
                      detail=f"{yangi.kalit} (AI taklifi, foydalanuvchi tasdiqladi)"))
    db.commit()
    domain.qayta_yukla(db)
    return {"ok": True, "xabar": f"«{yangi.nom}» faollashtirildi"}


def _buyurtma_maqomi(db, user, kirish):
    # MUHIM: maqomni shu yerda o'zgartirmaymiz, `set_status` ni
    # chaqiramiz. Maqom almashishida xomashyo yechish, bekor qilinganda
    # uni omborga qaytarish, topshirilgan sanani yozish kabi mantiq bor —
    # uni takrorlash ertami-kechmi ikkalasi bir-biridan farq qilishiga
    # olib keladi va ombor jimgina noto'g'ri bo'lib qoladi.
    from fastapi import HTTPException
    from .routers.orders import set_status
    try:
        set_status(int(kirish.get("buyurtma_id", 0)),
                   str(kirish.get("maqom", "")), db, user)
    except HTTPException as e:
        return {"xato": e.detail}
    return {"ok": True,
            "xabar": f"#{kirish.get('buyurtma_id')} → {kirish.get('maqom')}"}


def _mijozni_bloklash(db, user, kirish):
    from . import models as m
    c = db.get(m.Client, int(kirish.get("mijoz_id", 0)))
    if not c:
        return {"xato": "Mijoz topilmadi"}
    c.blacklisted = bool(kirish.get("bloklansin", True))
    db.add(m.AuditLog(who=user.name, action="Mijoz qora ro'yxati",
                      detail=f"{c.company}: {'bloklandi' if c.blacklisted else 'ochildi'}"
                             f" (AI taklifi, tasdiqlandi)"))
    db.commit()
    return {"ok": True, "xabar": f"{c.company} — "
                                 f"{'bloklandi' if c.blacklisted else 'blokdan chiqarildi'}"}


def _kredit_limiti(db, user, kirish):
    from . import models as m
    c = db.get(m.Client, int(kirish.get("mijoz_id", 0)))
    if not c:
        return {"xato": "Mijoz topilmadi"}
    eski = c.credit_limit
    c.credit_limit = Decimal(str(kirish.get("limit", 0)))
    db.add(m.AuditLog(who=user.name, action="Kredit limiti",
                      detail=f"{c.company}: {eski} → {c.credit_limit} "
                             f"(AI taklifi, tasdiqlandi)"))
    db.commit()
    return {"ok": True, "xabar": f"{c.company} limiti {c.credit_limit:,.0f} so'm"}


def _eng_past_qoldiq(db, user, kirish):
    from . import models as m
    mat = db.get(m.Material, int(kirish.get("material_id", 0)))
    if not mat:
        return {"xato": "Material topilmadi"}
    mat.min_stock = Decimal(str(kirish.get("miqdor", 0)))
    db.add(m.AuditLog(who=user.name, action="Eng past qoldiq",
                      detail=f"{mat.name}: {mat.min_stock} (AI taklifi, tasdiqlandi)"))
    db.commit()
    return {"ok": True, "xabar": f"{mat.name} — eng past qoldiq "
                                 f"{mat.min_stock} {mat.unit}"}


AMALLAR = {
    "profilni_faollashtir": {
        "izoh": ("Taklif qilingan soha profilini FAOL qiladi — butun tizim "
                 "shunga moslashadi. Profil saqlangandan keyin taklif qiling."),
        "tugma": "Faollashtirish", "xavfli": True,
        "rollar": ["Rahbar"], "bajar": _profilni_faollashtir,
    },
    "buyurtma_maqomi": {
        "izoh": "Buyurtmani keyingi bosqichga o'tkazishni taklif qiladi.",
        "tugma": "O'tkazish", "xavfli": False,
        "rollar": ["Rahbar", "Menejer", "Sex boshlig'i"], "bajar": _buyurtma_maqomi,
    },
    "mijozni_bloklash": {
        "izoh": "Mijozni qora ro'yxatga qo'shish/chiqarish taklifi.",
        "tugma": "Bloklash", "xavfli": True,
        "rollar": ["Rahbar"], "bajar": _mijozni_bloklash,
    },
    "kredit_limiti": {
        "izoh": "Mijozning kredit limitini o'zgartirish taklifi.",
        "tugma": "Limitni o'rnatish", "xavfli": True,
        "rollar": ["Rahbar", "Buxgalter"], "bajar": _kredit_limiti,
    },
    "eng_past_qoldiq": {
        "izoh": "Material uchun eng past qoldiq chegarasini o'rnatish taklifi.",
        "tugma": "O'rnatish", "xavfli": False,
        "rollar": ["Rahbar", "Sklad mudiri"], "bajar": _eng_past_qoldiq,
    },
}


def amalni_bajar(db, user, amal: str, kirish: dict) -> dict:
    """Foydalanuvchi tasdiqlagan amalni bajaradi.

    Rol shu yerda ham tekshiriladi: taklif ko'rsatilgan bo'lsa ham,
    huquqi yo'q odam uni bajara olmaydi.
    """
    tarif = AMALLAR.get(amal)
    if not tarif:
        return {"xato": f"'{amal}' — noma'lum amal"}
    if user.role not in tarif["rollar"] and user.role != "Rahbar":
        return {"xato": f"Bu amal faqat: {', '.join(tarif['rollar'])}"}
    return tarif["bajar"](db, user, kirish or {})


def korsatma_matni() -> str:
    """Modelga beriladigan ko'rsatma — komponentlar va amallar ro'yxati."""
    turlar = "\n".join(f"- `{nom}` — {t['izoh']}" for nom, t in TURLAR.items())
    amallar = "\n".join(f"- `{nom}` — {t['izoh']}" for nom, t in AMALLAR.items())
    return f"""
## KO'RINISH (komponentlar)

Javobingda RAQAM yoki RO'YXAT bo'lsa — uni matn bilan sanab chiqma,
`korsat` asbobi bilan CHIZ. Matning qisqa xulosa bo'lsin, tafsilot
komponentda ko'rinadi.

`korsat` ga komponentlarni `komponentlar_json` MAYDONIDA, JSON MATN
ko'rinishida ber (massiv). Kod bloki (```) ishlatma, faqat toza JSON.

`korsat` ga `komponentlar_json` — JSON MASSIVINING MATNI beriladi
(kod bloki, izoh yoki qo'shimcha matnsiz, faqat JSON).

Komponent turlari:
{turlar}

Qoidalar:
- Bir javobda ko'pi bilan {MAX_KOMPONENT} komponent, jadvalda {MAX_QATOR} qator.
- Jadvalda `holat` maydoni rang beradi: `ok` (yashil), `ogoh` (sariq),
  `xavf` (qizil), bo'sh (oddiy).
- Pul summasini o'zing formatla: «12 500 000 so'm».
- Uzun ro'yxatni qisqartir va «yana N ta» deb izohda ayt.

## HARAKAT TAKLIFI

Sen bazaga O'ZING yozmaysan. Biror narsani o'zgartirish kerak bo'lsa
`tasdiq` komponentini ko'rsat — foydalanuvchi tugmani bosadi va shundan
keyin bajariladi. Mavjud amallar:
{amallar}
"""
