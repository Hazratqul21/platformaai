"""CHUQUR SINOV — har sohada RAQAMLAR to'g'rimi.

`profil_test.py` dan farqi: u «200 qaytdimi» ni tekshiradi, bu esa
HISOB-KITOB to'g'rimi ni. Ishga tushirishdan oldin aynan shu kerak —
tizim javob berishi bilan to'g'ri javob berishi boshqa narsa.

Har soha uchun HAQIQIY stsenariy:
   1. profil faollashtiriladi
   2. ombor HAQIQIY narxlar bilan to'ldiriladi (ikki partiya — FIFO sinash uchun)
   3. mijoz + HAQIQIY miqdordagi buyurtma
   4. smeta hisobi tekshiriladi
   5. buyurtma to'liq sikldan yuriladi (xomashyo yechiladi)
   6. OMBOR HAQIQATAN kamayganmi — arifmetika tekshiriladi
   7. to'lov yoziladi, qarz to'g'ri chiqyaptimi
   8. hujjatlar yasaladi

TEKSHIRILADIGAN O'ZGARMASLAR (invariantlar):
   ombor_oldin - ombor_keyin == yechilgan miqdor
   jami        == narx × miqdor (+ QQS)
   qarz        == jami - to'lov
   FIFO        == arzon partiyadan boshlab

Ishga tushirish:
    DATABASE_URL=... SEED_EMPTY=1 PORT=8070 .venv/bin/python -m app.main
    BASE=http://localhost:8070 .venv/bin/python tests/chuqur_sinov.py
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

BASE = os.getenv("BASE", "http://localhost:8070")
XATOLAR: list[str] = []
OGOHLAR: list[str] = []


def call(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        gavda = e.read()
        try:
            return e.code, json.loads(gavda)
        except ValueError:
            return e.code, {"detail": gavda[:200].decode("utf-8", "replace")}


def bayt(path, token):
    req = urllib.request.Request(BASE + path)
    req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, 0


def tekshir(soha, nom, shart, izoh=""):
    if not shart:
        XATOLAR.append(f"{soha} · {nom} — {izoh}")
    return shart


def teng(soha, nom, a, b, aniqlik="0.01"):
    """Ikki son teng-mi. Pul va miqdorda float xatosi bo'lishi mumkin,
    shuning uchun aniq tenglik emas, chegara bilan solishtiriladi."""
    farq = abs(Decimal(str(a)) - Decimal(str(b)))
    return tekshir(soha, nom, farq <= Decimal(aniqlik),
                   f"{a} != {b} (farq {farq})")


# =====================================================================
#  HAQIQIY STSENARIYLAR — har soha uchun hayotdagidek qiymatlar
#
#  Bu yerdagi narxlar 2026 yil O'zbekiston bozoriga taxminan yaqin.
#  Aniq bo'lishi shart emas — muhimi REAL KATTALIK: 1 so'mlik un yoki
#  1 kg lik zakaz arifmetika xatosini yashirib yuboradi.
# =====================================================================

STSENARIYLAR = {
    "non": {
        "attrs": {"non_turi": "Patir", "ogirlik_g": 600, "un_navi": "oliy"},
        "miqdor": 2000,
        "ombor": [("Un", "kg", 6200, 6800), ("Tuz", "kg", 3500, 3800),
                  ("Xamirturush", "kg", 42000, 45000)],
    },
    "mebel": {
        "attrs": {"mahsulot": "Shkaf", "material": "LDSP", "en_mm": 1200,
                  "boy_mm": 2200, "chuqurlik_mm": 600, "rang": "Oq",
                  "furnitura": "Blum"},
        "miqdor": 12,
        "ombor": [("LDSP", "m²", 92000, 98000), ("Kromka lentasi", "metr", 3200, 3600),
                  ("Furnitura komplekti", "komplekt", 175000, 190000)],
    },
    "beton": {
        "attrs": {"marka": "M300", "hajm_m3": "1", "qoshimcha": "Plastifikator"},
        "miqdor": 45.5,
        "ombor": [("Sement", "kg", 1050, 1150), ("Qum", "m³", 170000, 185000),
                  ("Shag'al", "m³", 215000, 230000), ("Suv", "litr", 250, 300)],
    },
    "metall": {
        "attrs": {"mahsulot": "Darvoza", "metall": "Ст3", "qalinlik_mm": 4,
                  "en_mm": 3000, "boy_mm": 2200, "qoplama": "Kukun bo'yoq"},
        "miqdor": 3,
        "ombor": [("Ст3", "kg", 9200, 9800), ("Elektrod", "kg", 26000, 29000),
                  ("Bo'yoq", "kg", 52000, 58000)],
    },
    "kabel": {
        "attrs": {"marka": "ВВГ", "kesim_mm2": "4", "tomir": 3,
                  "izolyatsiya": "PVX", "uzunlik_m": 500},
        "miqdor": 500,
        "ombor": [("Mis", "kg", 95000, 102000), ("PVX izolyatsiya", "kg", 21000, 23000)],
    },
    "tikuvchilik": {
        "attrs": {"model": "Ish kombinezoni", "olcham": "L", "mato": "Gabardin",
                  "rang": "Ko'k", "logo": True},
        "miqdor": 300,
        "ombor": [("Mato", "metr", 28000, 31000), ("Ip", "dona", 12000, 13000),
                  ("Tugma", "dona", 400, 450)],
    },
    "kolbasa": {
        "attrs": {"mahsulot": "Kolbasa", "gosht_turi": "Mol", "ogirlik_g": 500,
                  "qobiq": "Tabiiy", "saqlash_kun": 20},
        "miqdor": 250.5,
        "ombor": [("Mol go'shti", "kg", 78000, 84000), ("Tuz", "kg", 3500, 3800),
                  ("Ziravor", "kg", 65000, 70000), ("Qobiq", "metr", 900, 1100)],
    },
    "plastik_deraza": {
        "attrs": {"mahsulot": "Deraza", "profil": "70 mm", "en_mm": 1500,
                  "boy_mm": 1400, "kamera": 5, "shisha_paket": "Uch qavat",
                  "moskitka": True},
        "miqdor": 24,
        "ombor": [("PVX profil 70 mm", "metr", 42000, 46000),
                  ("Shisha paket", "m²", 135000, 145000),
                  ("Furnitura komplekti", "komplekt", 175000, 190000),
                  ("Moskit to'r", "m²", 28000, 31000)],
    },
    "ulgurji_savdo": {
        "attrs": {"nomi": "Coca-Cola 1L", "artikul": "CC-1000", "brend": "Coca-Cola",
                  "birlik": "dona", "qadoq_soni": 12,
                  "ishlab_chiqaruvchi": "Coca-Cola Ichimlik Uzbekiston"},
        "miqdor": 1200,
        "ombor": [("Coca-Cola 1L", "dona", 9500, 10200)],
    },
    "poligrafiya": {
        "attrs": {"mahsulot": "Buklet", "format": "A4", "qogoz_zichligi": 170,
                  "ranglilik": "4+4", "laminatsiya": "Mat"},
        "miqdor": 5000,
        "ombor": [("Qog'oz", "kg", 14500, 15800), ("Bo'yoq", "kg", 165000, 178000)],
    },
    "gisht": {
        "attrs": {"mahsulot": "Pishgan g'isht", "marka": "M125",
                  "olcham_mm": "250x120x65", "rang": "Qizil", "sovuqbardosh": 50},
        "miqdor": 20000,
        "ombor": [("Gil", "kg", 210, 240), ("Qum", "m³", 170000, 185000)],
    },
    "sut": {
        "attrs": {"mahsulot": "Qatiq", "yoglilik": "3.2", "hajm_ml": 900,
                  "qadoq": "Plyonka", "saqlash_kun": 10},
        "miqdor": 3000,
        "ombor": [("Xom sut", "litr", 7800, 8400), ("Qadoq", "dona", 950, 1050)],
    },
    "kimyo": {
        "attrs": {"mahsulot": "Suyuq sovun", "hajm_ml": 500, "hid": "Lavanda",
                  "qadoq": "Butilka", "konsentrat": False},
        "miqdor": 4000,
        "ombor": [("Asosiy modda", "kg", 32000, 35000), ("Suv", "litr", 250, 300),
                  ("Qadoq", "dona", 950, 1050), ("Yorliq", "dona", 180, 210)],
    },
    "poyabzal": {
        # Retseptda «{material}» va «{tovon}» — atribut qiymati material
        # nomiga qo'yiladi. Shuning uchun omborda AYNAN shu nom turishi
        # kerak: «Tabiiy charm», «Tovon (Rezina)».
        "attrs": {"model": "Klassik tufli", "olcham": 42,
                  "material": "Tabiiy charm", "tovon": "Rezina", "rang": "Qora"},
        "miqdor": 200,
        "ombor": [("Tabiiy charm", "dm²", 9500, 10400),
                  ("Tovon (Rezina)", "juft", 32000, 36000),
                  ("Ip", "dona", 12000, 13000), ("Yelim", "kg", 48000, 53000)],
    },
    "yogoch_eshik": {
        "attrs": {"mahsulot": "Eshik", "en_mm": 900, "boy_mm": 2100,
                  "yogoch": "Qarag'ay", "qoplama": "Lak", "qulf": True},
        "miqdor": 15,
        "ombor": [("Qarag'ay", "m²", 320000, 345000), ("Lak", "kg", 68000, 74000),
                  ("Qulf", "dona", 145000, 160000)],
    },
    "montaj": {
        "attrs": {"ish_turi": "Pardozlash", "obyekt": "Turar-joy binosi",
                  "maydon_m2": "1", "material_bizdan": True, "muddat_kun": 45},
        "miqdor": 850,
        "ombor": [("Qurilish materiali", "m²", 42000, 46000)],
    },
    "chakana_dokon": {
        "attrs": {"nomi": "Yog' 1L", "kategoriya": "Oziq-ovqat",
                  "birlik": "dona", "shtrix_kod": "4780000000017"},
        "miqdor": 240,
        "ombor": [("Yog' 1L", "dona", 21000, 23500)],
    },
    "avto_servis": {
        "attrs": {"avto": "Chevrolet Cobalt", "davlat_raqam": "01A123BC",
                  "ish_turi": "Xodovoy", "probeg_km": 145000, "ehtiyot_qism": True},
        "miqdor": 1,
        "ombor": [("Ehtiyot qism", "komplekt", 850000, 920000)],
    },
    "texnika_tamiri": {
        "attrs": {"texnika": "Kir yuvish mashinasi", "brend": "Samsung",
                  "nosozlik": "Nasos ishlamayapti", "kafolat_oy": 6},
        "miqdor": 1,
        "ombor": [("Ehtiyot qism", "komplekt", 850000, 920000)],
    },
    # --- Materialsiz sohalar: xizmat. Retsept yo'q — ombor tekshiruvi
    #     o'tkazib yuboriladi, lekin pul va sikl baribir tekshiriladi.
    "logistika": {
        "attrs": {"yonalish": "Toshkent — Nukus", "transport": "Fura",
                  "ogirlik_kg": 18000, "masofa_km": 1250, "shoshilinch": False},
        "miqdor": 1,
        "ombor": [],
    },
    "reklama": {
        "attrs": {"xizmat": "Logotip", "murakkablik": "Murakkab",
                  "muddat_kun": 14, "tuzatish_soni": 3},
        "miqdor": 1,
        "ombor": [],
    },
    "karton": {
        "attrs": {"length_mm": 400, "width_mm": 300, "height_mm": 200,
                  "tur": "3 слой", "layers": 3, "grade": "K1", "colors": 2,
                  "is_offset": False},
        "miqdor": 5000,
        "ombor": [],
        "qogoz": [("K1", 140, 8200)],
    },
}


def profil_qiymatlari(joriy, tayyor_attrs):
    """Stsenariy bermagan maydonlarni profil ta'rifidan to'ldiradi."""
    q = dict(tayyor_attrs)
    for md in joriy["maydonlar"]:
        if md["hisoblanadi"] or md["kalit"] in q:
            continue
        if md.get("standart") is not None:
            q[md["kalit"]] = md["standart"]
        elif md.get("variantlar"):
            q[md["kalit"]] = md["variantlar"][0]
        elif md["tur"] == "butun":
            q[md["kalit"]] = md.get("min") or 1
        elif md["tur"] == "kasr":
            q[md["kalit"]] = str(md.get("min") or 1)
        elif md["tur"] == "mantiq":
            q[md["kalit"]] = False
        else:
            q[md["kalit"]] = "Sinov"
    return q


def sohani_sina(soha, st, token):
    s, _ = call("POST", "/api/soha/faollashtirish", {"kalit": soha}, token)
    if not tekshir(soha, "faollashtirish", s == 200):
        return
    s, joriy = call("GET", "/api/soha/joriy", token=token)

    # Karton hali eski `xomashyo` (RawLot) yo'lida — qog'oz boshqa
    # jadvalda, m² emas kg+grammaj bilan. Shu yo'l ham sinovsiz qolmasin.
    if st.get("qogoz"):
        s, sup = call("POST", "/api/warehouse/suppliers",
                      {"name": f"Sinov qog'oz · {soha}", "phone": "-",
                       "kind": "xomashyo"}, token)
        for marka, gramm, narx_kg in st["qogoz"]:
            s, d = call("POST", "/api/warehouse/raw",
                        {"grade": marka, "grammage": gramm, "qty_kg": 200_000,
                         "price_per_kg": narx_kg,
                         "supplier_id": sup.get("id")}, token)
            tekshir(soha, f"qog'oz kirim «{marka}»", s == 200, str(d)[:110])

    # --- 1. Ombor: har materialga IKKI partiya (FIFO sinash uchun) ------
    for nom, birlik, narx1, narx2 in st["ombor"]:
        for miqdor, narx in ((500_000, narx1), (500_000, narx2)):
            s, d = call("POST", "/api/warehouse/material-lot",
                        {"material": nom, "qty": miqdor, "price_per_unit": narx,
                         "unit": birlik}, token)
            tekshir(soha, f"ombor kirim «{nom}»", s == 200, str(d)[:110])

    s, ombor_oldin = call("GET", "/api/warehouse/materials", token=token)
    qoldiq_oldin = {x["name"]: x["stock_qty"] for x in ombor_oldin}

    # --- 2. Mijoz va buyurtma -----------------------------------------
    s, c = call("POST", "/api/clients",
                {"company": f"Chuqur sinov · {soha}", "phone": "901112233",
                 "category": "Standart"}, token)
    if not tekshir(soha, "mijoz", s == 200, str(c)[:110]):
        return

    attrs = profil_qiymatlari(joriy, st["attrs"])
    miqdor = st["miqdor"]

    # Smeta (agar profil formula bilan ishlasa) — narx qayerdan kelganini bilamiz
    s, smeta = call("POST", "/api/orders/smeta",
                    {"attributes": attrs, "qty": miqdor,
                     "client_id": c["id"]}, token)
    smeta_narx = smeta.get("unit_price") if s == 200 else None
    # Har profil ogohlantirishni O'Z nomi bilan qaytaradi. Faqat bittasini
    # qarab o'tirsam, karton «qog'oz narxi topilmadi» degani jimgina
    # yo'qoladi va past narx to'g'ridek ko'rinadi — birinchi yurishda
    # aynan shunday bo'ldi. Shuning uchun hammasi yig'iladi.
    if s == 200:
        for kalit in ("ogohlantirish", "narx_ogoh", "formula_ogoh"):
            qiymat = smeta.get(kalit)
            if not qiymat:
                continue
            matn = "; ".join(qiymat) if isinstance(qiymat, list) else str(qiymat)
            OGOHLAR.append(f"{soha} · {kalit}: {matn[:130]}")
    tannarx = smeta.get("unit_cost") if s == 200 else None

    tana = {"client_id": c["id"], "qty": miqdor, "attributes": attrs,
            "product_name": "Chuqur sinov"}
    if joriy["narx_usuli"] == "qolda":
        tana["unit_price"] = 50_000
    s, o = call("POST", "/api/orders", tana, token)
    if not tekshir(soha, "buyurtma", s == 200, str(o)[:180]):
        return

    # --- 3. Pul arifmetikasi ------------------------------------------
    # QQS «ustiga» rejimida: QQSsiz asos = narx × miqdor, jami = asos + QQS.
    # `total` — mijoz TO'LAYDIGAN summa, shuning uchun u narx × miqdordan
    # katta bo'lishi TO'G'RI. (Birinchi yozganimda shu chalkashib, tizimni
    # xato deb o'ylagandim — aslida test noto'g'ri edi.)
    asos = Decimal(str(o["unit_price"])) * Decimal(str(miqdor))
    teng(soha, "QQSsiz asos = narx × miqdor", o["qqssiz_summa"], asos, "1")
    teng(soha, "QQS = asos × 12%", o["qqs_summa"], asos * Decimal("0.12"), "1")
    teng(soha, "QQSsiz + QQS = jami",
         Decimal(str(o["qqssiz_summa"])) + Decimal(str(o["qqs_summa"])), o["total"])
    if smeta_narx:
        teng(soha, "smeta narxi = buyurtma narxi", smeta_narx, o["unit_price"], "1")
    if tannarx:
        # Sotuv narxi tannarxdan past bo'lsa — zarariga sotish. Formula
        # bo'lgan sohalarda bu bo'lmasligi kerak.
        tekshir(soha, "narx tannarxdan past emas",
                Decimal(str(o["unit_price"])) >= Decimal(str(tannarx)),
                f"narx {o['unit_price']} < tannarx {tannarx}")

    # --- 4. Retsept: nima ketishi kerak --------------------------------
    s, retsept = call("GET", f"/api/orders/{o['id']}/retsept", token=token)
    kutilgan = {}
    # Retsept endpointi 500 bergan payt test JIMGINA o'tib ketgan edi —
    # «0 material» chiqib turdi, lekin ✓ deb yozildi. Materialli soha
    # retseptsiz qolsa bu XATO, o'tkazib yuboriladigan hol emas.
    if st["ombor"]:
        tekshir(soha, "retsept olindi", s == 200, str(retsept)[:140])
        tekshir(soha, "retsept bor", bool(retsept.get("retsept_bor")),
                "profil retseptli, lekin endpoint bo'sh qaytardi")
    if s == 200 and retsept.get("retsept_bor"):
        tekshir(soha, "ombor yetadi", retsept["yetadi"],
                str([q for q in retsept["qatorlar"] if not q.get("yetadi")])[:140])
        for q in retsept["qatorlar"]:
            if q.get("kerak_material_birligida") is not None:
                kutilgan[q["material"]] = q["kerak_material_birligida"]

    if joriy["narx_usuli"] == "qolda" and s == 200 and retsept.get("retsept_bor"):
        xom = Decimal(str(retsept.get("xomashyo_summasi") or 0))
        zarar = xom > Decimal(str(o["qqssiz_summa"]))
        tekshir(soha, "zarariga sotish ogohlantirildi",
                (not zarar) or bool(retsept.get("zarar_ogoh")),
                f"xomashyo {xom:.0f} > narx {o['qqssiz_summa']:.0f}, ogoh yo'q")
        if zarar:
            OGOHLAR.append(f"{soha} · qo'lda narx xomashyodan past "
                           f"({o['qqssiz_summa']:.0f} < {xom:.0f}) — "
                           f"tizim to'g'ri ogohlantirdi")

    # --- 5. To'liq sikl (xomashyo shu yerda yechiladi) -----------------
    kart = {x["nom"]: x for x in joriy["statuslar"]}
    holat, yurildi = o["status"], [o["status"]]
    for _ in range(len(kart)):
        st_ = kart.get(holat)
        if not st_ or st_["mano"] == "topshirildi":
            break
        keyingi = [k for k in st_["keyingi"]
                   if kart.get(k, {}).get("mano") != "bekor" and k not in yurildi]
        if not keyingi:
            break
        tartib = {"muzokara": 0, "ishlab_chiqarish": 1, "tayyor": 2, "topshirildi": 3}
        keyingi.sort(key=lambda k: tartib.get(kart[k]["mano"], 0), reverse=True)
        maqsad = keyingi[0]
        s, d = call("POST", f"/api/orders/{o['id']}/status?status="
                    + urllib.parse.quote(maqsad), token=token)
        if not tekshir(soha, f"maqom → {maqsad}", s == 200, str(d)[:140]):
            break
        holat = maqsad
        yurildi.append(maqsad)
    tekshir(soha, "to'liq siklga yetdi",
            kart.get(holat, {}).get("mano") == "topshirildi", f"to'xtadi: {holat}")

    # --- 6. OMBOR HAQIQATAN KAMAYDIMI ---------------------------------
    s, ombor_keyin = call("GET", "/api/warehouse/materials", token=token)
    qoldiq_keyin = {x["name"]: x["stock_qty"] for x in ombor_keyin}
    for material, kerak in kutilgan.items():
        oldin = qoldiq_oldin.get(material)
        keyin = qoldiq_keyin.get(material)
        if oldin is None or keyin is None:
            tekshir(soha, f"ombor «{material}»", False, "material topilmadi")
            continue
        teng(soha, f"ombor kamayishi «{material}»", oldin - keyin, kerak, "0.01")

    # --- 7. To'lov va qarz --------------------------------------------
    yarim = round(o["total"] / 2, 2)
    s, p = call("POST", "/api/finance/payments",
                {"client_id": c["id"], "order_id": o["id"], "amount": yarim}, token)
    tekshir(soha, "to'lov yozildi", s == 200, str(p)[:110])
    s, d = call("GET", "/api/finance/debtors", token=token)
    if s == 200:
        meniki = [x for x in (d if isinstance(d, list) else d.get("debtors", []))
                  if x.get("company") == f"Chuqur sinov · {soha}"]
        if meniki:
            qarz = meniki[0].get("qarz") or meniki[0].get("debt") or 0
            teng(soha, "qarz = jami - to'lov", qarz, o["total"] - yarim, "1")

    # --- 8. Hujjatlar --------------------------------------------------
    for h in (f"/api/reports/act/{o['id']}.pdf",
              f"/api/reports/nakladnoy/{o['id']}.pdf",
              f"/api/reports/nakladnoy/{o['id']}.xlsx"):
        kod, hajm = bayt(h, token)
        tekshir(soha, h.rsplit("/", 1)[-1], kod == 200 and hajm > 1500,
                f"kod={kod} hajm={hajm}")

    print(f"  ✓ {soha:<16} {miqdor:>9} {joriy.get('maydonlar') and ''}"
          f"{o['total']:>16,.0f} so'm   {len(kutilgan)} material")


SINOV_PAROL = "Sinov2026Parol"


def kirish():
    """Token oladi. Yangi bazada admin standart parol bilan QULFLANGAN —
    sinov avval parolni almashtiradi, aks holda hamma so'rov 403 bo'ladi."""
    s, d = call("POST", "/api/auth/login", {"login": "admin", "password": "1234"})
    if s == 200 and d.get("parol_almashtirilsin"):
        call("POST", "/api/auth/change-password",
             {"old_password": "1234", "new_password": SINOV_PAROL}, d["token"])
        return d["token"]
    if s == 200:
        return d["token"]
    s, d = call("POST", "/api/auth/login",
                {"login": "admin", "password": SINOV_PAROL})
    if s != 200:
        print(f"❌ Login ({s}). Server {BASE} da ishlayaptimi?")
        raise SystemExit(1)
    return d["token"]


def main():
    token = kirish()

    # QQS yoqamiz — hayotdagi holat, va arifmetikani qiyinlashtiradi
    call("POST", "/api/finance/settings",
         {"values": {"qqs_rejimi": "ustiga", "qqs_stavka": "12"}}, token)

    print(f"{'SOHA':<18} {'MIQDOR':>9} {'JAMI':>18}   MATERIAL")
    print("-" * 62)
    for soha, st in STSENARIYLAR.items():
        sohani_sina(soha, st, token)

    print()
    if OGOHLAR:
        print(f"⚠️  {len(OGOHLAR)} ogohlantirish:")
        for o in OGOHLAR:
            print("   ·", o)
        print()
    if XATOLAR:
        print(f"❌ {len(XATOLAR)} XATO:")
        for x in XATOLAR:
            print("   ·", x)
        raise SystemExit(1)
    print(f"✅ {len(STSENARIYLAR)} SOHA — HISOB-KITOB TO'G'RI")


if __name__ == "__main__":
    main()
