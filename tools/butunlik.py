"""BUTUNLIK TEKSHIRUVI — bazadagi raqamlar o'zaro mos keladimi.

Bu vosita ISTALGAN bazada ishlaydi: demo, sinov yoki jonli prod. Hech
narsa yozmaydi, faqat o'qiydi va nomuvofiqlikni sanaydi.

Nima uchun alohida vosita: testlar YANGI yaratilgan ma'lumotni
tekshiradi, bu esa TO'PLANGAN ma'lumotni. Yillar davomida qo'lda
tuzatishlar, bekor qilingan buyurtmalar va o'chirilgan to'lovlar
yig'ilib, hech bir test ushlamaydigan nomuvofiqlik paydo bo'ladi.

Prodda oyiga bir marta yurgizib turish tavsiya qilinadi:
    .venv/bin/python tools/butunlik.py
"""
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal                      # noqa: E402
from app import models as m, domain, services as s   # noqa: E402

TIYIN = Decimal("1")     # 1 so'm chegara — yaxlitlash farqi kechiriladi


class Natija:
    def __init__(self):
        self.xato, self.ogoh, self.tekshiruv = [], [], 0

    def tekshir(self, nom, shart, izoh="", ogohmi=False):
        self.tekshiruv += 1
        if shart:
            return True
        (self.ogoh if ogohmi else self.xato).append(f"{nom} — {izoh}")
        return False


def tekshir_hammasi(db) -> Natija:
    n = Natija()

    # ---- 1. Buyurtma: jami = QQSsiz + QQS --------------------------
    buzuq = []
    for o in db.query(m.Order).all():
        jami = Decimal(str(o.total))
        qqs = Decimal(str(o.qqs_summa or 0))
        narx_miqdor = Decimal(str(o.unit_price)) * Decimal(str(o.qty))
        # QQS rejimiga qarab: «ustiga» da jami = narx×miqdor + QQS,
        # «ichida» da jami = narx×miqdor. Ikkalasida ham jami − QQS
        # QQSsiz asosga teng bo'lishi shart.
        if abs((jami - qqs) - narx_miqdor) > TIYIN and abs(jami - narx_miqdor) > TIYIN:
            buzuq.append(f"#{o.id}: jami={jami} qqs={qqs} narx×miqdor={narx_miqdor}")
    n.tekshir("buyurtma summasi (jami = QQSsiz + QQS)", not buzuq,
              f"{len(buzuq)} ta: " + "; ".join(buzuq[:3]))

    # ---- 2. Topshirilgan miqdor buyurtmadan oshmasin ----------------
    oshgan = [f"#{o.id}: {o.delivered_qty}/{o.qty}"
              for o in db.query(m.Order).all()
              if Decimal(str(o.delivered_qty or 0)) > Decimal(str(o.qty)) + Decimal("0.001")]
    n.tekshir("topshirilgan ≤ buyurtma miqdori", not oshgan,
              f"{len(oshgan)} ta: " + "; ".join(oshgan[:3]))

    # ---- 3. Ombor qoldig'i manfiy emasmi ---------------------------
    manfiy = [f"{mt.name}: {mt.stock_qty}" for mt in db.query(m.Material).all()
              if Decimal(str(mt.stock_qty or 0)) < 0]
    # Manfiy qoldiq XATO emas, OGOHLANTIRISH: xomashyo yetmasa ham
    # ishlab chiqarishga ruxsat berilgan (rahbar qaroriga qoldirilgan).
    n.tekshir("ombor qoldig'i manfiy emas", not manfiy,
              f"{len(manfiy)} ta: " + "; ".join(manfiy[:5]), ogohmi=True)

    # ---- 4. Partiyalar yig'indisi = material qoldig'i ---------------
    lot_yigindi = defaultdict(Decimal)
    for lot in db.query(m.MaterialLot).all():
        lot_yigindi[lot.material_id] += Decimal(str(lot.remaining or 0))
    farqli = []
    for mt in db.query(m.Material).all():
        qoldiq = Decimal(str(mt.stock_qty or 0))
        partiyalar = lot_yigindi.get(mt.id, Decimal("0"))
        # Faqat partiyali materiallar tekshiriladi: qo'lda kiritilgan
        # qoldiq (partiyasiz) bu qoidaga bo'ysunmaydi.
        if partiyalar > 0 and abs(qoldiq - partiyalar) > Decimal("0.01"):
            farqli.append(f"{mt.name}: kartochka={qoldiq} partiyalar={partiyalar}")
    n.tekshir("partiyalar yig'indisi = ombor qoldig'i", not farqli,
              f"{len(farqli)} ta: " + "; ".join(farqli[:3]))

    # ---- 5. Mijoz qarzi ikki xil yo'l bilan bir xilmi ---------------
    # `client_balance` (bitta mijoz) va `client_balances_batch` (hammasi)
    # alohida yozilgan — biri o'zgarib, ikkinchisi qolib ketishi mumkin.
    ommaviy = s.client_balances_batch(db)
    farqlar = []
    for c in db.query(m.Client).limit(200).all():
        bitta = s.client_balance(db, c.id)
        toplam = ommaviy.get(c.id)
        if toplam is None:
            continue
        if abs(bitta["debt"] - toplam["debt"]) > TIYIN:
            farqlar.append(f"{c.company}: {bitta['debt']} vs {toplam['debt']}")
    n.tekshir("qarz hisobi ikki yo'lda bir xil", not farqlar,
              f"{len(farqlar)} ta: " + "; ".join(farqlar[:3]))

    # ---- 5b. Qarz yoshi bo'laklari «jami qarz» ga to'g'ri keladimi ---
    # Bu ikkisi alohida hisoblanadi va bir marta ajralib ketgan edi:
    # bo'laklar buyurtma `total` idan, jami esa topshirilgan ulushdan.
    # Natijada moliya jadvali o'z-o'ziga zid ko'rinardi.
    nomos = []
    for q in s.debt_aging(db):
        bolaklar = sum(Decimal(str(v)) for v in q["aging"].values())
        jami = Decimal(str(q["debt"]))
        if abs(bolaklar - jami) > Decimal("1"):
            nomos.append(f"{q['company']}: jami={jami:.0f} bo'laklar={bolaklar:.0f}")
    n.tekshir("qarz yoshi bo'laklari = jami qarz", not nomos,
              f"{len(nomos)} ta: " + "; ".join(nomos[:3]))

    # ---- 5c. Pul oqimi prognozi qarzdan oshmasin --------------------
    jami_qarz = sum(Decimal(str(x["debt"])) for x in s.debt_aging(db))
    oqim = s.cash_flow_forecast(db, 365)
    n.tekshir("kutilayotgan kirim ≤ jami qarz",
              Decimal(str(oqim["expected_in"])) <= jami_qarz + Decimal("1"),
              f"kirim={oqim['expected_in']:.0f} qarz={jami_qarz:.0f}")

    # ---- 5d. Sdelshina: QC dan o'tmagan ishga haq yozilmasin --------
    # Tizim qoidasi: QC dan o'tmagan mahsulot uchun ish haqi to'lanmaydi.
    # Agar summa yozilib qolsa — oylik oshib ketadi va buni faqat xodim
    # sezadi.
    yomon = [f"#{w.id}" for w in db.query(m.WorkEntry).all()
             if not w.qc_passed and Decimal(str(w.amount or 0)) > 0]
    n.tekshir("QC dan o'tmagan ishga haq yozilmagan", not yomon,
              f"{len(yomon)} ta: " + ", ".join(yomon[:5]))

    # Ish haqi = miqdor × stavka — FAQAT sdelshina (qty>0) uchun.
    # qty=0 bo'lsa bu OKLAD (belgilangan maosh): amount to'g'ridan-to'g'ri
    # yoziladi va qty×stavka ga bog'liq emas. Rustam akaning bazasida
    # ishchilar okladga ishlaydi (qty=0, amount=4 mln) — bu real holat.
    notogri = [f"#{w.id}" for w in db.query(m.WorkEntry).all()
               if w.qc_passed and Decimal(str(w.qty)) > 0
               and abs(Decimal(str(w.amount or 0))
                       - Decimal(str(w.qty)) * Decimal(str(w.rate))) > TIYIN]
    n.tekshir("ish haqi = miqdor × stavka (sdelshina)", not notogri,
              f"{len(notogri)} ta: " + ", ".join(notogri[:5]))

    # ---- 6. To'lovlar mijozga bog'langanmi --------------------------
    yetim = db.query(m.Payment).filter(
        ~m.Payment.client_id.in_(db.query(m.Client.id))).count()
    n.tekshir("to'lovlarda yetim yozuv yo'q", yetim == 0, f"{yetim} ta")

    # ---- 7. Buyurtma maqomi profilda bormi --------------------------
    mavjud = {st.nom for st in domain.profil().modul.statuslar}
    notanish = defaultdict(int)
    for o in db.query(m.Order).all():
        if o.status not in mavjud:
            notanish[o.status] += 1
    # Bu OGOHLANTIRISH: profil almashtirilsa eski buyurtmalar eski
    # maqomda qoladi — bu kutilgan hol, ma'lumot buzilgani emas.
    n.tekshir("buyurtma maqomlari faol profilda bor", not notanish,
              ", ".join(f"«{k}» {v} ta" for k, v in list(notanish.items())[:5]),
              ogohmi=True)

    # ---- 8. Manfiy pul yo'qmi ---------------------------------------
    manfiy_pul = []
    if db.query(m.Payment).filter(m.Payment.amount < 0).count():
        manfiy_pul.append("to'lovlarda manfiy summa")
    if db.query(m.Order).filter(m.Order.total < 0).count():
        manfiy_pul.append("buyurtmalarda manfiy jami")
    if db.query(m.KassaEntry).filter(m.KassaEntry.amount < 0).count():
        manfiy_pul.append("kassada manfiy summa")
    n.tekshir("manfiy pul summasi yo'q", not manfiy_pul, ", ".join(manfiy_pul))

    # ---- 9. Retsept birlik ziddiyatlari -----------------------------
    ziddiyat = domain.retsept_ziddiyatlari()
    n.tekshir("retseptlarda birlik ziddiyati yo'q", not ziddiyat,
              "; ".join(ziddiyat[:3]))

    # ---- 10. Narx tannarxdan past buyurtmalar -----------------------
    zarar = [f"#{o.id}" for o in db.query(m.Order).all()
             if Decimal(str(o.unit_cost or 0)) > 0
             and Decimal(str(o.unit_price)) < Decimal(str(o.unit_cost))]
    n.tekshir("zarariga sotilgan buyurtma yo'q", not zarar,
              f"{len(zarar)} ta: " + ", ".join(zarar[:8]), ogohmi=True)

    # ---- BOSH KITOB (parallel davr tekshiruvi) ---------------------
    # GL hozircha eski hisob-kitob bilan PARALLEL yoziladi. Bu ikkalasi
    # bir xil raqam berayotganini tekshiradi — GL ni asosiy manba
    # qilishdan OLDIN shu toza o'tishi shart.
    try:
        from app.hisob import xizmat as gl
        provodka_bor = db.query(m.Provodka).count() > 0
    except Exception:                              # noqa: BLE001
        provodka_bor = False

    if provodka_bor:
        # 1. Balans: jami debet == jami kredit (Дт—Кт shakli buni
        #    kafolatlaydi; teng chiqmasa ma'lumot qo'lda buzilgan)
        b = gl.balans_tekshiruvi(db)
        n.tekshir("bosh kitob balansi (debet == kredit)",
                  b["jami_debet"] == b["jami_kredit"],
                  f"debet {b['jami_debet']} != kredit {b['jami_kredit']}")

        # 2. Mijoz qarzi: GL dagi 4010 saldosi == eski usul bo'yicha jami qarz
        gl_qarz = gl.saldo(db, "4010")["qoldiq"]
        eski_qarz = Decimal("0")
        for c in db.query(m.Client).all():
            eski_qarz += Decimal(str(s.client_balance(db, c.id)["debt"]))
        # Faqat GL yozila boshlagandan keyingi buyurtmalar hisobga olinadi,
        # shuning uchun eski baza bo'lsa farq bo'lishi TABIIY — ogohlantirish.
        n.tekshir("GL mijoz qarzi (4010) eski usulga mos",
                  abs(gl_qarz - eski_qarz) <= TIYIN,
                  f"GL {gl_qarz} != eski usul {eski_qarz} "
                  f"(farq {gl_qarz - eski_qarz}). Parallel davrda GL faqat "
                  f"YANGI amallarni yozadi — eski ma'lumotli bazada bu normal.",
                  ogohmi=True)

        # 3. Kassa: GL dagi 5010 manfiy bo'lmasin (pul manfiy bo'lolmaydi)
        kassa = gl.saldo(db, "5010")["qoldiq"]
        n.tekshir("GL kassa saldosi manfiy emas", kassa >= 0,
                  f"kassa {kassa} — manfiy qoldiq mumkin emas")

        # 4. Storno qilingan provodka ikki marta storno qilinmagan
        stornolar = [x.storno_id for x in db.query(m.Provodka)
                     .filter(m.Provodka.storno_id.isnot(None)).all()]
        n.tekshir("har provodka bir marta storno qilingan",
                  len(stornolar) == len(set(stornolar)),
                  "bitta provodka ikki marta bekor qilingan")

        # 5. Yopilgan davrga yozuv tushmagan
        yopiq = {d.oy for d in db.query(m.YopilganDavr).all()}
        buzuq = [p.id for p in db.query(m.Provodka).all()
                 if p.sana.strftime("%Y-%m") in yopiq]
        n.tekshir("yopilgan davrda yangi yozuv yo'q", not buzuq,
                  f"{len(buzuq)} provodka yopilgan davrda: {buzuq[:5]}")

    return n


def main() -> int:
    db = SessionLocal()
    try:
        print(f"Faol profil: {domain.profil().nom}")
        print(f"Buyurtma: {db.query(m.Order).count()} · "
              f"Mijoz: {db.query(m.Client).count()} · "
              f"To'lov: {db.query(m.Payment).count()} · "
              f"Material: {db.query(m.Material).count()}")
        print()
        n = tekshir_hammasi(db)
    finally:
        db.close()

    if n.ogoh:
        print(f"⚠️  {len(n.ogoh)} ogohlantirish (ma'lumot buzilgani emas):")
        for x in n.ogoh:
            print("   ·", x)
        print()
    if n.xato:
        print(f"❌ {len(n.xato)} NOMUVOFIQLIK:")
        for x in n.xato:
            print("   ·", x)
        return 1
    print(f"✅ {n.tekshiruv} TEKSHIRUV — BAZA BUTUN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
