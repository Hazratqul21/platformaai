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


def _bolimlarni_sozla(db, user, kirish):
    """Yon menyuni MIJOZ xohlaganidek yig'adi (AI taklif qiladi, odam bosadi).

    Bu — konstruktorning eng ko'rinadigan qismi: odam chatda «menga
    ombor kerak emas, kassa va buxgalteriya yetadi» deydi, AI ro'yxatni
    taklif qiladi, tugma bosilgach menyu o'zgaradi. Kod yozilmaydi.

    `dash`, `ai`, `set`, `help` olib tashlanmaydi — ularsiz mijoz
    tizimga qaytib kira olmaydi (`bolimlar.MAJBURIY`).
    """
    from . import models as m, bolimlar as b
    xom = kirish.get("kalitlar") or []
    if isinstance(xom, str):                 # model satr yuborishi mumkin
        xom = [x.strip() for x in xom.replace(",", " ").split() if x.strip()]
    notanish = [k for k in xom if k not in b.KATALOG]
    if notanish:
        return {"xato": f"Noma'lum bo'lim: {', '.join(notanish)}. "
                        f"Mavjudlari: {', '.join(b.KATALOG)}"}
    if not xom:
        return {"xato": "Bo'limlar ro'yxati bo'sh"}

    tanlov = b.saqla(db, xom)
    db.add(m.AuditLog(who=user.name, action="Bo'limlar o'zgartirildi",
                      detail=f"{', '.join(tanlov)} (AI taklifi, tasdiqlandi)"))
    db.commit()
    nomlar = [b.KATALOG[k]["nom"] for k in tanlov]
    return {"ok": True, "bolimlar": tanlov,
            "xabar": "Menyu yangilandi: " + ", ".join(nomlar) +
                     ". Sahifani yangilang."}


RUXSAT_MAYDON_TUR = {"matn", "raqam", "pul", "sana", "tanlov", "belgi"}


def _maydon_tuz(fld, indeks):
    """Bitta maydon (ustun) ta'rifini normallashtiradi. Xato bo'lsa
    {"xato": ...} qaytaradi, bo'lmasa maydon dict.

    `tanlov` — ro'yxatdan bittasi: `variantlar` (yoki `options`) kerak.
    `belgi` — Ha/Yo'q. Boshqalar: matn/raqam/pul/sana."""
    if isinstance(fld, str):
        fld = {"label": fld, "type": "matn"}
    label = str(fld.get("label") or "").strip()
    tur = str(fld.get("type") or "matn").strip()
    if not label:
        return {"xato": "Maydon nomi bo'sh bo'lmasin"}
    if tur not in RUXSAT_MAYDON_TUR:
        return {"xato": f"Maydon turi noto'g'ri: {tur}. Ruxsat: "
                        "matn, raqam, pul, sana, tanlov, belgi"}
    m = {"key": f"f{indeks}", "label": label, "type": tur}
    if tur == "tanlov":
        xom = fld.get("variantlar") or fld.get("options") or []
        variant = [str(o).strip() for o in xom if str(o).strip()]
        if not variant:
            return {"xato": f"«{label}» (tanlov) uchun kamida 1 ta variant kerak"}
        m["options"] = variant
    return m


def _bolim_yarat(db, user, kirish):
    """MIJOZ chatda tasvirlagan YANGI bo'limni yaratadi (AI IDE yadrosi).

    Bu — ORDO ni «biznes uchun AI IDE» qiladigan qism: odam «menga
    bilyard stollari holatini kuzatadigan joy kerak: stol raqami,
    holat, joriy tarif» deydi, AI shu bo'limni maydonlari bilan
    taklif qiladi, tugma bosilgach HAQIQIY bo'lim yaratiladi va yon
    menyuda paydo bo'ladi. Kod yozilmaydi — konfiguratsiya.

    `constructor.py` dagi yaratish mantig'i bilan bir xil (bitta
    haqiqat manbai): maydon turlari matn/raqam/pul/sana bo'lishi shart.
    """
    import json as _json
    from . import models as m
    nom = (kirish.get("nom") or "").strip()
    ikonka = (kirish.get("ikonka") or "clipboard").strip()[:10]
    xom = kirish.get("maydonlar") or []
    if not nom:
        return {"xato": "Bo'lim nomi bo'sh bo'lmasin"}
    if not xom:
        return {"xato": "Kamida 1 ta maydon (ustun) kerak"}
    maydonlar = []
    for i, fld in enumerate(xom):
        m2 = _maydon_tuz(fld, i + 1)
        if "xato" in m2:
            return m2
        maydonlar.append(m2)
    mavjud = db.query(m.CustomSection).filter(m.CustomSection.name == nom).first()
    if mavjud:
        return {"xato": f"«{nom}» nomli bo'lim allaqachon bor"}
    # Kim ko'radi: rol nomlari ro'yxati. Bo'sh/berilmagan = hammaga ochiq.
    rollar = [str(x).strip() for x in (kirish.get("rollar") or []) if str(x).strip()]
    b = m.CustomSection(name=nom[:80], icon=ikonka,
                        fields_json=_json.dumps(maydonlar, ensure_ascii=False),
                        roles_json=_json.dumps(rollar, ensure_ascii=False) if rollar else None)
    db.add(b)
    db.add(m.AuditLog(who=user.name, action="Yangi bo'lim yaratildi (AI konstruktor)",
                      detail=f"{nom}: {', '.join(x['label'] for x in maydonlar)}"))
    db.commit()
    return {"ok": True, "section_id": b.id, "nom": nom,
            "xabar": f"«{nom}» bo'limi yaratildi ({len(maydonlar)} ustun). "
                     "Sahifani yangilang — u yon menyuda ko'rinadi."}


def _yozuv_qosh(db, user, kirish):
    """Custom bo'limga bitta YOZUV qo'shadi (AI IDE — kundalik ma'lumot).

    Mijoz «stol 5 band bo'ldi, tarif 45000» deydi, AI shu bo'limga
    yozuvni qo'shishni taklif qiladi. `section_id` — qaysi bo'lim,
    `data` — {ustun_kaliti: qiymat}. AI ustun kalitini `konstruktor_royxat`
    dan biladi; label yuborsa ham moslaymiz.
    """
    import json as _json
    from . import models as m
    sid = kirish.get("section_id")
    data = kirish.get("data") or {}
    b = db.get(m.CustomSection, sid) if sid else None
    if not b:
        return {"xato": "Bo'lim topilmadi. Avval `konstruktor_royxat` bilan id ni oling."}
    maydonlar = _json.loads(b.fields_json)
    kalitlar = {f["key"] for f in maydonlar}
    # label -> key moslash (AI kalit o'rniga nom yuborsa)
    label2key = {f["label"].lower(): f["key"] for f in maydonlar}
    tur_bo = {f["key"]: f for f in maydonlar}
    toza = {}
    for k, v in data.items():
        key = k if k in kalitlar else label2key.get(str(k).lower())
        if not key:
            continue  # notanish kalit — jimgina tashlanadi (bo'limda yo'q ustun)
        f = tur_bo[key]
        tur = f["type"]
        if tur == "belgi":
            v = v in (True, "true", "1", "ha", "Ha", "on", "bor", "band")
        elif tur in ("raqam", "pul") and v not in ("", None):
            try:
                v = float(v)
            except (TypeError, ValueError):
                return {"xato": f"«{f['label']}» raqam bo'lishi kerak"}
        elif tur == "tanlov" and v not in ("", None):
            variant = f.get("options") or []
            if variant and str(v) not in variant:
                return {"xato": f"«{f['label']}» uchun variant noto'g'ri: {v}. "
                                f"Ruxsat: {', '.join(variant)}"}
        toza[key] = v
    if not toza:
        return {"xato": "Yozuvda birorta ustun qiymati yo'q"}
    r = m.CustomRecord(section_id=b.id,
                       data_json=_json.dumps(toza, ensure_ascii=False))
    db.add(r)
    db.add(m.AuditLog(who=user.name, action="Bo'limga yozuv qo'shildi (AI)",
                      detail=f"{b.name}: {toza}"))
    db.commit()
    return {"ok": True, "xabar": f"«{b.name}» bo'limiga yozuv qo'shildi. "
                                 "Bo'limni ochib ko'ring."}


def _bolim_tahrir(db, user, kirish):
    """Mavjud custom bo'limga USTUN qo'shadi yoki olib tashlaydi (AI IDE).

    Mijoz «Stollar bo'limiga «Mijoz» ustunini qo'sh» yoki «Tarif
    ustunini olib tashla» deydi. AI avval `konstruktor_royxat` bilan
    `section_id` va mavjud ustun kalitlarini biladi.

    `qoshiladigan` — yangi ustunlar [{label, type}]; yangi kalit eng
    katta mavjud f-raqamdan KEYIN beriladi, shu bois eski yozuvlar
    buzilmaydi. `oladigan` — olib tashlanadigan ustun kalitlari yoki
    nomlari. Ustun olib tashlansa, eski yozuvdagi qiymat `data_json`
     da SAQLANIB qoladi (yo'qolmaydi, faqat jadvalda ko'rinmaydi) —
    fikr o'zgarsa ustunni qayta qo'shish mumkin.
    """
    import json as _json
    import re as _re
    from . import models as m
    sid = kirish.get("section_id")
    b = db.get(m.CustomSection, sid) if sid else None
    if not b:
        return {"xato": "Bo'lim topilmadi. Avval `konstruktor_royxat` bilan id ni oling."}
    maydonlar = _json.loads(b.fields_json)
    qoshiladigan = kirish.get("qoshiladigan") or []
    oladigan = kirish.get("oladigan") or []
    # rollar berilsa — kim ko'rishini o'zgartiramiz. `["hamma"]` yoki bo'sh
    # ro'yxat = hammaga ochiq. Berilmasa (kalit yo'q) — tegilmaydi.
    rol_ozgardi = False
    if "rollar" in kirish:
        xrol = [str(x).strip() for x in (kirish.get("rollar") or []) if str(x).strip()]
        xrol = [r for r in xrol if r.lower() != "hamma"]
        b.roles_json = _json.dumps(xrol, ensure_ascii=False) if xrol else None
        rol_ozgardi = True

    # --- olib tashlash (kalit yoki nom bo'yicha) ---
    olindi = []
    if oladigan:
        oxbor = {str(x).lower() for x in oladigan}
        qoldi = []
        for f in maydonlar:
            if f["key"].lower() in oxbor or f["label"].lower() in oxbor:
                olindi.append(f["label"])
            else:
                qoldi.append(f)
        maydonlar = qoldi

    # --- qo'shish (kalit eng katta f-raqamdan keyin) ---
    qoshildi = []
    if qoshiladigan:
        raqamlar = [int(mn.group(1)) for f in maydonlar
                    for mn in [_re.fullmatch(r"f(\d+)", f["key"])] if mn]
        keyingi = (max(raqamlar) if raqamlar else 0) + 1
        for fld in qoshiladigan:
            m2 = _maydon_tuz(fld, keyingi)
            if "xato" in m2:
                return m2
            maydonlar.append(m2)
            qoshildi.append(m2["label"])
            keyingi += 1

    if not qoshildi and not olindi and not rol_ozgardi:
        return {"xato": "Hech qanday o'zgarish yo'q — ustun qo'shish/olib "
                        "tashlash yoki rollarni ko'rsating"}
    if not maydonlar:
        return {"xato": "Bo'limda kamida 1 ta ustun qolishi kerak"}

    b.fields_json = _json.dumps(maydonlar, ensure_ascii=False)
    tafsil = []
    if qoshildi:
        tafsil.append("qo'shildi: " + ", ".join(qoshildi))
    if olindi:
        tafsil.append("olindi: " + ", ".join(olindi))
    if rol_ozgardi:
        rlar = _json.loads(b.roles_json) if b.roles_json else None
        tafsil.append("ko'rish: " + (", ".join(rlar) if rlar else "hammaga"))
    db.add(m.AuditLog(who=user.name, action="Bo'lim ustunlari tahrirlandi (AI)",
                      detail=f"{b.name}: {'; '.join(tafsil)}"))
    db.commit()
    return {"ok": True, "xabar": f"«{b.name}» bo'limi yangilandi ({'; '.join(tafsil)}). "
                                 "Bo'limni ochib ko'ring."}


AMALLAR = {
    "bolim_yarat": {
        "izoh": ("YANGI bo'lim/ro'yxat YARATISH taklifi — mijoz chatda "
                 "«menga ... kuzatadigan joy/ro'yxat kerak» yoki «... "
                 "bo'lim ochib ber» desa. `nom` — bo'lim nomi, `maydonlar` "
                 "— ustunlar ro'yxati [{label, type}], type FAQAT: matn, "
                 "raqam, pul, sana, tanlov, belgi. `tanlov` (ro'yxatdan "
                 "bittasi) uchun `variantlar` ham bering (masalan {label:"
                 "'Holat',type:'tanlov',variantlar:['band','bo\\'sh']}); "
                 "`belgi` = Ha/Yo'q. `ikonka` — ixtiyoriy (clipboard, box, "
                 "truck, cash, users, calendar...). `rollar` — ixtiyoriy: "
                 "kim ko'radi (masalan ['Menejer','Buxgalter']); berilmasa "
                 "HAMMAGA ochiq (Rahbar doimo ko'radi). Masalan «bilyard "
                 "stollari»: nom=Stollar, maydonlar=[{label:'Stol raqami',"
                 "type:'raqam'},{label:'Holat',type:'matn'},{label:'Tarif',"
                 "type:'pul'}]."),
        "tugma": "Bo'limni yaratish", "xavfli": False,
        "kirish_namuna": {"nom": "Stollar", "ikonka": "clipboard",
                          "maydonlar": [{"label": "Stol raqami", "type": "raqam"},
                                        {"label": "Holat", "type": "matn"}]},
        "rollar": ["Rahbar"], "bajar": _bolim_yarat,
    },
    "yozuv_qosh": {
        "izoh": ("Qo'shimcha (konstruktor) bo'limga bitta YOZUV qo'shish "
                 "taklifi — mijoz «... band bo'ldi», «... qo'shildi» kabi "
                 "kundalik ma'lumot aytsa. Avval `konstruktor_royxat` bilan "
                 "`section_id` va ustun kalitlarini oling. `data` — "
                 "{ustun_kaliti: qiymat}."),
        "tugma": "Yozuvni qo'shish", "xavfli": False,
        "kirish_namuna": {"section_id": 1,
                          "data": {"f1": "5", "f2": "band", "f3": "45000"}},
        "rollar": ["Rahbar", "Menejer", "Buxgalter", "Sklad mudiri",
                   "Sex boshlig'i"], "bajar": _yozuv_qosh,
    },
    "bolim_tahrir": {
        "izoh": ("Mavjud QO'SHIMCHA bo'limga USTUN qo'shish yoki olib "
                 "tashlash taklifi — mijoz «... bo'limiga «X» ustunini "
                 "qo'sh» yoki «X ustunini olib tashla» desa. Avval "
                 "`konstruktor_royxat` bilan `section_id` va mavjud "
                 "ustunlarni oling. `qoshiladigan` — [{label, type}] "
                 "(type: matn/raqam/pul/sana), `oladigan` — ustun "
                 "kalitlari yoki nomlari. `rollar` — kim ko'rishini "
                 "o'zgartirish (masalan ['Menejer']); bo'sh ['] yoki "
                 "['hamma'] = hammaga ochadi. Eski yozuvlar buzilmaydi."),
        "tugma": "Bo'limni yangilash", "xavfli": False,
        "kirish_namuna": {"section_id": 1,
                          "qoshiladigan": [{"label": "Mijoz", "type": "matn"}],
                          "oladigan": []},
        "rollar": ["Rahbar"], "bajar": _bolim_tahrir,
    },
    "bolimlarni_sozla": {
        "izoh": ("Yon menyudagi BO'LIMLARNI mijoz xohlaganidek yig'ish "
                 "taklifi. `kalitlar` — bo'lim kalitlari ro'yxati "
                 "(`bolimlarni_kor` asbobidan olinadi). Mijoz «bu bo'lim "
                 "kerak emas» yoki «menga faqat kassa kerak» desa shuni "
                 "taklif qiling."),
        "tugma": "Menyuni yangilash", "xavfli": True,
        "kirish_namuna": {"kalitlar": ["kassa", "fin", "hisob", "crm"]},
        "rollar": ["Rahbar"], "bajar": _bolimlarni_sozla,
    },
    "profilni_faollashtir": {
        "izoh": ("Taklif qilingan soha profilini FAOL qiladi — butun tizim "
                 "shunga moslashadi. Profil saqlangandan keyin taklif qiling."),
        "tugma": "Faollashtirish", "xavfli": True,
        "kirish_namuna": {"kalit": "bilyard"},
        "rollar": ["Rahbar"], "bajar": _profilni_faollashtir,
    },
    "buyurtma_maqomi": {
        "izoh": "Buyurtmani keyingi bosqichga o'tkazishni taklif qiladi.",
        "tugma": "O'tkazish", "xavfli": False,
        "kirish_namuna": {"buyurtma_id": 42, "maqom": "Topshirildi"},
        "rollar": ["Rahbar", "Menejer", "Sex boshlig'i"], "bajar": _buyurtma_maqomi,
    },
    "mijozni_bloklash": {
        "izoh": "Mijozni qora ro'yxatga qo'shish/chiqarish taklifi.",
        "tugma": "Bloklash", "xavfli": True,
        "kirish_namuna": {"mijoz_id": 7, "bloklansin": True},
        "rollar": ["Rahbar"], "bajar": _mijozni_bloklash,
    },
    "kredit_limiti": {
        "izoh": "Mijozning kredit limitini o'zgartirish taklifi.",
        "tugma": "Limitni o'rnatish", "xavfli": True,
        "kirish_namuna": {"mijoz_id": 7, "limit": 5000000},
        "rollar": ["Rahbar", "Buxgalter"], "bajar": _kredit_limiti,
    },
    "eng_past_qoldiq": {
        "izoh": "Material uchun eng past qoldiq chegarasini o'rnatish taklifi.",
        "tugma": "O'rnatish", "xavfli": False,
        "kirish_namuna": {"material_id": 3, "miqdor": 500},
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
    from . import rollar as _r
    _asos = _r.asos(db, user.role)
    if _asos not in tarif["rollar"] and _asos != _r.ENG_YUQORI:
        return {"xato": f"Bu amal faqat: {', '.join(tarif['rollar'])}"}
    return tarif["bajar"](db, user, kirish or {})


def korsatma_matni() -> str:
    """Modelga beriladigan ko'rsatma — komponentlar va amallar ro'yxati."""
    turlar = "\n".join(f"- `{nom}` — {t['izoh']}" for nom, t in TURLAR.items())
    import json as _json
    amallar = "\n".join(
        f"- `{nom}` — {t['izoh']}\n  kirish: "
        f"{_json.dumps(t.get('kirish_namuna', {}), ensure_ascii=False)}"
        for nom, t in AMALLAR.items())
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
keyin bajariladi.

MUHIM: `tasdiq` komponentidagi `kirish` maydonini TO'LDIR. Bo'sh
qoldirsang tugma bosilganda amal bajarilmaydi va foydalanuvchi
«ishlamadi» deb qoladi. Har amalning kirish namunasi pastda berilgan —
qiymatlarni ASBOB javobidan ol, o'ylab topma.

Mavjud amallar:
{amallar}
"""
