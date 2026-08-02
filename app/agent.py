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
import os

log = logging.getLogger("gofra.agent")

MODEL = "claude-opus-5"

# Suhbat qancha marta asbob chaqira olishi. Cheksiz halqadan himoya —
# model qandaydir sababga ko'ra to'xtamasa, so'rov abadiy osilib qolmasin.
MAX_QADAM = 12


def kalit_bormi() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


# =====================================================================
#  ASBOBLAR — agent shular orqali tizimga ta'sir qiladi
#
#  Ataylab TOR: profil o'qish/yozish/faollashtirish va sinov. Agentga
#  bazaga to'g'ridan-to'g'ri yozish yoki kod ishga tushirish berilmagan.
# =====================================================================

ASBOBLAR = [
    {
        "name": "modullarni_kor",
        "description": (
            "Mavjud ish tartiblari (modullar) ro'yxatini qaytaradi. "
            "Har modul — buyurtmaning hayot sikli (statuslar). Yangi profil "
            "yasashdan OLDIN chaqiring: mijoz biznesiga qaysi ish tartibi "
            "mos kelishini shundan tanlaysiz."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "profillarni_kor",
        "description": (
            "Bazadagi mavjud soha profillari ro'yxati. Mijoz biznesiga "
            "yaqin profil bormi — shuni tekshiring. Bor bo'lsa uni asos "
            "qilib oling, noldan yasamang."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "profilni_oqi",
        "description": (
            "Bitta profilning TO'LIQ ta'rifini (JSON) qaytaradi. Mavjud "
            "profilni namuna qilib olish yoki tahrirlash uchun."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"kalit": {"type": "string", "description": "Profil kaliti, masalan 'karton'"}},
            "required": ["kalit"],
            "additionalProperties": False,
        },
    },
    {
        "name": "profil_saqla",
        "description": (
            "Soha profilini yaratadi yoki yangilaydi. Ta'rif tuzilishi "
            "tizim ko'rsatmasida berilgan. Ta'rif TEKSHIRILADI — buzuq "
            "bo'lsa xato qaytadi va bazaga tushmaydi. Saqlash faollashtirmaydi."
        ),
        "input_schema": {
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
        "name": "profilni_faollashtir",
        "description": (
            "Profilni FAOL qiladi — shundan keyin butun tizim (buyurtma "
            "formasi, hujjatlar, ombor) shu sohaga moslashadi. Mijoz "
            "tasdiqlagandan keyin chaqiring."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"kalit": {"type": "string"}},
            "required": ["kalit"],
            "additionalProperties": False,
        },
    },
    {
        "name": "sinov_buyurtma",
        "description": (
            "Faol profil bilan SINOV buyurtmasi yasab ko'radi va natijani "
            "qaytaradi (o'lcham matni, tarkib, retsept, narx). Bazaga hech "
            "narsa yozilmaydi. Profilni mijozga ko'rsatishdan oldin shu "
            "bilan o'zingiz tekshiring — maydonlar to'g'ri hisoblanyaptimi."
        ),
        "input_schema": {
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
    from . import domain, models as m
    from .services import qqs_hisobla  # noqa: F401  (kelajakda smeta uchun)

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

    return {"xato": f"'{nom}' — noma'lum asbob"}


# =====================================================================
#  Suhbat halqasi
# =====================================================================

def suhbat(db, xabarlar: list[dict]) -> dict:
    """Bitta navbatni oxirigacha yuritadi (asboblar bilan birga).

    `xabarlar` — Anthropic formatidagi to'liq tarix. API holatsiz,
    shuning uchun har safar butun tarix yuboriladi.

    Qaytaradi: {"xabarlar": yangilangan tarix, "javob": matn, "izlar": [...]}
    """
    import anthropic

    client = anthropic.Anthropic()
    tarix = list(xabarlar)
    izlar = []   # foydalanuvchiga ko'rsatiladigan «nima qildim» izi

    for _ in range(MAX_QADAM):
        javob = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=[{"type": "text", "text": TIZIM_KORSATMASI,
                     # Ko'rsatma har so'rovda bir xil — keshlansa
                     # har navbatda qayta hisoblanmaydi.
                     "cache_control": {"type": "ephemeral"}}],
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            tools=ASBOBLAR,
            messages=tarix,
        )

        # Xavfsizlik klassifikatori rad etsa — `content` bo'sh bo'lishi
        # mumkin, shuning uchun `stop_reason` avval tekshiriladi.
        if javob.stop_reason == "refusal":
            return {"xabarlar": tarix, "izlar": izlar,
                    "javob": "Kechirasiz, bu so'rovga javob bera olmadim. "
                             "Iltimos, boshqacha ifodalab ko'ring."}

        tarix.append({"role": "assistant", "content": javob.content})

        asbob_chaqiruvlari = [b for b in javob.content if b.type == "tool_use"]
        if not asbob_chaqiruvlari:
            matn = "".join(b.text for b in javob.content if b.type == "text")
            return {"xabarlar": tarix, "javob": matn, "izlar": izlar}

        natijalar = []
        for chaqiruv in asbob_chaqiruvlari:
            try:
                natija = _asbobni_bajar(db, chaqiruv.name, chaqiruv.input or {})
                xato = False
            except Exception as e:                      # noqa: BLE001
                # Asbob yiqilsa butun suhbat to'xtamasin — xato modelga
                # qaytadi va u boshqacha urinib ko'radi.
                log.exception("Agent asbobi yiqildi: %s", chaqiruv.name)
                db.rollback()
                natija, xato = {"xato": str(e)}, True
            izlar.append({"asbob": chaqiruv.name, "kirish": chaqiruv.input,
                          "natija": natija})
            natijalar.append({
                "type": "tool_result", "tool_use_id": chaqiruv.id,
                "content": json.dumps(natija, ensure_ascii=False, default=str),
                "is_error": xato,
            })
        tarix.append({"role": "user", "content": natijalar})

    return {"xabarlar": tarix, "izlar": izlar,
            "javob": "Juda ko'p qadam bo'ldi — to'xtatdim. "
                     "Nima qilishimni aniqroq ayting."}
