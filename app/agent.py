"""AI AGENT — mijoz bilan gaplashib, ERP ni yig'ib beradi.

MUHIM QOIDA (arxitektura qarori, o'zgartirilmaydi):
    AI KOD YOZMAYDI — KONFIGURATSIYA TO'LDIRADI.

Agent mijozdan biznesini so'raydi va javoblardan `SohaProfil` ta'rifini
yasaydi: maydonlar, retsept, narx usuli, matn shablonlari. Bu ta'rif
allaqachon mavjud `POST /api/soha/profillar` yo'li bilan tekshiriladi va
saqlanadi — ya'ni agent yangi imkoniyat ochmaydi, faqat mavjudini
to'ldiradi. Agar AI har mijozga kod yozsa, 10 mijozdan keyin boshqarib
bo'lmaydi.

NEGA QO'LDA HALQA (tool runner emas):
SDK ning `tool_runner` yordamchisi asboblarni O'ZI chaqiradi va halqani
yopadi. Bizga esa har qadamda: (1) `db` seansini asbobga uzatish,
(2) suhbatni bazaga yozish, (3) frontendga asbob chaqiruvlari izini
qaytarish kerak. Shuning uchun halqa qo'lda yozilgan — bu SDK
hujjatidagi «manual agentic loop» naqshi.
"""
import json
import logging

from . import genui, llm

log = logging.getLogger("gofra.agent")

# Suhbat qancha marta asbob chaqira olishi. Cheksiz halqadan himoya —
# model qandaydir sababga ko'ra to'xtamasa, so'rov abadiy osilib qolmasin.
MAX_QADAM = 12


def kalit_bormi() -> bool:
    return llm.tayyormi()[0]


# =====================================================================
#  ASBOBLAR — agent shular orqali tizimga ta'sir qiladi
#
#  Ataylab TOR: profil o'qish/yozish/faollashtirish va sinov. Agentga
#  bazaga to'g'ridan-to'g'ri yozish yoki kod ishga tushirish berilmagan.
# =====================================================================

HAMMA_ASBOBLAR = [
    {
        "nom": "modullarni_kor",
        "izoh": (
            "Mavjud ish tartiblari (modullar) ro'yxatini qaytaradi. "
            "Har modul — buyurtmaning hayot sikli (statuslar). Yangi profil "
            "yasashdan OLDIN chaqiring: mijoz biznesiga qaysi ish tartibi "
            "mos kelishini shundan tanlaysiz."
        ),
        "sxema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "nom": "profillarni_kor",
        "izoh": (
            "Bazadagi mavjud soha profillari ro'yxati. Mijoz biznesiga "
            "yaqin profil bormi — shuni tekshiring. Bor bo'lsa uni asos "
            "qilib oling, noldan yasamang."
        ),
        "sxema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "nom": "profilni_oqi",
        "izoh": (
            "Bitta profilning TO'LIQ ta'rifini (JSON) qaytaradi. Mavjud "
            "profilni namuna qilib olish yoki tahrirlash uchun."
        ),
        "sxema": {
            "type": "object",
            "properties": {"kalit": {"type": "string", "description": "Profil kaliti, masalan 'karton'"}},
            "required": ["kalit"],
            "additionalProperties": False,
        },
    },
    {
        "nom": "profil_saqla",
        "izoh": (
            "Soha profilini yaratadi yoki yangilaydi. Ta'rif tuzilishi "
            "tizim ko'rsatmasida berilgan. Ta'rif TEKSHIRILADI — buzuq "
            "bo'lsa xato qaytadi va bazaga tushmaydi. Saqlash faollashtirmaydi."
        ),
        "sxema": {
            "type": "object",
            "properties": {
                "tarif": {
                    "type": "object",
                    "description": "Profilning to'liq JSON ta'rifi (kalit, nom, maydonlar, ...)",
                }
            },
            "required": ["tarif"],
            "additionalProperties": False,
        },
    },
    {
        "nom": "profilni_faollashtir",
        "izoh": (
            "Profilni FAOL qiladi — shundan keyin butun tizim (buyurtma "
            "formasi, hujjatlar, ombor) shu sohaga moslashadi. Mijoz "
            "tasdiqlagandan keyin chaqiring."
        ),
        "sxema": {
            "type": "object",
            "properties": {"kalit": {"type": "string"}},
            "required": ["kalit"],
            "additionalProperties": False,
        },
    },
    {
        "nom": "sinov_buyurtma",
        "izoh": (
            "Faol profil bilan SINOV buyurtmasi yasab ko'radi va natijani "
            "qaytaradi (o'lcham matni, tarkib, retsept, narx). Bazaga hech "
            "narsa yozilmaydi. Profilni mijozga ko'rsatishdan oldin shu "
            "bilan o'zingiz tekshiring — maydonlar to'g'ri hisoblanyaptimi."
        ),
        "sxema": {
            "type": "object",
            "properties": {
                "qiymatlar": {
                    "type": "object",
                    "description": "Soha maydonlari, masalan {\"ogirlik_g\": 600}",
                },
                "miqdor": {"type": "number", "description": "Buyurtma miqdori"},
            },
            "required": ["qiymatlar"],
            "additionalProperties": False,
        },
    },
]


# `korsat` — GenUI ning kirish nuqtasi. Model komponentlarni SHU ASBOB
# orqali yuboradi. Nega asbob: javob matnining ichiga JSON yozdirish
# ishonchsiz (model kod bloki, izoh yoki noto'g'ri qavs qo'shib yuboradi),
# asbob chaqiruvi esa provayder darajasida tuzilgan JSON kafolatlaydi.
KORSAT_ASBOBI = {
    "nom": "korsat",
    "izoh": (
        "Foydalanuvchiga KO'RINISH chizadi: jadval, ko'rsatkichlar, tafsilot, "
        "taqsimot, profil oynasi, tasdiq tugmasi, hujjat yoki ogohlantirish. "
        "Raqam va ro'yxatni matnda sanab chiqma — shu asbob bilan chiz."
    ),
    # NEGA OBYEKT MASSIVI EMAS, SATR:
    # Komponentlar har xil shaklda (jadvalda `ustunlar`, taqsimotda
    # `elementlar`...) — bu JSON Schema'da birlashma (union) bo'ladi.
    # Gemini'ning funksiya e'lonlari birlashmani va «turi ko'rsatilmagan
    # obyekt»ni ifodalay olmaydi: jonli sinovda u har safar
    # `MALFORMED_FUNCTION_CALL` bilan qaytardi va agent umuman javob
    # bermay qoldi.
    #
    # SATR esa uchala provayderda ham bir xil ishonchli o'tadi. Buzuq
    # JSON kelsa — xato MODELGA qaytariladi va u o'zi tuzatadi (halqa
    # shuning uchun bor).
    "sxema": {
        "type": "object",
        "properties": {
            "komponentlar_json": {
                "type": "string",
                "description": (
                    "Komponentlar ro'yxatining JSON matni. Masalan: "
                    '[{"tur":"jadval","sarlavha":"Qarzdorlar",'
                    '"ustunlar":["Mijoz","Qarz"],'
                    '"qatorlar":[{"hujayralar":["A MChJ","12 000 000 so\'m"],'
                    '"holat":"xavf"}]}]'
                ),
            }
        },
        "required": ["komponentlar_json"],
        "additionalProperties": False,
    },
}


TIZIM_KORSATMASI = """Sen — INNASOFT PLATFORMA ning sozlash yordamchisisan.

Vazifang: mijoz bilan gaplashib uning biznesini tushunish va o'sha
biznesga mos ERP konfiguratsiyasini yig'ish. Mijoz texnik odam EMAS —
sodda, kundalik til bilan gapir. «JSON», «maydon turi», «profil kaliti»
kabi so'zlarni ishlatma.

## Qanday ishlaysan

1. Avval `modullarni_kor` va `profillarni_kor` ni chaqir — nima borligini bil.
2. Mijozdan so'ra: nima ishlab chiqaradi/sotadi, mahsuloti nima bilan
   o'lchanadi, qaysi xususiyatlari muhim, nimalardan tayyorlanadi,
   narxni qanday hisoblaydi, qanday bosqichlardan o'tadi.
   BIR VAQTDA 1-2 SAVOL. Anketa qilma, suhbat qil.
3. Mijoz biznesiga yaqin profil bo'lsa — `profilni_oqi` bilan o'qib,
   uni asos qil. Noldan yasashdan ko'ra o'zgartirish oson va xavfsiz.
4. Ta'rifni yig'ib `profil_saqla` bilan saqla.
5. `profilni_faollashtir`, keyin `sinov_buyurtma` bilan O'ZING tekshir.
6. Natijani mijozga oddiy til bilan ko'rsat: «600 g patir, 1000 dona —
   un 397.8 kg ketadi, tannarx 3 566 so'm, taklif narxi 4 458 so'm».
7. Mijoz tuzatish aytsa — ta'rifni yangilab, qaytadan sinab ko'rsat.

## Profil ta'rifi tuzilishi

```json
{
  "kalit": "non",                      // lotin harflar, _ bilan
  "nom": "Non zavodi",
  "modul": "ishlab_chiqarish",         // modullarni_kor dan tanlanadi
  "maydonlar": [
    {"kalit": "ogirlik_g", "nom": "Og'irlik", "tur": "butun",
     "birlik": "g", "min": 50, "max": 5000, "majburiy": true},
    {"kalit": "un_navi", "nom": "Un navi", "tur": "matn",
     "standart": "oliy", "variantlar": ["oliy", "1-nav"]}
  ],
  "hosila": {                          // ixtiyoriy: bir maydondan boshqasi
    "kepakli": {"manba": "un_navi", "teng": "to'liq don"}
  },
  "olchov": {"birlik": "dona", "kasrli": false, "min": "1", "max": "1000000"},
  "narx": {"usul": "retsept", "ish_haqi": "ogirlik_g * 0.5",
           "qoshimcha_xarajat_foiz": 12},
  "retsept": [
    {"material": "Un", "birlik": "kg",
     "miqdor": "ogirlik_g * qty / 1000 * 0.65", "brak_foiz": 2}
  ],
  "matnlar": {
    "olcham": "{ogirlik_g} g",
    "tarkib": "{non_turi}, {un_navi} un",
    "tur": "{non_turi}",
    "tur_zaxira": "non",
    "hujjat_mahsulot": "Нон: {tarkib}, {olcham}",
    "nakladnoy_mahsulot": "Нон: {tarkib}, {olcham}"
  }
}
```

Maydon turlari: `butun`, `kasr`, `matn`, `mantiq`.
Maydon qo'shimchalari: `birlik`, `standart`, `min`, `max`, `variantlar`,
`majburiy`, `hisoblanadi` (tizim o'zi hisoblaydi, mijoz kiritmaydi).

`narx.usul`:
- `retsept` — tannarx retseptdan hisoblanadi, ustiga ish haqi va foiz.
  Ish haqi son yoki maydonlar ustidan formula bo'lishi mumkin.
- `qolda` — menejer narxni o'zi kiritadi (formulasi noma'lum soha).

`retsept` — 1 buyurtmaga qancha material. `miqdor` formulasida faqat
RAQAMLI maydonlar va `qty` (buyurtma miqdori) ishlatiladi. `material`
nomida `{maydon}` yozsang, qiymat o'sha maydondan olinadi.

`matnlar` shablonlarida vergul bilan ajratilgan bo'lak ichidagi maydon
bo'sh bo'lsa — o'sha bo'lak tushib qoladi. Shuning uchun
«{colors} рангли босма» ranglar 0 bo'lganda umuman chiqmaydi.

## Muhim cheklovlar

- Bir xil material turli profillarda BIR XIL birlikda bo'lishi shart.
  Ombor bitta: «Qum» bir joyda m³, boshqasida kg bo'lsa tizim yiqiladi.
- Formulalarda faqat + - * / ( ) va raqamli maydon nomlari. Funksiya
  chaqirish yo'q. Kasr son NUQTA bilan (0.65), vergul bilan emas.
- Miqdor kasrli bo'lishi kerakmi — o'ylab ko'r. Beton m³ bilan
  o'lchanadi va 2.5 m³ bo'ladi; non dona bilan va 2.5 dona bo'lmaydi.

## Uslub

O'zbek tilida yoz. Qisqa gaplar. Bir javobda bitta fikr. Mijoz
aytmagan narsani o'ylab qo'shma — bilmasang so'ra. Tayyor bo'lgach
nima qilganingni bir-ikki gapda ayt, uzun hisobot yozma."""


# =====================================================================
#  Asboblarni bajarish
# =====================================================================

def _asbobni_bajar(db, nom: str, kirish: dict) -> dict:
    """Asbobni bajaradi va natijani (JSON ga aylanadigan) dict qaytaradi."""
    from decimal import Decimal

    from . import domain, models as m, services as s

    if nom == "modullarni_kor":
        return {"modullar": [
            {"kalit": k, "nom": t.get("nom"), "izoh": t.get("izoh"),
             "statuslar": [s["nom"] for s in t.get("statuslar", [])]}
            for k, t in domain.modullar().items()]}

    if nom == "profillarni_kor":
        return {"profillar": [
            {"kalit": p.kalit, "nom": p.nom, "faol": p.faol}
            for p in db.query(m.SohaProfil).order_by(m.SohaProfil.id).all()]}

    if nom == "profilni_oqi":
        p = db.query(m.SohaProfil).filter(
            m.SohaProfil.kalit == kirish["kalit"]).first()
        if not p:
            return {"xato": f"'{kirish['kalit']}' profili topilmadi"}
        return {"tarif": json.loads(p.tarif_json)}

    if nom == "profil_saqla":
        tarif = kirish["tarif"]
        try:
            tekshirilgan = domain.Profil(tarif)
        except (KeyError, ValueError, TypeError) as e:
            # Xatoni AGENTGA qaytaramiz — u o'zi tuzatib qayta yuboradi.
            # Foydalanuvchiga texnik xato ko'rsatilmaydi.
            return {"xato": f"Ta'rif noto'g'ri: {e}"}

        ziddiyat = domain.retsept_ziddiyatlari(
            {**domain.shablonlar(), tekshirilgan.kalit: tarif})
        mavjud = db.query(m.SohaProfil).filter(
            m.SohaProfil.kalit == tekshirilgan.kalit).first()
        tarif_json = json.dumps(tarif, ensure_ascii=False)
        if mavjud:
            mavjud.nom, mavjud.tarif_json = tekshirilgan.nom, tarif_json
            mavjud.ozgartirilgan = True
        else:
            db.add(m.SohaProfil(kalit=tekshirilgan.kalit, nom=tekshirilgan.nom,
                                tarif_json=tarif_json, faol=False,
                                ozgartirilgan=True))
        db.add(m.AuditLog(who="AI agent", action="Soha profili yozildi",
                          detail=tekshirilgan.kalit))
        db.commit()
        if mavjud and mavjud.faol:
            domain.qayta_yukla(db)
        return {"ok": True, "kalit": tekshirilgan.kalit,
                "maydonlar": len(tekshirilgan.maydonlar),
                "ogohlantirish": ziddiyat}

    if nom == "profilni_faollashtir":
        yangi = db.query(m.SohaProfil).filter(
            m.SohaProfil.kalit == kirish["kalit"]).first()
        if not yangi:
            return {"xato": f"'{kirish['kalit']}' profili topilmadi"}
        for p in db.query(m.SohaProfil).all():
            p.faol = (p.id == yangi.id)
        db.add(m.AuditLog(who="AI agent", action="Soha profili faollashtirildi",
                          detail=yangi.kalit))
        db.commit()
        domain.qayta_yukla(db)
        return {"ok": True, "faol": yangi.kalit}

    if nom == "sinov_buyurtma":
        from .routers.orders import _Vaqtinchalik, retsept_narxi
        p = domain.profil()
        miqdor = kirish.get("miqdor") or 1
        tayyor, xato = domain.tayyorla(dict(kirish["qiymatlar"]))
        if xato:
            return {"xato": xato}
        soxta = _Vaqtinchalik(tayyor, miqdor)
        natija = {
            "profil": p.nom,
            "olcham": domain.olcham_matni(soxta),
            "tarkib": domain.tarkib_matni(soxta),
            "hujjat": domain.mahsulot_matni(soxta),
            "birlik": p.birlik,
            "retsept": [
                {"material": q["material"], "birlik": q["birlik"],
                 "miqdor": float(q["miqdor"])}
                for q in domain.retsept_qatorlari(soxta)],
        }
        if p.narx.get("usul") == "retsept":
            h = retsept_narxi(db, tayyor, miqdor, "Standart")
            natija["narx"] = {
                "material_1dona": float(h["material_1dona"]),
                "ish_haqi_1dona": float(h["ish_haqi_1dona"]),
                "tannarx": float(h["unit_cost"]),
                "taklif_narxi": float(h["unit_price"]),
                "ogohlantirish": h["ogohlantirish"],
            }
        return natija

    # ---- BO'LIM AGENTLARI ASBOBLARI (faqat O'QIYDI) -----------------
    # Bularning birortasi ham bazaga yozmaydi: agent ko'rsatadi va
    # hisoblaydi, qaror odamniki. Shuning uchun ular xavfsiz va ko'p
    # rolga ochiq.

    if nom == "ombor_qoldigi":
        chiqish = []
        for mat in db.query(m.Material).filter(m.Material.active.is_(True)).all():
            lots = (db.query(m.MaterialLot)
                    .filter(m.MaterialLot.material_id == mat.id,
                            m.MaterialLot.remaining > 0).all())
            chiqish.append({
                "material": mat.name, "birlik": mat.unit,
                "qoldiq": float(mat.stock_qty or 0),
                "eng_past": float(mat.min_stock or 0),
                "oxirgi_narx": float(mat.last_price or 0),
                "partiyalar": len(lots)})
        return {"ombor": chiqish}

    if nom == "buyurtmalar":
        from datetime import date
        q = db.query(m.Order)
        if kirish.get("holat"):
            q = q.filter(m.Order.status == kirish["holat"])
        chiqish = []
        nechta = max(1, min(int(kirish.get("nechta") or 20), 60))
        for o in q.order_by(m.Order.created_at.desc()).limit(nechta):
            kechikkan = bool(o.due_date and o.due_date < date.today()
                             and domain.manosi(o.status) not in
                             ("topshirildi", "bekor"))
            chiqish.append({
                "id": o.id, "mijoz": o.client.company,
                "mahsulot": domain.tarkib_matni(o) or o.product_name,
                "olcham": domain.olcham_matni(o),
                "miqdor": float(o.qty), "birlik": domain.profil().birlik,
                "summa": float(o.total), "maqom": o.status,
                "muddat": o.due_date.isoformat() if o.due_date else None,
                "kechikkan": kechikkan})
        return {"buyurtmalar": chiqish, "korsatilgan": len(chiqish),
                "jami_soni": q.count()}

    if nom == "buyurtma_retsepti":
        from .services import material_top, _konversiya
        o = db.get(m.Order, kirish["buyurtma_id"])
        if not o:
            return {"xato": "Buyurtma topilmadi"}
        qatorlar = domain.retsept_qatorlari(o)
        if not qatorlar:
            # Karton hali eski `xomashyo.m2_marka` yo'lida — retsepti yo'q.
            # Agent bunda ham ko'r qolmasligi kerak, shuning uchun o'sha
            # yo'ldan hisoblab beramiz. (Ikkala yo'l birlashtirilgach
            # bu shox olib tashlanadi.)
            xom, marka = domain.xomashyo_kerak(o)
            if xom is None:
                return {"buyurtma_id": o.id, "retsept_bor": False,
                        "izoh": "Bu sohada avtomatik xomashyo hisobi yo'q"}
            qatorlar = [{"material": marka, "birlik": "m²", "miqdor": xom}]
        natija, yetadi = [], True
        for q in qatorlar:
            mat = material_top(db, q["material"])
            qator = {"material": q["material"], "birlik": q["birlik"],
                     "kerak": float(q["miqdor"])}
            if mat is None:
                qator.update({"omborda": 0, "yetadi": False,
                              "izoh": "ombor kartochkasi yo'q"})
                yetadi = False
            else:
                try:
                    koef = _konversiya(mat, q["birlik"])
                except ValueError as e:
                    qator.update({"yetadi": False, "izoh": str(e)})
                    yetadi = False
                    natija.append(qator); continue
                kerak = Decimal(str(q["miqdor"])) * koef
                bor = Decimal(str(mat.stock_qty or 0))
                qator.update({"omborda": float(bor),
                              "material_birligi": mat.unit,
                              "yetadi": bor >= kerak,
                              "yetishmayapti": float(max(kerak - bor, 0))})
                if bor < kerak:
                    yetadi = False
            natija.append(qator)
        return {"buyurtma_id": o.id, "retsept_bor": True,
                "qatorlar": natija, "yetadi": yetadi}

    if nom == "qarzdorlar":
        # QARZ MOLIYA BO'LIMI BILAN BIR XIL MANBADAN.
        #
        # Ilgari bu yerda qarz alohida hisoblanardi: buyurtma `total` i
        # bo'yicha, topshirilgan ulush emas. Natijada AI «jami qarz
        # 1 457 mln» deb aytardi, moliya ekranida esa 853 mln turardi.
        # Foydalanuvchi uchun bu eng yomon holat — qaysi biriga
        # ishonishni bilmaydi. Endi ikkalasi ham `debt_aging` dan.
        from datetime import date
        chiqish = []
        telefonlar = {c.id: c.phone for c in db.query(m.Client).all()}
        for q in s.debt_aging(db):
            c_id = q["client_id"]
            muddatlar = [o.payment_due_date for o in
                         db.query(m.Order).filter(m.Order.client_id == c_id,
                                                  m.Order.delivered_qty > 0)
                         if o.payment_due_date]
            eng_eski = min(muddatlar) if muddatlar else None
            # MAYDON TARTIBI MUHIM. Model jadvalni shu tartibda chizadi,
            # telefon esa `qarz` dan oldin turganda mobil ekranda aynan
            # SAVOLNING JAVOBI — summa — o'ngga surilib ko'rinmay qolardi
            # (brauzerda ko'rildi). Eng muhim raqam nomdan keyin turadi,
            # telefon esa oxiriga o'tkazildi.
            chiqish.append({
                "mijoz_id": c_id, "mijoz": q["company"],
                "qarz": round(q["debt"], 2),
                "kredit_limiti": q["credit_limit"],
                "qora_royxatda": q["blacklisted"],
                "muddat_boyicha": q["aging"],
                "eng_eski_muddat": eng_eski.isoformat() if eng_eski else None,
                "kechikkan_kun": (date.today() - eng_eski).days
                                 if eng_eski and eng_eski < date.today() else 0,
                "telefon": telefonlar.get(c_id, "")})
        # ENG KATTALARI qaytariladi, hammasi emas.
        #
        # Nega: 53 mijozning hammasini bersak, model ularni jadvalga
        # ko'chirishga urinadi va chiqish byudjetiga urilib, javob
        # o'rtasida uzilib qoladi (MALFORMED_FUNCTION_CALL). Amalda
        # rahbarga eng katta qarzdorlar kerak; qolgani jamida ko'rinadi.
        nechta = int(kirish.get("nechta") or 15)
        nechta = max(1, min(nechta, 50))
        jami = round(sum(x["qarz"] for x in chiqish), 2)
        return {"qarzdorlar": chiqish[:nechta],
                "korsatilgan": min(nechta, len(chiqish)),
                "jami_soni": len(chiqish),
                "jami_qarz": jami}

    if nom == "pul_holati":
        from .routers.finance import _sotilgan
        sotilgan = db.query(m.Order).filter(
            m.Order.status.in_(_sotilgan())).all()
        jami_sotuv = sum(Decimal(str(o.total)) for o in sotilgan)
        tolovlar = sum(Decimal(str(p.amount)) for p in db.query(m.Payment).all())
        # Mijozlar qarzi ham moliya bo'limi bilan bir xil manbadan
        mijoz_qarzi = sum(Decimal(str(x["debt"])) for x in s.debt_aging(db))
        kassa = db.query(m.KassaEntry).all()
        kirim = sum(Decimal(str(k.amount)) for k in kassa if k.direction == "Kirim")
        chiqim = sum(Decimal(str(k.amount)) for k in kassa if k.direction == "Chiqim")
        xaridlar = db.query(m.Purchase).all()
        xarid_qarz = sum(Decimal(str(p.total)) - Decimal(str(p.paid_amount or 0))
                         for p in xaridlar)
        return {
            "jami_sotuv": float(jami_sotuv),
            "tolovlar": float(tolovlar),
            "mijozlar_qarzi": float(mijoz_qarzi),
            "kassa_qoldigi": float(kirim - chiqim),
            "yetkazib_beruvchiga_qarz": float(xarid_qarz),
            "buyurtmalar_soni": len(sotilgan)}

    if nom == "mijoz_hisobi":
        c = db.get(m.Client, kirish["mijoz_id"])
        if not c:
            return {"xato": "Mijoz topilmadi"}
        # Bitta manba (`client_balance`) — moliya ekrani ham shundan
        bal = s.client_balance(db, c.id)
        jami, tolangan = bal["taken"], bal["paid"]
        return {
            "mijoz": c.company, "telefon": c.phone, "toifa": c.category,
            "kredit_limiti": float(c.credit_limit or 0),
            "qora_royxatda": c.blacklisted,
            "buyurtmalar": [
                {"id": o.id, "mahsulot": domain.tarkib_matni(o),
                 "miqdor": float(o.qty), "summa": float(o.total),
                 "maqom": o.status,
                 "sana": o.created_at.date().isoformat()} for o in c.orders[-20:]],
            "tolovlar": [
                {"summa": float(p.amount), "usul": p.method,
                 "sana": p.paid_at.isoformat()} for p in c.payments[-20:]],
            "olingan_mol_qiymati": float(jami), "jami_tolov": float(tolangan),
            "qoldiq_qarz": float(bal["debt"])}

    if nom == "korsat":
        xom = kirish.get("komponentlar_json")
        # Ba'zi model to'g'ridan-to'g'ri ro'yxat yuborishi mumkin —
        # qabul qilamiz, qaytarib yubormaymiz.
        if isinstance(xom, list):
            royxat = xom
        else:
            matn = str(xom or "").strip()
            # Model JSON ni ```json ``` bloki ichida yuborishi odatiy hol
            if matn.startswith("```"):
                matn = matn.strip("`")
                matn = matn.split("\n", 1)[-1] if "\n" in matn else matn
                matn = matn.removeprefix("json").strip()
            try:
                royxat = json.loads(matn or "[]")
            except ValueError as e:
                # Xato MODELGA qaytadi — u tuzatib qayta yuboradi
                return {"xato": f"komponentlar_json buzuq JSON: {e}"}
        if isinstance(royxat, dict):
            royxat = [royxat]
        # Komponentlar TEKSHIRILADI (app/genui.py). Modelga esa nechtasi
        # qabul qilingani qaytariladi — buzuq komponent yuborsa, buni
        # bilib, keyingi qadamda tuzatadi.
        toza = genui.tekshir_royxat(royxat)
        if not toza:
            return {"xato": "birorta komponent tekshiruvdan o'tmadi — "
                            "«tur» maydonini va ruxsat etilgan turlarni tekshiring"}
        return {"ok": True, "chizildi": len(toza), "_komponentlar": toza}

    return {"xato": f"'{nom}' — noma'lum asbob"}


# =====================================================================
#  Suhbat halqasi
# =====================================================================

# Asbob javobi modelga MATN bo'lib boradi va u shu matnni jadvalga
# ko'chirmoqchi bo'ladi. Javob juda katta bo'lsa model chiqish
# byudjetiga urilib, `korsat` chaqiruvi o'rtasida uzilib qoladi —
# API buni MALFORMED_FUNCTION_CALL deb qaytaradi va javob BUTUNLAY
# yo'qoladi. Shuning uchun har asbob javobi shu chegara bilan
# qisqartiriladi. Yangi asbob qo'shilganda ham himoya o'z-o'zidan
# ishlaydi — har biriga alohida chegara yozish shart emas.
MAX_ASBOB_JAVOBI = 12_000     # belgi

# Javob uzilib qolganda modelga qo'shiladigan ko'rsatma. Ataylab qisqa
# va aniq: «kamroq yoz» degani yetarli emas, aniq son kerak.
QISQARTIR_OGOHI = """

## DIQQAT — OLDINGI URINISH UZILIB QOLDI

Javobing juda uzun bo'ldi va yarmida uzildi. Bu safar QISQA yoz:
jadvalda ko'pi bilan 10 qator, har qatorda 4 ustun. Qolganini
matnda bir gap bilan ayt («yana 25 ta mijoz bor»)."""


def _javobni_qisqartir(natija: dict) -> dict:
    """Katta ro'yxatlarni kesadi va modelga nima bo'lganini aytadi."""
    xom = json.dumps(natija, ensure_ascii=False, default=str)
    if len(xom) <= MAX_ASBOB_JAVOBI:
        return natija

    qisqa = dict(natija)
    for kalit, qiymat in natija.items():
        if not isinstance(qiymat, list) or len(qiymat) <= 5:
            continue
        # Ro'yxatni ikkiga bo'lib qisqartiramiz, chegaraga sig'guncha
        n = len(qiymat)
        while n > 5:
            n //= 2
            qisqa[kalit] = qiymat[:n]
            if len(json.dumps(qisqa, ensure_ascii=False, default=str)) <= MAX_ASBOB_JAVOBI:
                break
        qisqa["_qisqartirildi"] = (
            f"«{kalit}» juda uzun edi: {len(qiymat)} tadan {n} tasi berildi. "
            f"Kerak bo'lsa `nechta` yoki filtr bilan qayta so'rang.")
    return qisqa


def _ai_sarf_yoz(javob: dict, agent_kalit: str, user_login: str = "") -> None:
    """AI so'rovini boshqaruv bazasidagi `ai_sarf` ga yozadi.

    Ijarachiliksiz rejimda (akkaunt yo'q) — o'tkazib yuboriladi.
    Xatosi AI javobini TO'XTATMAYDI: sarf yozilmasa ham foydalanuvchi
    javobsiz qolmasin. Har LLM chaqiruvi alohida yoziladi (har qadam
    o'z tokenini sarflaydi)."""
    try:
        from . import tenancy
        akkaunt = tenancy.joriy() if tenancy.yoqilganmi() else None
        if not akkaunt:
            return
        from .platforma.db import BoshqaruvSession
        from .platforma import xizmat as px
        bdb = BoshqaruvSession()
        try:
            px.sarf_yoz(
                bdb, akkaunt.id, javob.get("provayder", ""),
                javob.get("model", ""),
                int(javob.get("kirish_token", 0) or 0),
                int(javob.get("chiqish_token", 0) or 0),
                agent=agent_kalit, user_login=user_login,
                muvaffaqiyat=not javob.get("rad_etildi"))
        finally:
            bdb.close()
    except Exception:                                  # noqa: BLE001
        log.warning("AI sarfi yozilmadi (javob buzilmadi)")


def suhbat_oqim(db, xabarlar: list[dict], agent_kalit: str = "yordamchi",
                user_login: str = "", rol: str = ""):
    """Bitta navbatni yuritadi va HAR QADAMNI oqim sifatida chiqaradi.

    NEGA OQIM: agent bitta savolga 10–25 soniya sarflaydi (model
    o'ylaydi, asbob chaqiradi, yana o'ylaydi). Shu vaqt davomida
    ekranda faqat «O'ylayapman…» tursa, foydalanuvchi tizim qotib
    qoldimi deb o'ylaydi va sahifani yangilaydi — javob esa yo'qoladi.
    Endi u qaysi asbob ishlayotganini ko'rib turadi.

    Chiqaradigan hodisalar (har biri lug'at):
        {"tur": "qadam",  "nomer": 1}              — modelga so'rov ketdi
        {"tur": "asbob",  "nom": "qarzdorlar"}     — asbob chaqirilmoqda
        {"tur": "asbob_ok", "nom": ..., "xato": bool}
        {"tur": "yakun",  ...}                     — to'liq natija

    `suhbat()` shu generatorning ustiga qurilgan — eski chaqiruvchilar
    (masalan Telegram bot) o'zgarishsiz ishlayveradi.
    """
    # Eski agent kalitlari («moliya», «ombor»…) ham qabul qilinadi —
    # hammasi BITTA yordamchiga olib boradi (eski havolalar buzilmasin).
    if agent_kalit not in AGENTLAR:
        agent_kalit = YORDAMCHI_KALIT
    a = AGENTLAR[agent_kalit]

    # ASBOBLAR ROL BO'YICHA FILTRLANADI — himoyaning asosiy joyi.
    # Sklad mudiriga `qarzdorlar` umuman berilmaydi, ya'ni model uni
    # chaqira olmaydi (ilgari bu agent darajasida edi).
    # ROL — HAR DOIM YUQORI CHEGARA, qaysi agent so'ralganidan qat'i
    # nazar. Ilgari bu faqat `YORDAMCHI_KALIT` uchun ishlardi va eski
    # kalitlar («moliya») uni chetlab o'tardi — sklad mudiri moliya
    # asboblarini olib qolardi. Marshrutizator buni 403 bilan to'xtatadi,
    # bu esa ikkinchi qatlam: u yerdan o'tib ketilsa ham model
    # taqiqlangan asbobni KO'RMAYDI.
    if not rol:
        ruxsat = set(a["asboblar"])
    elif agent_kalit == YORDAMCHI_KALIT:
        ruxsat = set(rolga_asboblar(rol))
    else:
        ruxsat = set(a["asboblar"]) & set(rolga_asboblar(rol))
    # `korsat` HAR agentga beriladi: ko'rinish chizish bo'limga bog'liq
    # emas, hammasiga kerak.
    asboblar = [x for x in HAMMA_ASBOBLAR if x["nom"] in ruxsat]
    asboblar.append(KORSAT_ASBOBI)
    # Ko'rsatma KODDAN emas, `korsatma.ol()` dan — mijoz yoki biz
    # uni bazadan o'zgartirgan bo'lishimiz mumkin. Xavfsizlik
    # qismi (`_UMUMIY_USLUB`) ichida majburan qo'shiladi.
    from . import korsatma as _kors
    korsatma = _kors.ol(agent_kalit) + genui.korsatma_matni()
    tarix = list(xabarlar)
    izlar = []
    komponentlar = []
    provayder = model = ""

    def yakun(javob_matni):
        return {"tur": "yakun", "xabarlar": tarix, "javob": javob_matni,
                "izlar": izlar, "komponentlar": komponentlar,
                "provayder": provayder, "model": model}

    qayta_boshlandi = False
    qisqartir_ogohi = ""
    qadam = 0
    while qadam < MAX_QADAM:
        qadam += 1
        yield {"tur": "qadam", "nomer": qadam}
        try:
            # Birinchi javobdan keyin model QOTIRILADI — suhbat o'rtasida
            # boshqa modelga o'tish asbob chaqiruvi muhrini buzadi
            # (app/llm.py dagi izohga qarang).
            javob = llm.javob_ol(tarix, asboblar,
                                 korsatma + qisqartir_ogohi, model or None)
        except llm.JavobBuzildi:
            # Model juda uzun asbob argumenti yozib, yarmida uzildi.
            # Bir marta QISQAROQ yozishni aytib qayta uramiz — bu
            # haqiqiy ma'lumotda (50 mijoz, uzun nomlar) tez-tez
            # uchraydi va aks holda javob butunlay yo'qoladi.
            if qisqartir_ogohi:
                yield yakun("Javob juda uzun chiqdi. Savolni toraytiring "
                            "— masalan «eng katta 5 tasini ko'rsat».")
                return
            log.warning("Javob uzilib qoldi — qisqartirish ogohi bilan qayta")
            qisqartir_ogohi = QISQARTIR_OGOHI
            qadam -= 1                  # shu qadamni qaytadan
            yield {"tur": "qayta_urinish"}
            continue
        except llm.LLMBand:
            # Qotirilgan model o'rtada tugab qoldi (kvota). Zaxira
            # modelga O'TIB BO'LMAYDI — uning muhri boshqa. Shuning
            # uchun navbatni BOSHIDAN boshlaymiz: tarix tozalanadi,
            # model bo'shatiladi va zanjir keyingisini tanlaydi.
            # Asboblar qaytadan chaqiriladi — bir oz isrof, lekin
            # foydalanuvchi javobsiz qolmaydi.
            if qayta_boshlandi or not model:
                raise
            log.warning("«%s» o'rtada tugadi — navbat zaxira model bilan "
                        "qaytadan boshlanmoqda", model)
            qayta_boshlandi = True
            tarix = list(xabarlar)
            izlar.clear()
            komponentlar.clear()
            model = ""
            qadam = 0
            yield {"tur": "qayta_boshlandi"}
            continue
        provayder, model = javob["provayder"], javob["model"]
        # AI SARFI — har chaqiruvdan keyin (ijarachilikda ai_sarf ga).
        _ai_sarf_yoz(javob, agent_kalit, user_login)

        if javob["rad_etildi"]:
            yield yakun("Kechirasiz, bu so'rovga javob bera olmadim. "
                        "Iltimos, boshqacha ifodalab ko'ring.")
            return

        tarix.append({"rol": "assistant", "matn": javob["matn"],
                      "asbob_chaqiruvlari": javob["chaqiruvlar"]})

        if not javob["chaqiruvlar"]:
            yield yakun(javob["matn"])
            return

        natijalar = []
        for chaqiruv in javob["chaqiruvlar"]:
            yield {"tur": "asbob", "nom": chaqiruv["nom"]}
            try:
                natija = _asbobni_bajar(db, chaqiruv["nom"], chaqiruv["kirish"] or {})
                xato = bool(natija.get("xato"))
            except Exception as e:                      # noqa: BLE001
                # Asbob yiqilsa butun suhbat to'xtamasin — xato modelga
                # qaytadi va u boshqacha urinib ko'radi.
                log.exception("Agent asbobi yiqildi: %s", chaqiruv["nom"])
                db.rollback()
                natija, xato = {"xato": str(e)}, True
            yield {"tur": "asbob_ok", "nom": chaqiruv["nom"], "xato": xato}

            # Komponentlar javobga alohida chiqadi, model tarixiga esa
            # ularning NUSXASI kerak emas — faqat «chizildi» tasdig'i.
            # Aks holda har navbatda butun jadval tarixga qo'shilib,
            # tokenlar tez tugab qolardi.
            chizilgan = natija.pop("_komponentlar", None)
            if chizilgan:
                komponentlar.extend(chizilgan)
            izlar.append({"asbob": chaqiruv["nom"], "kirish": chaqiruv["kirish"],
                          "natija": natija})
            natijalar.append({
                "id": chaqiruv["id"], "nom": chaqiruv["nom"],
                "natija": json.dumps(_javobni_qisqartir(natija),
                                     ensure_ascii=False, default=str),
                "xato": xato})
        tarix.append({"rol": "user", "matn": "", "asbob_natijalari": natijalar})

    yield yakun("Juda ko'p qadam bo'ldi — to'xtatdim. "
                "Nima qilishimni aniqroq ayting.")


def suhbat(db, xabarlar: list[dict], agent_kalit: str = "yordamchi",
           user_login: str = "", rol: str = "") -> dict:
    """Oqimsiz variant — oxirgi natijani qaytaradi.

    `suhbat_oqim` ustiga qurilgan, ya'ni mantiq bitta joyda. Oqim
    kerak bo'lmagan chaqiruvchilar (bot, testlar) shuni ishlatadi.
    """
    oxirgi = None
    for hodisa in suhbat_oqim(db, xabarlar, agent_kalit, user_login, rol):
        if hodisa.get("tur") == "yakun":
            oxirgi = hodisa
    if oxirgi is None:                       # bo'lmasligi kerak, lekin
        return {"xabarlar": list(xabarlar), "javob": "", "izlar": [],
                "komponentlar": [], "provayder": "", "model": ""}
    natija = dict(oxirgi)
    natija.pop("tur", None)
    return natija


# =====================================================================
#  BO'LIM AGENTLARI
#
#  Bitta halqa, ko'p «shaxs». Har agent = tizim ko'rsatmasi + asboblar
#  QISMI. Nega bitta katta agent emas: 30 ta asbob berilsa model qaysi
#  birini chaqirishni chalkashtiradi va aniqligi tushadi. Har bo'limga
#  o'z ishiga kerakli asbob berilsa — javob aniq va tez.
#
#  Har agentga BERILMAGAN asbob unga umuman ko'rinmaydi: ombor agenti
#  profil almashtira olmaydi, sozlash agenti pul yozolmaydi.
# =====================================================================

_UMUMIY_USLUB = """

## Uslub
O'zbek tilida yoz. Qisqa gaplar. Raqamlarni aniq ayt, taxmin qilma —
bilmasang asbob chaqirib bil. Ma'lumot yo'q bo'lsa «ma'lumot yo'q» deb
ayt, o'ylab topma. Uzun hisobot yozma.

## Jadval ustunlari
Jadvalda 3-4 tadan ortiq ustun bo'lmasin va SO'RALMAGAN ustunni
qo'shma. Birinchi ustun — nom yoki raqam, IKKINCHI ustun — savolning
javobi bo'lgan raqam. Telefon, id, manzil kabilar faqat so'ralgandagina
chiqadi.

Nega: javob telefonda ham o'qiladi, ekran tor. Ortiqcha ustun qo'shsang
savolning javobi ekrandan surilib chiqib ketadi va odam uni ko'rmaydi."""

AGENTLAR = {
    "sozlash": {
        "nom": "Sozlash yordamchisi",
        "izoh": "Biznesingizni so'rab, tizimni shunga moslaydi",
        "rollar": ["Rahbar"],
        "asboblar": ["modullarni_kor", "profillarni_kor", "profilni_oqi",
                     "profil_saqla", "profilni_faollashtir", "sinov_buyurtma"],
        "korsatma": TIZIM_KORSATMASI,
    },
    "ombor": {
        "nom": "Ombor yordamchisi",
        "izoh": "Nima tugayapti, qancha kerak, nima sotib olish kerak",
        "rollar": ["Rahbar", "Sklad mudiri", "Sex boshlig'i"],
        "asboblar": ["ombor_qoldigi", "buyurtma_retsepti", "sinov_buyurtma"],
        "korsatma": """Sen — ombor yordamchisisan.

Sklad mudiri savol beradi: nima qoldi, qaysi buyurtmaga nima yetmaydi,
nima sotib olish kerak. Javobni RAQAM bilan ber.

Ish tartibing:
1. `ombor_qoldigi` bilan hozirgi holatni ol.
2. Savol biror buyurtma haqida bo'lsa `buyurtma_retsepti` bilan
   nima ketishini va yetadimi-yo'qmi ko'r.
3. «Nima olish kerak» degan savolga — yetishmayotgan miqdorni ayt,
   ustiga zaxira qo'shishni MASLAHAT ber, lekin o'zing qaror qilma.

Ombordan hech narsa yechmaysan va kirim qilmaysan — bu sklad mudirining
ishi. Sen faqat ko'rsatasan va hisoblaysan.""",
    },
    "moliya": {
        "nom": "Moliya yordamchisi",
        "izoh": "Kim qarzdor, pul holati, muddati o'tganlar",
        "rollar": ["Rahbar", "Buxgalter"],
        "asboblar": ["qarzdorlar", "pul_holati", "mijoz_hisobi"],
        "korsatma": """Sen — moliya yordamchisisan.

Rahbar yoki buxgalter savol beradi: kim qancha qarzdor, muddati
o'tganmi, bu oy qancha tushdi. Javobni RAQAM va SANA bilan ber.

Ish tartibing:
1. `pul_holati` — umumiy manzara (tushum, qarz, kassa).
2. `qarzdorlar` — kim qancha, muddati o'tganini alohida ajrat.
3. Aniq mijoz haqida so'ralsa `mijoz_hisobi` bilan uning
   buyurtmalari va to'lovlarini ko'r.

Pul yozmaysan va to'lov o'chirmaysan — bu buxgalterning ishi.
Qarz undirish bo'yicha maslahat berishing mumkin, lekin mijozga
o'zing xabar yubormaysan.""",
    },
    "buyurtma": {
        "nom": "Buyurtma yordamchisi",
        "izoh": "Zakazlar holati, smeta hisobi, qaysi biri kechikyapti",
        "rollar": ["Rahbar", "Menejer", "Sex boshlig'i"],
        "asboblar": ["buyurtmalar", "buyurtma_retsepti", "sinov_buyurtma",
                     "ombor_qoldigi"],
        "korsatma": """Sen — buyurtma yordamchisisan.

Menejer savol beradi: qaysi zakazlar qayerda turibdi, qaysi biri
kechikyapti, bu zakazga qancha material ketadi, narxi qancha bo'ladi.

Ish tartibing:
1. `buyurtmalar` — holat bo'yicha ro'yxat.
2. Aniq zakaz haqida so'ralsa `buyurtma_retsepti` bilan material va
   yetishmovchilikni ko'r.
3. «Bunday zakaz qancha turadi» degan savolga `sinov_buyurtma` bilan
   hisoblab ber — bazaga hech narsa yozilmaydi.

Buyurtma yaratmaysan va statusini o'zgartirmaysan — bu menejerning
ishi. Sen hisoblaysan va ko'rsatasan.""",
    },
}




# =====================================================================
#  BITTA YORDAMCHI (2026-08-20)
#
# Ilgari 4 ta alohida agent bor edi (sozlash / ombor / moliya /
# buyurtma) va foydalanuvchi qaysi biriga savol berishni O'ZI tanlardi.
# Amalda bu noqulay: odam «qarzim qancha» deb so'ramoqchi, lekin avval
# «Moliya yordamchisi» ni tanlashi kerak edi. Savol chegarani kesib
# o'tsa («shu mijozga qancha mol bergan va qancha qarzi bor?») —
# ikkita agentga bo'lib so'rashga to'g'ri kelardi.
#
# Endi BITTA yordamchi. Nima o'zgardi va nima O'ZGARMADI:
#
#   O'ZGARDI:  foydalanuvchi agent tanlamaydi — shunchaki so'raydi
#   O'ZGARMADI: ROL CHEKLOVI. Ilgari cheklov AGENT darajasida edi
#              (moliya agenti faqat Rahbar/Buxgalterga ochiq), endi
#              ASBOB darajasida: sklad mudiri `qarzdorlar` asbobini
#              umuman KO'RMAYDI, ya'ni himoya aynan o'sha kuchda.
#
# Nega endi xavfsiz: asboblar jami 12 ta. Dastlabki tashvish «40 asbob
# berilsa model chalkashadi» edi — 12 ta zamonaviy model uchun muammo
# emas. Asbob soni 20 dan oshsa, bu qaror qayta ko'riladi.
# =====================================================================

# Har asbobni qaysi rol ishlatishi mumkin. Eski AGENTLAR dagi
# `rollar` maydonlarining BIRLASHMASI — himoya kuchi o'zgarmadi.
ASBOB_ROLLARI = {
    # Tizimni sozlash — faqat Rahbar (profil yaratadi/o'zgartiradi)
    "modullarni_kor":       ["Rahbar"],
    "profillarni_kor":      ["Rahbar"],
    "profilni_oqi":         ["Rahbar"],
    "profil_saqla":         ["Rahbar"],
    "profilni_faollashtir": ["Rahbar"],
    # Ombor va ishlab chiqarish
    "ombor_qoldigi":     ["Rahbar", "Sklad mudiri", "Sex boshlig'i", "Menejer"],
    "buyurtma_retsepti": ["Rahbar", "Sklad mudiri", "Sex boshlig'i", "Menejer"],
    "sinov_buyurtma":    ["Rahbar", "Sklad mudiri", "Sex boshlig'i", "Menejer"],
    # Buyurtmalar
    "buyurtmalar":       ["Rahbar", "Menejer", "Sex boshlig'i"],
    # MOLIYA — pul ma'lumoti. Sklad mudiri va sex boshlig'i KO'RMAYDI.
    "qarzdorlar":        ["Rahbar", "Buxgalter"],
    "pul_holati":        ["Rahbar", "Buxgalter"],
    "mijoz_hisobi":      ["Rahbar", "Buxgalter"],
}

YORDAMCHI_KALIT = "yordamchi"

YORDAMCHI_KORSATMASI = """Sen — korxonaning ERP yordamchisisan.

Rahbar, menejer, buxgalter, sklad mudiri va sex boshlig'i senga savol
beradi: ombor, buyurtma, mijoz qarzi, pul holati, tizim sozlamasi.
Javobni RAQAM va SANA bilan ber.

MUHIM: senga berilgan asboblar foydalanuvchining ROLIGA qarab
tanlangan. Ro'yxatda yo'q asbobni chaqirma va «men buni ko'ra
olmayman» deb ayt — masalan sklad mudiri qarzdorlarni so'rasa,
«bu ma'lumot buxgalter va rahbarga ochiq» deb javob ber.

Ish tartibing:
1. Savol qaysi sohaga tegishli ekanini o'zing aniqla — foydalanuvchi
   bo'lim tanlamaydi.
2. Kerakli asbobni chaqir. Bir nechta kerak bo'lsa ketma-ket chaqir
   (masalan «bu mijozga qancha mol berdik va qarzi qancha?» —
   `buyurtmalar` va `mijoz_hisobi`).
3. Raqamni ASBOBDAN ol. Bilmasang «ma'lumot yo'q» deb ayt.

Sen bazaga O'ZING yozmaysan. O'zgartirish kerak bo'lsa TAKLIF
qilasan — tugmani odam bosadi."""


# Bitta yordamchining ta'rifi. Eski `AGENTLAR` saqlanadi (ko'rsatma
# tahrirlash va eski chaqiruvlar uchun), lekin ishlatiladigan
# yordamchi shu.
AGENTLAR[YORDAMCHI_KALIT] = {
    "nom": "Yordamchi",
    "izoh": "Ombor, buyurtma, mijoz, pul va sozlama — hammasi bitta joyda",
    # Hamma rol ochiq: nima ko'rishi ASBOB darajasida hal qilinadi
    "rollar": ["Rahbar", "Menejer", "Buxgalter", "Sklad mudiri",
               "Sex boshlig'i"],
    "asboblar": list(ASBOB_ROLLARI.keys()),
    "korsatma": YORDAMCHI_KORSATMASI,
}


def rolga_asboblar(rol: str) -> list[str]:
    """Shu rol ishlatishi mumkin bo'lgan asboblar."""
    return [nom for nom, rollar in ASBOB_ROLLARI.items() if rol in rollar]


def agent_royxati(rol: str) -> list[dict]:
    """Ochiq yordamchilar — endi BITTA.

    Ro'yxat shakli saqlanadi (frontend va eski chaqiruvchilar
    o'zgarmasin), lekin ichida bitta yozuv bo'ladi. Rol nima
    ko'rishini asboblar hal qiladi (`rolga_asboblar`)."""
    y = AGENTLAR[YORDAMCHI_KALIT]
    n = len(rolga_asboblar(rol))
    return [{"kalit": YORDAMCHI_KALIT, "nom": y["nom"], "izoh": y["izoh"],
             "asbob_soni": n}]


# --- Bo'lim agentlari uchun qo'shimcha asboblar ------------------------

HAMMA_ASBOBLAR += [
    {
        "nom": "ombor_qoldigi",
        "izoh": ("Ombordagi materiallar: nomi, birligi, qoldig'i, eng past "
                 "chegarasi va partiyalari (FIFO narxlari bilan)."),
        "sxema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "nom": "buyurtmalar",
        "izoh": ("Buyurtmalar ro'yxati. `holat` berilsa faqat o'sha maqomdagi, "
                 "berilmasa hammasi. Har biri: mijoz, mahsulot, miqdor, summa, "
                 "maqom, muddat va kechikkanmi."),
        "sxema": {
            "type": "object",
            "properties": {
                "holat": {"type": "string",
                          "description": "Maqom nomi, masalan 'Kutishda'"},
                "nechta": {"type": "integer",
                           "description": "Nechta buyurtma (standart 20)"}},
            "additionalProperties": False,
        },
    },
    {
        "nom": "buyurtma_retsepti",
        "izoh": ("Bitta buyurtmaga qancha material ketishi va omborda "
                 "yetadimi. Ishlab chiqarishga berishdan oldin tekshirish uchun."),
        "sxema": {
            "type": "object",
            "properties": {"buyurtma_id": {"type": "integer"}},
            "required": ["buyurtma_id"],
            "additionalProperties": False,
        },
    },
    {
        "nom": "qarzdorlar",
        "izoh": ("Qarzdor mijozlar: kim qancha qarzdor, muddati o'tganmi, "
                 "necha kun kechikkan. Eng kattalaridan boshlab beriladi. "
                 "`nechta` — nechtasi kerakligi (standart 15)."),
        "sxema": {
            "type": "object",
            "properties": {"nechta": {"type": "integer",
                                      "description": "Nechta mijoz (1-50)"}},
            "additionalProperties": False,
        },
    },
    {
        "nom": "pul_holati",
        "izoh": ("Umumiy moliya manzarasi: tushum, qarz, kassa qoldig'i, "
                 "yetkazib beruvchiga qarz."),
        "sxema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "nom": "mijoz_hisobi",
        "izoh": ("Bitta mijozning hisobi: buyurtmalari, to'lovlari, qoldiq qarzi."),
        "sxema": {
            "type": "object",
            "properties": {"mijoz_id": {"type": "integer"}},
            "required": ["mijoz_id"],
            "additionalProperties": False,
        },
    },
]
