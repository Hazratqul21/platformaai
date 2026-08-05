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

from . import llm

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

    from . import domain, models as m

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
        for o in q.order_by(m.Order.created_at.desc()).limit(100):
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
        return {"buyurtmalar": chiqish, "soni": len(chiqish)}

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
        from datetime import date
        chiqish = []
        for c in db.query(m.Client).all():
            # Qarz = buyurtmalar jami - to'lovlar + tizimdan oldingi qoldiq.
            # `total` QQS bilan, ya'ni mijoz TO'LAYDIGAN summa — qarz ham shu.
            jami = sum(Decimal(str(o.total)) for o in c.orders)
            tolangan = sum(Decimal(str(p.amount)) for p in c.payments)
            qarz = float(jami - tolangan + Decimal(str(c.opening_balance or 0)))
            if qarz <= 0:
                continue
            muddatlar = [o.payment_due_date for o in c.orders
                         if o.payment_due_date]
            eng_eski = min(muddatlar) if muddatlar else None
            chiqish.append({
                "mijoz_id": c.id, "mijoz": c.company, "telefon": c.phone,
                "qarz": round(qarz, 2),
                "eng_eski_muddat": eng_eski.isoformat() if eng_eski else None,
                "kechikkan_kun": (date.today() - eng_eski).days
                                 if eng_eski and eng_eski < date.today() else 0})
        chiqish.sort(key=lambda x: -x["qarz"])
        return {"qarzdorlar": chiqish,
                "jami_qarz": round(sum(x["qarz"] for x in chiqish), 2)}

    if nom == "pul_holati":
        from .routers.finance import _sotilgan
        sotilgan = db.query(m.Order).filter(
            m.Order.status.in_(_sotilgan())).all()
        jami_sotuv = sum(Decimal(str(o.total)) for o in sotilgan)
        tolovlar = sum(Decimal(str(p.amount)) for p in db.query(m.Payment).all())
        kassa = db.query(m.KassaEntry).all()
        kirim = sum(Decimal(str(k.amount)) for k in kassa if k.direction == "Kirim")
        chiqim = sum(Decimal(str(k.amount)) for k in kassa if k.direction == "Chiqim")
        xaridlar = db.query(m.Purchase).all()
        xarid_qarz = sum(Decimal(str(p.total)) - Decimal(str(p.paid_amount or 0))
                         for p in xaridlar)
        return {
            "jami_sotuv": float(jami_sotuv),
            "tolovlar": float(tolovlar),
            "mijozlar_qarzi": float(jami_sotuv - tolovlar),
            "kassa_qoldigi": float(kirim - chiqim),
            "yetkazib_beruvchiga_qarz": float(xarid_qarz),
            "buyurtmalar_soni": len(sotilgan)}

    if nom == "mijoz_hisobi":
        c = db.get(m.Client, kirish["mijoz_id"])
        if not c:
            return {"xato": "Mijoz topilmadi"}
        jami = sum(Decimal(str(o.total)) for o in c.orders)
        tolangan = sum(Decimal(str(p.amount)) for p in c.payments)
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
            "jami_buyurtma": float(jami), "jami_tolov": float(tolangan),
            "qoldiq_qarz": float(jami - tolangan +
                                 Decimal(str(c.opening_balance or 0)))}

    return {"xato": f"'{nom}' — noma'lum asbob"}


# =====================================================================
#  Suhbat halqasi
# =====================================================================

def suhbat(db, xabarlar: list[dict], agent_kalit: str = "sozlash") -> dict:
    """Bitta navbatni oxirigacha yuritadi (asboblar bilan birga).

    `xabarlar` — ICHKI ko'rinishdagi tarix (app/llm.py ga qarang). U
    provayderdan mustaqil: kalit almashtirilsa eski suhbat o'qilaveradi.

    Qaytaradi: {"xabarlar", "javob", "izlar", "provayder", "model"}
    """
    a = AGENTLAR[agent_kalit]
    asboblar = [x for x in HAMMA_ASBOBLAR if x["nom"] in a["asboblar"]]
    tarix = list(xabarlar)
    izlar = []
    provayder = model = ""

    for _ in range(MAX_QADAM):
        javob = llm.javob_ol(tarix, asboblar, a["korsatma"])
        provayder, model = javob["provayder"], javob["model"]

        if javob["rad_etildi"]:
            return {"xabarlar": tarix, "izlar": izlar,
                    "provayder": provayder, "model": model,
                    "javob": "Kechirasiz, bu so'rovga javob bera olmadim. "
                             "Iltimos, boshqacha ifodalab ko'ring."}

        tarix.append({"rol": "assistant", "matn": javob["matn"],
                      "asbob_chaqiruvlari": javob["chaqiruvlar"]})

        if not javob["chaqiruvlar"]:
            return {"xabarlar": tarix, "javob": javob["matn"], "izlar": izlar,
                    "provayder": provayder, "model": model}

        natijalar = []
        for chaqiruv in javob["chaqiruvlar"]:
            try:
                natija = _asbobni_bajar(db, chaqiruv["nom"], chaqiruv["kirish"] or {})
                xato = bool(natija.get("xato"))
            except Exception as e:                      # noqa: BLE001
                # Asbob yiqilsa butun suhbat to'xtamasin — xato modelga
                # qaytadi va u boshqacha urinib ko'radi.
                log.exception("Agent asbobi yiqildi: %s", chaqiruv["nom"])
                db.rollback()
                natija, xato = {"xato": str(e)}, True
            izlar.append({"asbob": chaqiruv["nom"], "kirish": chaqiruv["kirish"],
                          "natija": natija})
            natijalar.append({
                "id": chaqiruv["id"], "nom": chaqiruv["nom"],
                "natija": json.dumps(natija, ensure_ascii=False, default=str),
                "xato": xato})
        tarix.append({"rol": "user", "matn": "", "asbob_natijalari": natijalar})

    return {"xabarlar": tarix, "izlar": izlar,
            "provayder": provayder, "model": model,
            "javob": "Juda ko'p qadam bo'ldi — to'xtatdim. "
                     "Nima qilishimni aniqroq ayting."}


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
ayt, o'ylab topma. Uzun hisobot yozma."""

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
ishi. Sen faqat ko'rsatasan va hisoblaysan.""" + _UMUMIY_USLUB,
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
o'zing xabar yubormaysan.""" + _UMUMIY_USLUB,
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
ishi. Sen hisoblaysan va ko'rsatasan.""" + _UMUMIY_USLUB,
    },
}


def agent_royxati(rol: str) -> list[dict]:
    """Foydalanuvchi roliga ochiq agentlar."""
    return [{"kalit": k, "nom": a["nom"], "izoh": a["izoh"]}
            for k, a in AGENTLAR.items() if rol in a["rollar"]]


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
            "properties": {"holat": {"type": "string",
                                     "description": "Maqom nomi, masalan 'Kutishda'"}},
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
                 "necha kun kechikkan."),
        "sxema": {"type": "object", "properties": {}, "additionalProperties": False},
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
