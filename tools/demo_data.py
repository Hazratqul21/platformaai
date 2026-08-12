"""DEMO MA'LUMOT GENERATORI — har soha uchun to'liq, ishlaydigan baza.

NEGA KERAK: bo'sh tizimda hamma narsa chiroyli ko'rinadi. Muammolar
ma'lumot to'planganda chiqadi — qarz yoshi, FIFO, kechikkan buyurtma,
qisman topshirish, minusga ketgan ombor. Prodga chiqishdan oldin har
sohani AYNAN shunday holatda ko'rish kerak.

ASOSIY G'OYA — materiallar RETSEPTDAN olinadi:
    Har profilda `retsept` bor: qaysi material, qaysi birlikda. Generator
    shu ro'yxatni o'qib ombor kartochkalarini yasaydi. Demak yangi soha
    qo'shilganda (yoki AI agent profil yaratganda) generatorga TEGILMAYDI —
    u yangi sohani ham to'ldiraveradi.

Narxlar `NARX_TAXMINI` dan olinadi; ro'yxatda yo'q material birligiga
qarab taxminlanadi (kg arzon, komplekt qimmat). Aniq bo'lishi shart emas,
muhimi — KATTALIK haqiqiyga yaqin bo'lsin, aks holda arifmetika xatosi
ko'rinmay qoladi.

Ishlatish:
    .venv/bin/python tools/demo_data.py --soha non
    .venv/bin/python tools/demo_data.py --hammasi      # 22 soha ketma-ket
    .venv/bin/python tools/demo_data.py --soha beton --mijoz 12 --buyurtma 40
"""
import argparse
import random
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal                      # noqa: E402
from app import models as m, domain, services as s   # noqa: E402

RNG = random.Random(20260807)     # takrorlanadigan natija — xato qidirish oson

# --- Mijoz nomlari: haqiqiyga o'xshasin, lekin haqiqiy korxona bo'lmasin ---
BOSH = ["Oq", "Zar", "Yangi", "Baraka", "Nur", "Sifat", "Ishonch", "Global",
        "Milliy", "Sharq", "Vodiy", "Marvarid", "Chinor", "Umid", "Poytaxt"]
OXIR = ["Savdo", "Invest", "Group", "Trade", "Servis", "Bizness", "Logistik",
        "Impeks", "Prom", "Tex"]
SHAKL = ["MChJ", "XK", "OK", "QK"]
ISM = ["Aziz", "Bobur", "Dilshod", "Eldor", "Farrux", "G'ayrat", "Hasan",
       "Iqbol", "Jasur", "Kamol", "Laziz", "Murod", "Nodir", "Otabek",
       "Rustam", "Sardor", "Temur", "Ulug'bek", "Vohid", "Zafar"]
FAMILIYA_HARF = ["A.", "B.", "D.", "E.", "F.", "G.", "H.", "I.", "K.", "M.",
                 "N.", "O.", "R.", "S.", "T.", "U."]

# --- Material narxi taxmini (2026, so'm). Nomga qarab topiladi ---
NARX_TAXMINI = {
    "un": 6500, "tuz": 3600, "xamirturush": 43000, "sement": 1100,
    "qum": 178000, "shag'al": 222000, "suv": 270, "gil": 225,
    "mis": 98000, "mato": 29500, "ip": 12500, "tugma": 420,
    "ldsp": 95000, "kromka": 3400, "furnitura": 182000,
    "qog'oz": 15000, "bo'yoq": 55000, "elektrod": 27500,
    "xom sut": 8100, "qadoq": 1000, "yorliq": 195, "asosiy modda": 33500,
    "mol go'shti": 81000, "ziravor": 67500, "qobiq": 1000,
    "shisha paket": 140000, "moskit to'r": 29500, "pvx": 22000,
    "ehtiyot qism": 885000, "qurilish materiali": 44000,
    "tabiiy charm": 9900, "tovon": 34000, "yelim": 50000,
    "qarag'ay": 332000, "lak": 71000, "qulf": 152000,
}
# Nomdan topilmasa — BIRLIKKA qarab. Bir kg xomashyo bilan bir komplekt
# ehtiyot qism narxi ming marta farq qiladi, shuni hisobga olmasak
# demo ma'lumot bema'ni chiqadi.
BIRLIK_NARXI = {
    "kg": 25_000, "litr": 8_000, "metr": 20_000, "m²": 90_000,
    "m³": 200_000, "dona": 5_000, "komplekt": 250_000, "juft": 35_000,
    "dm²": 9_000, "ish": 500_000, "soat": 80_000,
}


def material_narxi(nom: str, birlik: str) -> int:
    past = (nom or "").lower()
    for kalit, narx in NARX_TAXMINI.items():
        if kalit in past:
            return narx
    return BIRLIK_NARXI.get(birlik, 30_000)


def firma_nomi() -> str:
    return f"«{RNG.choice(BOSH)}{RNG.choice(OXIR)}» {RNG.choice(SHAKL)}"


def odam_nomi() -> str:
    return f"{RNG.choice(ISM)} {RNG.choice(FAMILIYA_HARF)}"


def telefon() -> str:
    return f"9{RNG.choice('01345789')}{RNG.randint(1000000, 9999999)}"


# =====================================================================
#  Profil maydonlarini to'ldirish
# =====================================================================

def maydon_qiymati(md):
    """Bitta maydonga ishonchli tasodifiy qiymat.

    Chegaralar (`min`/`max`) hurmat qilinadi — aks holda generator o'zi
    validatsiyaga tushib qoladi va demo yasalmaydi.
    """
    if md.variantlar:
        return RNG.choice(md.variantlar)
    if md.tur == "mantiq":
        return RNG.random() < 0.5
    if md.tur in ("butun", "kasr"):
        past = float(md.min) if md.min is not None else 1
        yuqori = float(md.max) if md.max is not None else max(past * 20, 100)
        # Chegara berilmagan maydonlar uchun BIRLIKKA qarab aqlli oraliq.
        # Busiz 177×3852×1814 mm «quti» chiqib qolardi — tizim uni qabul
        # qiladi, lekin demo ma'lumot ishonchsiz ko'rinadi va haqiqiy
        # xatoni ham yashiradi.
        oraliq = {"mm": (150, 1200), "g": (100, 2000), "ml": (250, 2000),
                  "kun": (3, 45), "km": (5, 1500), "soat": (1, 40)}
        if md.min is None and md.max is None and md.birlik in oraliq:
            past, yuqori = oraliq[md.birlik]
        if md.standart is not None:
            # Standart bor — undan uncha uzoqlashmaymiz, shunda o'lchamlar
            # hayotdagidek bo'ladi (900 mm eshik, 2100 mm bo'y).
            asos = float(md.standart)
            past = max(past, asos * 0.7)
            yuqori = min(yuqori, asos * 1.4) if yuqori > asos else yuqori
            if past > yuqori:
                past, yuqori = yuqori, past
        # PASTGA MOYIL taqsimot. Tekis tanlansa keng oraliqda («en_mm»
        # 100..20000 — katta metall konstruksiya uchun to'g'ri chegara)
        # o'rtacha 10 metrlik darvoza chiqadi. Hayotda esa mahsulotlar
        # oraliqning quyi qismida to'planadi, kattasi kam uchraydi.
        # `triangular(past, yuqori, past)` — cho'qqisi pastda.
        qiymat = RNG.triangular(past, yuqori, past)
        return int(round(qiymat)) if md.tur == "butun" else f"{qiymat:.2f}"
    if md.standart:
        return md.standart
    return f"{md.nom} namunasi"


def buyurtma_atributlari(p) -> dict:
    qiymatlar = {md.kalit: maydon_qiymati(md)
                 for md in p.maydonlar if not md.hisoblanadi}
    tayyor, xato = domain.tayyorla(qiymatlar)
    if xato:
        # Chegaralarga tushmasa standartlarga qaytamiz — demo baribir yasalsin
        qiymatlar = {md.kalit: (md.standart if md.standart is not None
                                else (md.variantlar[0] if md.variantlar else 1))
                     for md in p.maydonlar if not md.hisoblanadi}
        tayyor, xato = domain.tayyorla(qiymatlar)
        if xato:
            raise ValueError(f"maydonlarni to'ldirib bo'lmadi: {xato}")
    return tayyor


def miqdor_tanla(p) -> Decimal:
    """Sohaga mos miqdor: m³ da 45.5, dona da 5000."""
    past = float(p.min_miqdor)
    if p.birlik in ("m³", "ish", "komplekt", "juft"):
        xom = RNG.uniform(max(past, 1), 60)
    elif p.birlik in ("m²", "metr", "kg", "litr"):
        xom = RNG.uniform(max(past, 10), 900)
    else:
        xom = RNG.uniform(max(past, 100), 8000)
    xom = min(xom, float(p.max_miqdor))
    return Decimal(f"{xom:.2f}") if p.kasrli else Decimal(str(int(xom)))


# =====================================================================
#  Generator
# =====================================================================

def soha_toldir(db, kalit: str, mijoz_soni: int, buyurtma_soni: int) -> dict:
    profil_yozuvi = db.query(m.SohaProfil).filter(
        m.SohaProfil.kalit == kalit).first()
    if not profil_yozuvi:
        raise SystemExit(f"❌ '{kalit}' profili topilmadi")
    for x in db.query(m.SohaProfil).all():
        x.faol = (x.id == profil_yozuvi.id)
    db.commit()
    domain.qayta_yukla(db)
    p = domain.profil()

    hisob = {"soha": p.nom, "mijozlar": 0, "materiallar": 0,
             "buyurtmalar": 0, "tolovlar": 0, "xaridlar": 0, "kassa": 0,
             "ish_yozuvi": 0, "sex_xarajati": 0}

    # ---- 1. Ombor: materiallar RETSEPTDAN --------------------------
    kerakli = {}
    for qator in (p.retsept or []):
        nom = str(qator.get("material", "")).strip()
        # «{material}» kabi shablon — atribut qiymati qo'yiladi. Namuna
        # atributlardan bittasini olib, haqiqiy nomni chiqaramiz.
        if "{" in nom:
            namuna = buyurtma_atributlari(p)
            try:
                nom = nom.format(**namuna)
            except (KeyError, IndexError):
                continue
        if nom:
            kerakli[nom] = qator.get("birlik", "dona")

    yb = db.query(m.Supplier).filter(m.Supplier.kind == "xomashyo").first()
    if yb is None:
        yb = m.Supplier(name=firma_nomi(), phone=telefon(), kind="xomashyo")
        db.add(yb)
        db.flush()

    for nom, birlik in kerakli.items():
        mat = s.material_top(db, nom)
        if mat is None:
            mat = m.Material(name=nom, unit=birlik, active=True,
                             min_stock=Decimal("50"))
            db.add(mat)
            db.flush()
            hisob["materiallar"] += 1
        asos = material_narxi(nom, birlik)
        # UCH partiya, narxi o'sib boradi — FIFO shu bilan ko'rinadi
        for nechanchi in range(3):
            narx = Decimal(str(int(asos * (1 + nechanchi * 0.06))))
            miqdor = Decimal(str(RNG.randint(20_000, 90_000)))
            db.add(m.MaterialLot(
                material_id=mat.id, qty=miqdor, remaining=miqdor,
                price_per_unit=narx, supplier_id=yb.id,
                received_at=date.today() - timedelta(days=60 - nechanchi * 20)))
            mat.stock_qty = Decimal(str(mat.stock_qty or 0)) + miqdor
            mat.last_price = narx
    db.commit()

    # ---- 2. Mijozlar ------------------------------------------------
    toifalar = ["VIP"] * 2 + ["Standart"] * 6 + ["Yangi"] * 2
    mijozlar = []
    for _ in range(mijoz_soni):
        c = m.Client(
            company=firma_nomi(), contact=odam_nomi(), phone=telefon(),
            inn=str(RNG.randint(200000000, 399999999)),
            pay_type=RNG.choice(["Naqd", "Pere4isleniya"]),
            category=RNG.choice(toifalar),
            credit_limit=Decimal(str(RNG.choice([30, 50, 100, 200]) * 1_000_000)),
            blacklisted=False,
            # Ba'zi mijozda tizimdan oldingi qarz bo'ladi — hayotda shunday
            opening_balance=(Decimal(str(RNG.randint(1, 40) * 100_000))
                             if RNG.random() < 0.25 else Decimal("0")),
            opening_date=date.today() - timedelta(days=180),
        )
        db.add(c)
        mijozlar.append(c)
    db.flush()
    hisob["mijozlar"] = len(mijozlar)

    # ---- 3. Buyurtmalar: har bosqichda, har xil sanada ---------------
    kart = {st.nom: st for st in p.modul.statuslar}
    boshlanish = next((st.nom for st in p.modul.statuslar
                       if st.mano == "boshlanish"), None)
    yakun = [st.nom for st in p.modul.statuslar if st.mano == "topshirildi"]
    orta = [st.nom for st in p.modul.statuslar
            if st.mano in ("muzokara", "ishlab_chiqarish", "tayyor")]

    for nechanchi in range(buyurtma_soni):
        c = RNG.choice(mijozlar)
        atr = buyurtma_atributlari(p)
        miqdor = miqdor_tanla(p)
        # Sanalar 150 kunga yoyiladi — qarz yoshi (0-15/15-30/30-60/60+)
        # jadvali shundagina to'ldiriladi.
        kun_oldin = RNG.randint(0, 150)
        yaratilgan = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=kun_oldin)

        narx_hisobi = _narx(db, p, atr, miqdor, c.category)
        if narx_hisobi is None:
            continue
        tannarx, narx = narx_hisobi

        # MIQDORNI QIYMATGA QARAB KAMAYTIRAMIZ. Katta mahsulotdan ko'p
        # buyurtma qilinmaydi: 20 m² darvozadan 2500 dona — trillion
        # so'mlik zakaz bo'ladi va butun hisobot ma'nosini yo'qotadi.
        # Chegara kichik-o'rta korxona uchun realistik: ~300 mln so'm.
        CHEGARA = Decimal("300000000")
        if narx > 0 and narx * miqdor > CHEGARA:
            miqdor = max(Decimal("1"), (CHEGARA / narx))
            miqdor = (miqdor.quantize(Decimal("0.01")) if p.kasrli
                      else Decimal(str(max(1, int(miqdor)))))
            narx_hisobi = _narx(db, p, atr, miqdor, c.category)
            if narx_hisobi is None:
                continue
            tannarx, narx = narx_hisobi
        qqs = s.qqs_hisobla(db, narx * miqdor)

        # Eski buyurtmalar ko'proq yakunlangan, yangilari yo'lda —
        # shunda ro'yxat hayotdagidek ko'rinadi.
        if kun_oldin > 60:
            holat = RNG.choice(yakun or [boshlanish])
        elif kun_oldin > 20:
            holat = RNG.choice((yakun or []) + orta) if (yakun or orta) else boshlanish
        else:
            holat = RNG.choice(([boshlanish] if boshlanish else []) + orta) \
                    if orta else boshlanish

        topshirilgan = Decimal("0")
        if domain.manosi(holat) == "topshirildi":
            # Ba'zilari QISMAN topshirilgan — qarz hisobining eng nozik joyi
            topshirilgan = (miqdor if RNG.random() < 0.75
                            else (miqdor * Decimal("0.6")).quantize(Decimal("0.001")))

        o = m.Order(
            client_id=c.id, attributes=atr, qty=miqdor,
            delivered_qty=topshirilgan,
            product_name=domain.tarkib_matni(_Soxta(atr, miqdor))[:100] or p.nom,
            unit_cost=tannarx, unit_price=narx,
            qqs_stavka=qqs["stavka"], qqs_summa=qqs["qqs"], total=qqs["jami"],
            prepaid_percent=RNG.choice([0, 30, 50]), status=holat,
            note=RNG.choice(["", "", "", "Shoshilinch", "Mijoz o'zi oladi"]),
            created_at=yaratilgan,
            due_date=(yaratilgan + timedelta(days=15)).date(),
            payment_due_date=(yaratilgan + timedelta(days=RNG.choice([10, 15, 30]))).date(),
            delivered_at=(yaratilgan + timedelta(days=RNG.randint(3, 12))).date()
            if topshirilgan > 0 else None,
            accepted_stamp=topshirilgan > 0 and RNG.random() < 0.5,
        )
        db.add(o)
        db.flush()
        hisob["buyurtmalar"] += 1

        # ---- 4. To'lovlar: to'liq / qisman / umuman yo'q -------------
        if topshirilgan > 0:
            qiymat = (Decimal(str(o.total)) * topshirilgan / miqdor)
            tanlov = RNG.random()
            if tanlov < 0.45:
                summa = qiymat                                  # to'liq
            elif tanlov < 0.80:
                summa = (qiymat * Decimal(str(RNG.uniform(0.3, 0.8)))
                         ).quantize(Decimal("0.01"))            # qisman
            else:
                summa = Decimal("0")                            # qarzga
            if summa > 0:
                db.add(m.Payment(
                    client_id=c.id, order_id=o.id, amount=summa,
                    method=RNG.choice(["Naqd", "Karta", "O'tkazma"]),
                    paid_at=(yaratilgan + timedelta(days=RNG.randint(1, 20))).date(),
                    note=""))
                hisob["tolovlar"] += 1
    db.commit()

    # ---- 4b. Xaridlar ------------------------------------------------
    # Busiz «bizning qarzimiz» va pul oqimidagi chiqim NOL bo'lib qoladi,
    # ya'ni moliya paneli yarim bo'sh ko'rinadi.
    materiallar = db.query(m.Material).filter(m.Material.active.is_(True)).all()
    if materiallar:
        for _ in range(RNG.randint(8, 16)):
            mat = RNG.choice(materiallar)
            miqdor_x = Decimal(str(RNG.randint(50, 800)))
            narx_x = Decimal(str(mat.last_price or 10000))
            jami_x = (miqdor_x * narx_x).quantize(Decimal("0.01"))
            # Bir qismi to'langan, bir qismi qarz — hayotdagidek
            ulush = RNG.choice([Decimal("1"), Decimal("0.5"), Decimal("0")])
            db.add(m.Purchase(
                material_id=mat.id, supplier_id=yb.id,
                qty=miqdor_x, unit=mat.unit,
                unit_price=narx_x, total=jami_x,
                payment_type=RNG.choice(["Naqd", "O'tkazma"]),
                paid_amount=(jami_x * ulush).quantize(Decimal("0.01")),
                purchased_at=date.today() - timedelta(days=RNG.randint(0, 140)),
                # Qarzga olingan xaridga to'lov muddati — pul oqimi
                # prognozida chiqim shundan hisoblanadi
                due_date=(date.today() + timedelta(days=RNG.randint(-20, 45))
                          if ulush < 1 else None),
                note="demo xarid"))
            hisob["xaridlar"] = hisob.get("xaridlar", 0) + 1
        db.commit()

    # ---- 5. Kassa jurnali -------------------------------------------
    for _ in range(40):
        kun = RNG.randint(0, 150)
        kirimmi = RNG.random() < 0.45
        db.add(m.KassaEntry(
            firm="Asosiy",
            direction="Kirim" if kirimmi else "Chiqim",
            who=odam_nomi() if not kirimmi else firma_nomi(),
            note=RNG.choice(["Ish haqi", "Yoqilg'i", "Ijara", "Kommunal",
                             "Mijoz to'lovi", "Xomashyo", "Transport"]),
            amount=Decimal(str(RNG.randint(2, 90) * 100_000)),
            currency="so'm",
            entry_at=date.today() - timedelta(days=kun),
            created_by="demo"))
        hisob["kassa"] += 1

    # ---- 6. Xodimlar -------------------------------------------------
    if db.query(m.Employee).count() < 5:
        for _ in range(RNG.randint(6, 12)):
            db.add(m.Employee(
                name=odam_nomi(), position=RNG.choice(
                    ["Stanokchi", "Usta", "Yordamchi", "Sex boshlig'i"]),
                phone=telefon(),
                rate_per_box=Decimal(str(RNG.randint(80, 400))),
                brigade=RNG.choice(["A", "B", ""]), active=True))
        db.commit()

    # ---- 7. Sex ishi va xarajatlari ----------------------------------
    # Busiz «Цех харажатлари» va «Ходимлар» bo'limlari deyarli bo'sh
    # qolardi: oylik hisobi, sdelshina va podotchyot ko'rinmasdi.
    xodimlar = db.query(m.Employee).filter(m.Employee.active.is_(True)).all()
    tayyor_buyurtmalar = [
        o for o in db.query(m.Order)
                     .filter(m.Order.delivered_qty > 0).limit(60).all()]
    if xodimlar:
        # Sdelshina: ishlab chiqarilgan mahsulot bo'yicha ish haqi.
        # Ba'zi yozuv QC dan o'tmagan — bonus/jarima mantiqi ko'rinsin.
        for _ in range(RNG.randint(25, 45)):
            xodim = RNG.choice(xodimlar)
            buyurtma = RNG.choice(tayyor_buyurtmalar) if tayyor_buyurtmalar else None
            miqdor = RNG.randint(50, 1500)
            stavka = Decimal(str(xodim.rate_per_box or 150))
            qc = RNG.random() > 0.12
            db.add(m.WorkEntry(
                employee_id=xodim.id,
                order_id=buyurtma.id if buyurtma else None,
                qty=miqdor, qc_passed=qc, rate=stavka,
                # QC dan o'tmagan ish HAQ TO'LANMAYDI — shuning uchun 0.
                # Tizimdagi qoida shunday, demo ham unga mos bo'lsin.
                amount=(stavka * miqdor) if qc else Decimal("0"),
                worked_at=date.today() - timedelta(days=RNG.randint(0, 120))))
            hisob["ish_yozuvi"] = hisob.get("ish_yozuvi", 0) + 1

        # Podotchyot: avans va mayda xarajatlar
        for _ in range(RNG.randint(10, 20)):
            xodim = RNG.choice(xodimlar)
            tur = RNG.choice(["Avans", "Xarajat", "Xarajat"])
            db.add(m.CashEntry(
                employee_id=xodim.id, kind=tur,
                amount=Decimal(str(RNG.randint(2, 40) * 50_000)),
                note=(RNG.choice(["Oylik avansi", "Bayram avansi"])
                      if tur == "Avans" else
                      RNG.choice(["Yo'lkira", "Tushlik", "Instrument",
                                  "Ta'mirlash", "Yoqilg'i", "Kanselyariya"])),
                entry_at=date.today() - timedelta(days=RNG.randint(0, 120))))
            hisob["sex_xarajati"] = hisob.get("sex_xarajati", 0) + 1

    db.add(m.AuditLog(who="Demo generator", action="Demo ma'lumot yasaldi",
                      detail=f"{kalit}: " + ", ".join(
                          f"{k}={v}" for k, v in hisob.items() if k != "soha")))
    db.commit()
    return hisob


class _Soxta:
    """Retsept/matn funksiyalari uchun yengil «buyurtmaga o'xshash» obyekt."""

    def __init__(self, attributes, qty):
        self.attributes = attributes
        self.qty = qty
        self.id = None


def _narx(db, p, atr, miqdor, toifa):
    """Profil usuliga qarab tannarx va narx. Hisoblanmasa — None."""
    usul = p.narx.get("usul", "qolda")
    if usul == "retsept":
        from app.routers.orders import retsept_narxi
        try:
            h = retsept_narxi(db, atr, miqdor, toifa)
            return h["unit_cost"], h["unit_price"]
        except Exception:                                    # noqa: BLE001
            return None
    if usul == "karton_formula":
        try:
            q = s.quote(db, atr["length_mm"], atr["width_mm"], atr["height_mm"],
                        atr.get("layers", 3), atr.get("grade", "K1"),
                        atr.get("colors", 0), float(miqdor), toifa)
            return q["unit_cost"], q["unit_price"]
        except Exception:                                    # noqa: BLE001
            return None
    # Qo'lda narxli soha (xizmat, chakana savdo, ta'mir). Tannarx nolga
    # qoldiriladi — hayotda ham bunday sohada tannarx tizimda yo'q.
    #
    # DIQQAT: narx MIQDORDAN kelib chiqadi. Avval «bitta ish narxi»
    # tanlanardi va u miqdorga ko'paytirilardi — natijada 1200 ta kir
    # yuvish mashinasini 1.5 mln dan ta'mirlash, ya'ni 2 mlrd so'mlik
    # zakaz chiqardi. To'g'risi: avval BUTUN ish qiymati tanlanadi,
    # birlik narxi undan bo'linadi.
    jami = Decimal(str(RNG.randint(300_000, 30_000_000)))
    narx = (jami / (Decimal(str(miqdor)) or Decimal("1")))
    narx = max(Decimal("100"), narx.quantize(Decimal("1")))
    return Decimal("0"), narx


def main():
    ap = argparse.ArgumentParser(description="Demo ma'lumot generatori")
    ap.add_argument("--soha", help="Profil kaliti, masalan 'non'")
    ap.add_argument("--hammasi", action="store_true", help="Hamma profil")
    ap.add_argument("--mijoz", type=int, default=10)
    ap.add_argument("--buyurtma", type=int, default=25)
    a = ap.parse_args()

    db = SessionLocal()
    try:
        if a.hammasi:
            kalitlar = [p.kalit for p in
                        db.query(m.SohaProfil).order_by(m.SohaProfil.id).all()]
        elif a.soha:
            kalitlar = [a.soha]
        else:
            ap.error("--soha yoki --hammasi kerak")

        print(f"{'SOHA':<18} {'MIJOZ':>6} {'BUYURTMA':>9} {'TO`LOV':>7} "
              f"{'XARID':>6} {'ISH':>5} {'XARAJAT':>8} {'MATERIAL':>9}")
        print("-" * 78)
        for kalit in kalitlar:
            try:
                h = soha_toldir(db, kalit, a.mijoz, a.buyurtma)
                print(f"{kalit:<18} {h['mijozlar']:>6} {h['buyurtmalar']:>9} "
                      f"{h['tolovlar']:>7} {h['xaridlar']:>6} "
                      f"{h['ish_yozuvi']:>5} {h['sex_xarajati']:>8} "
                      f"{h['materiallar']:>9}")
            except Exception as e:                            # noqa: BLE001
                db.rollback()
                print(f"{kalit:<18} ❌ {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
