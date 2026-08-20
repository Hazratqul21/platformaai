from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..auth import get_user, require_roles
from .. import models as m
from .. import services as s
from .. import kassa_sync as ks
from .. import domain
from ..domain import soha_yoz, soha_oqi

router = APIRouter(prefix="/api/orders", tags=["Buyurtmalar"])


class QuoteIn(BaseModel):
    product_name: str = ""
    length_mm: int
    width_mm: int
    height_mm: int
    tur: str = m.TUR_DEFAULT      # "3 слой" / "Самоклейка" / "Офсет" / "Картон Меловка"
    layers: int = 3               # eski mijozlar uchun; tur dan qayta hisoblanadi
    grade: str = "K1"
    colors: int = 0
    is_offset: bool = False
    qty: int = 1000
    client_id: int | None = None


class OrderIn(BaseModel):
    """Buyurtma yaratish — SOHA-NEYTRAL.

    Soha maydonlari `attributes` da keladi. Eski (tekis) karton maydonlari
    ham qabul qilinadi, chunki hozirgi frontend shunday yuboradi — ular
    quyida `attributes` ga yig'iladi. Frontend ko'chgach olib tashlanadi.
    """
    client_id: int
    qty: float = 1000
    product_name: str = ""
    attributes: dict | None = None
    unit_price: float | None = None   # menejer qo'lda o'zgartirsa
    qqs_stavka: float | None = None   # eksport 0% kabi istisnolar uchun
    prepaid_percent: int = 0
    due_days: int = 15          # tayyorlash muddati
    payment_due_days: int = 15  # to'lov muddati
    note: str = ""



def soha_qiymatlari(data) -> dict:
    """So'rovdan soha maydonlarini yig'adi: `attributes` + tekis maydonlar."""
    qiymatlar = dict(getattr(data, "attributes", None) or {})
    for kalit in domain.profil().kalitlar:
        qiymat = getattr(data, kalit, None)
        if qiymat is not None and kalit not in qiymatlar:
            qiymatlar[kalit] = qiymat
    return qiymatlar


def tekshir_yoki_400(qiymatlar: dict, qty) -> tuple[dict, Decimal]:
    """Miqdorni va soha maydonlarini profil qoidalari bo'yicha tekshiradi."""
    miqdor, xato = domain.miqdor_tekshir(qty)
    if xato:
        raise HTTPException(400, xato)
    tayyor, xato = domain.tayyorla(qiymatlar)
    if xato:
        raise HTTPException(400, xato)
    return tayyor, miqdor


def narxla(db, qiymatlar: dict, qty, category: str,
           qolda_narx: float | None, order=None) -> dict:
    """Tannarx va narxni profil belgilagan usul bilan hisoblaydi.

    "karton_formula" — eski m²/FIFO/ustama hisobi (bayt-ma-bayt o'zgarmagan)
    "retsept"        — RETSEPTDAN: material + ish haqi + qo'shimcha xarajat,
                       ustiga mijoz toifasi bo'yicha ustama. Har soha shu
                       bilan o'z kalkulyatoriga ega bo'ladi.
    "qolda"          — menejer narxni o'zi kiritadi (formulasi yo'q soha)
    """
    p = domain.profil()
    usul = p.narx.get("usul", "qolda")

    if usul == "karton_formula":
        res = s.quote(db, qiymatlar["length_mm"], qiymatlar["width_mm"],
                      qiymatlar["height_mm"], qiymatlar["layers"],
                      qiymatlar["grade"], qiymatlar["colors"], qty, category)
        return {"unit_cost": res["unit_cost"], "unit_price": res["unit_price"],
                "hisoblangan": {"m2_per_box": res["m2_per_box"]}, "xom": res}

    if usul == "retsept":
        hisob = retsept_narxi(db, qiymatlar, qty, category)
        # Menejer narxni qo'lda bergan bo'lsa u ustun — hisob faqat
        # tannarx va marja ko'rsatish uchun qoladi.
        narx = (Decimal(str(qolda_narx)) if qolda_narx
                else hisob["unit_price"])
        return {"unit_cost": hisob["unit_cost"], "unit_price": narx,
                "hisoblangan": {}, "xom": hisob}

    if qolda_narx is None:
        raise HTTPException(400, "Нарх киритилсин (профилда формула йўқ)")
    return {"unit_cost": Decimal("0"), "unit_price": Decimal(str(qolda_narx)),
            "hisoblangan": {}, "xom": None}


class _Vaqtinchalik:
    """Retsept hisobiga kerak bo'ladigan «buyurtmaga o'xshash» obyekt.

    Retsept `order.attributes` va `order.qty` ni o'qiydi. Smeta paytida
    hali buyurtma YO'Q, shuning uchun shu yengil o'rinbosar ishlatiladi —
    bazaga hech narsa yozilmaydi.
    """

    def __init__(self, attributes, qty):
        self.attributes = attributes
        self.qty = qty
        self.id = None


def retsept_narxi(db, qiymatlar: dict, qty, category: str) -> dict:
    """Retseptdan to'liq smeta: material + ish haqi + xarajat + ustama.

    Formulasi:
        1 dona tannarx = (material summasi / miqdor)
                       + ish haqi (1 dona)
                       + qo'shimcha xarajat (% material+ish haqidan)
        taklif narxi   = tannarx × (1 + ustama%)

    Ustama mijoz toifasidan (VIP/Standart/Yangi) — mavjud sozlamalar
    qayta ishlatildi, chunki ular allaqachon ishlab turgan mantiq.
    """
    p = domain.profil()
    qty_d = Decimal(str(qty or 1)) or Decimal("1")

    qatorlar = domain.retsept_qatorlari(_Vaqtinchalik(qiymatlar, qty_d))
    material = s.retsept_tannarx(db, qatorlar)

    # Ish haqi: son yoki soha maydonlari ustidan formula
    ish_haqi_ifoda = str(p.narx.get("ish_haqi", "0"))
    ozgaruvchilar = {"qty": float(qty_d)}
    for k, v in qiymatlar.items():
        if isinstance(v, bool):
            ozgaruvchilar[k] = 1.0 if v else 0.0
        elif isinstance(v, (int, float, Decimal)):
            ozgaruvchilar[k] = float(v)
    try:
        ish_haqi = Decimal(str(s.eval_formula(ish_haqi_ifoda, **ozgaruvchilar)))
    except (ValueError, KeyError, TypeError):
        ish_haqi = Decimal("0")
        material["ogohlantirish"].append(
            f"Ish haqi formulasi noto'g'ri: {ish_haqi_ifoda}")

    material_1 = (material["jami"] / qty_d).quantize(Decimal("0.01"))
    xarajat_foiz = Decimal(str(p.narx.get("qoshimcha_xarajat_foiz", 0)))
    xarajat = ((material_1 + ish_haqi) * xarajat_foiz / 100).quantize(Decimal("0.01"))

    tannarx = material_1 + ish_haqi + xarajat
    ustama = s.ustama_foizi(db, category)
    narx = (tannarx * (Decimal("1") + ustama / 100)).quantize(Decimal("0.01"))

    return {
        "unit_cost": tannarx, "unit_price": narx,
        "material_1dona": material_1, "material_jami": material["jami"],
        "ish_haqi_1dona": ish_haqi, "qoshimcha_xarajat_1dona": xarajat,
        "ustama_foiz": ustama, "qatorlar": material["qatorlar"],
        "ogohlantirish": material["ogohlantirish"],
    }


@router.post("/quote")
def make_quote(q: QuoteIn, db: Session = Depends(get_db), user=Depends(get_user)):
    """Smeta kalkulyatori — KARTONGA XOS (m² × qog'oz narxi × ustama).

    Boshqa profilda bu hisob ma'nosiz, shuning uchun rad etiladi: non
    zavodi narxni qo'lda kiritadi (`narx.usul = "qolda"`). Har sohaning
    o'z kalkulyatori bo'lishi — keyingi ish.
    """
    if domain.profil().narx.get("usul") != "karton_formula":
        raise HTTPException(400, "Бу профилда смета калкулятори йўқ — "
                                 "нарх қўлда киритилади")
    tayyor, miqdor = tekshir_yoki_400(soha_qiymatlari(q), q.qty)
    category = "Standart"
    credit = None
    if q.client_id:
        c = db.get(m.Client, q.client_id)
        if c:
            category = c.category
    res = s.quote(db, tayyor["length_mm"], tayyor["width_mm"], tayyor["height_mm"],
                  tayyor["layers"], tayyor["grade"], tayyor["colors"], miqdor, category)
    if q.client_id:
        c = db.get(m.Client, q.client_id)
        if c:
            credit = s.credit_check(db, c, Decimal(res["total"]))
    # Decimal -> float JSON uchun
    out = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in res.items()}
    out["category"] = category
    out["credit"] = credit
    return out


def order_out(o: m.Order) -> dict:
    soha = domain.soha_hammasi(o)   # soha maydonlari — attributes dan
    # Miqdorlar endi Decimal (kasrli bo'lishi mumkin) — pul hisobida
    # float bilan ARALASHTIRILMAYDI, aks holda TypeError va aniqlik
    # yo'qolishi. JSON ga chiqishda bir marta float qilinadi.
    delivered = Decimal(str(o.delivered_qty or 0))
    delivered_value = float(Decimal(str(o.unit_price)) * delivered)
    paid_for_order = float(sum(Decimal(p.amount) for p in o.payments)) if o.payments else 0.0
    # Asosiy rasm sifatida ko'rsatiladigan fayl (pastdagi izohga qarang)
    asosiy_rasm = o.photo or ""
    if o.photos and asosiy_rasm not in [p.filename for p in o.photos]:
        asosiy_rasm = o.photos[0].filename
    return {
        "id": o.id, "client_id": o.client_id, "company": o.client.company,
        "product_name": o.product_name,
        "size": domain.olcham_matni(o),
        "tur": domain.tur_matni(o),
        "tarkib": domain.tarkib_matni(o),
        # Asosiy rasm: eski o.photo maydonidagi fayl endi mavjud bo'lmasligi mumkin
        # (fayl o'chirilgan/ko'chirilgan). Shunda mavjud rasmlardan birinchisini
        # ko'rsatamiz — aks holda buzuq rasm belgisi va 404 chiqadi.
        "photo": asosiy_rasm,
        "photo_url": f"/uploads/{asosiy_rasm}" if asosiy_rasm else None,
        "photos": [{"filename": p.filename, "url": f"/uploads/{p.filename}"} for p in o.photos]
                  or ([{"filename": asosiy_rasm, "url": f"/uploads/{asosiy_rasm}"}] if asosiy_rasm else []),
        "qty": float(o.qty),
        # Soha maydonlarining YAGONA manbasi. Frontend formani va
        # tavsifni shundan chizadi (static/js/core/soha.js).
        "attributes": o.attributes or {},
        "delivered_qty": float(delivered),
        "qolgan_qty": float(Decimal(str(o.qty)) - delivered),
        "qty_birlik": domain.profil().birlik,
        # topshirilgan mol qiymati vs shu buyurtmaga bog'langan to'lov
        "delivered_value": delivered_value, "paid_for_order": paid_for_order,
        "tolanmadi": delivered > 0 and paid_for_order + 1 < delivered_value,
        "unit_cost": float(o.unit_cost),
        "unit_price": float(o.unit_price), "total": float(o.total),
        # QQS: `total` — mijoz to'laydigan (QQS bilan), `qqssiz` — soliqsiz asos
        "qqs_stavka": float(o.qqs_stavka or 0),
        "qqs_summa": float(o.qqs_summa or 0),
        "qqssiz_summa": float(Decimal(str(o.total)) - Decimal(str(o.qqs_summa or 0))),
        "margin": round((float(o.unit_price) / float(o.unit_cost) - 1) * 100, 1) if float(o.unit_cost) else 0,
        "prepaid_percent": o.prepaid_percent, "status": o.status, "note": o.note,
        # bazada UTC — foydalanuvchiga Toshkent vaqti (aks holda kechqurun
        # yaratilgan zakaz oldingi kun bo'lib ko'rinadi)
        "created_at": s.mahalliy_vaqt(o.created_at).isoformat(),
        "due_date": o.due_date.isoformat() if o.due_date else None,
        "payment_due_date": o.payment_due_date.isoformat() if o.payment_due_date else None,
        "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
        "accepted_stamp": o.accepted_stamp,
    }


@router.get("")
def list_orders(status: str | None = None, firm: str | None = None,
               archive: int = 0, db: Session = Depends(get_db), user=Depends(get_user)):
    """archive=0 (standart): FAOL zakazlar — hali ishlanayotgan yoki qisman topshirilgan.
    To'liq topshirilgan (Yetkazildi, qoldi=0) va bekor qilinganlar KO'RINMAYDI.
    archive=1: aynan o'sha tugallangan/bekor qilingan zakazlar (arxiv)."""
    q = db.query(m.Order).order_by(m.Order.created_at.desc())
    if status:
        q = q.filter(m.Order.status == status)
    if firm:
        # buyurtma firmasi = mijozning firmasi (ikki firma aralashmasligi uchun).
        # firmasi belgilanmagan mijoz ikkala firmada ham ko'rinadi.
        q = q.filter(m.Order.client.has(m.Client.firm.in_([firm, ""])))
    rows = q.limit(500).all()

    def tugallangan(o):
        # to'liq topshirilgan yoki bekor qilingan — arxivga
        mano = domain.manosi(o.status)
        return mano == "bekor" or \
            (mano == "topshirildi" and (o.delivered_qty or 0) >= o.qty)

    if archive:
        rows = [o for o in rows if tugallangan(o)]
    else:
        rows = [o for o in rows if not tugallangan(o)]
    return [order_out(o) for o in rows[:300]]


@router.post("")
def create_order(data: OrderIn, db: Session = Depends(get_db),
                 user=Depends(require_roles("Menejer"))):
    c = db.get(m.Client, data.client_id)
    if not c:
        raise HTTPException(404, "Мижоз топилмади")
    if data.unit_price is not None and data.unit_price <= 0:
        raise HTTPException(400, "Нарх 0 дан катта бўлсин")

    tayyor, miqdor = tekshir_yoki_400(soha_qiymatlari(data), data.qty)
    narx = narxla(db, tayyor, miqdor, c.category, data.unit_price)
    tayyor.update(narx["hisoblangan"])   # m2_per_box va h.k.

    unit_price = (Decimal(str(data.unit_price)) if data.unit_price
                  else narx["unit_price"])
    # QQS: `total` mijoz TO'LAYDIGAN summa (QQS bilan). Kredit limiti va
    # qarz ham shu summadan hisoblanadi — mijoz aynan shuni to'laydi.
    qqs = s.qqs_hisobla(db, unit_price * miqdor, data.qqs_stavka)
    total = qqs["jami"]
    check = s.credit_check(db, c, total)
    if check["blocked"]:
        reason = "qora ro'yxatda" if check["blacklisted"] else "kredit limitidan oshadi"
        raise HTTPException(409, f"Buyurtma bloklandi: mijoz {reason}. Rahbar tasdig'i kerak.")

    o = m.Order(
        client_id=c.id, qty=miqdor,
        qqs_stavka=qqs["stavka"], qqs_summa=qqs["qqs"],
        # Boshlang'ich maqom ustun standartidan EMAS, ish tartibidan:
        # sexda «Kutishda», savdoda «Yangi buyurtma», servisda «Qabul qilindi».
        status=domain.boshlangich_status(),
        unit_cost=narx["unit_cost"], unit_price=unit_price, total=total,
        prepaid_percent=data.prepaid_percent, note=data.note,
        product_name=data.product_name,
        due_date=date.today() + timedelta(days=data.due_days),
        payment_due_date=date.today() + timedelta(days=data.payment_due_days),
    )
    soha_yoz(o, tayyor)          # soha maydonlari -> attributes
    db.add(o)
    db.flush()
    db.add(m.AuditLog(who=user.name, action="Buyurtma yaratildi",
                      detail=f"{c.company} · {miqdor} {domain.profil().birlik} · {float(total):,.0f} so'm"))
    db.commit()
    # mijozga botdan smeta yuboriladi (bot yoqilgan va mijoz bog'langan bo'lsa)
    try:
        from ..bot import notify_order
        notify_order(o.id)
    except Exception:
        pass  # bot ishlamasa buyurtma baribir yaratiladi
    out = order_out(o)
    out["credit_warning"] = check["over_limit"]
    return out


class OrderEditIn(BaseModel):
    """Tahrir — yaratish kabi soha-neytral."""
    product_name: str | None = None
    attributes: dict | None = None
    qty: float | None = None
    unit_price: float | None = None
    note: str | None = None
    due_days: int | None = None
    payment_due_days: int | None = None



@router.put("/{oid}")
def edit_order(oid: int, data: OrderEditIn, db: Session = Depends(get_db),
               user=Depends(require_roles("Menejer", "Buxgalter"))):
    """Buyurtmani yaratilgandan keyin tuzatish: dona, narx, o'lcham, tur, marka, izoh,
    muddatlar. Jami qayta hisoblanadi. Cexga berilgan bo'lsa xomashyo allaqachon
    yechilgan — ogohlantirish beriladi, lekin tuzatishga ruxsat (rahbar qaroriga)."""
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
    if domain.manosi(o.status) in ("topshirildi", "bekor"):
        raise HTTPException(400, "Етказилган ёки бекор қилинган буюртмани таҳрирлаб бўлмайди")

    # Mavjud soha qiymatlari ustiga so'rovdagilarni qo'yamiz — berilmagani
    # o'zgarmaydi. Tekshiruv va hosila hisobi yaratishdagi bilan bir xil.
    qiymatlar = domain.soha_hammasi(o)
    qiymatlar.update(soha_qiymatlari(data))

    qty = data.qty if data.qty is not None else o.qty
    if Decimal(str(qty)) < Decimal(str(o.delivered_qty or 0)):
        raise HTTPException(400, f"Тираж топширилган миқдордан ({o.delivered_qty}) кам бўлмасин")
    tayyor, qty = tekshir_yoki_400(qiymatlar, qty)
    narx = narxla(db, tayyor, qty, o.client.category, data.unit_price)
    tayyor.update(narx["hisoblangan"])

    o.product_name = data.product_name if data.product_name is not None else o.product_name
    o.qty = qty
    o.unit_cost = narx["unit_cost"]
    o.unit_price = Decimal(str(data.unit_price)) if data.unit_price else narx["unit_price"]
    # Tahrirda QQS stavkasi BUYURTMANIKI bo'lib qoladi — davlat stavkani
    # o'zgartirgan bo'lsa ham eski hujjat o'z stavkasida qayta hisoblanadi.
    qqs = s.qqs_hisobla(db, o.unit_price * qty, o.qqs_stavka or None)
    o.qqs_stavka, o.qqs_summa = qqs["stavka"], qqs["qqs"]
    o.total = qqs["jami"]
    soha_yoz(o, tayyor)
    if data.note is not None:
        o.note = data.note
    if data.due_days is not None:
        o.due_date = date.today() + timedelta(days=data.due_days)
    if data.payment_due_days is not None:
        o.payment_due_date = date.today() + timedelta(days=data.payment_due_days)

    # DIQQAT: tiraj berilgan miqdorga tenglashsa ham zakazni AVTOMAT yopmaymiz.
    # Sababi: yopilgan (Yetkazib berildi) zakazni na tahrirlash, na statusini
    # qaytarish mumkin. Foydalanuvchi tirajni xato yozsa (10000 o'rniga 1000)
    # zakaz o'z-o'zidan yopilib qolar va uni faqat baza orqali tuzatish kerak
    # bo'lardi. Shuning uchun faqat OGOHLANTIRAMIZ — yopishni foydalanuvchi
    # «🏁 Якунлаш» tugmasi orqali o'zi, tasdiqlab bajaradi.
    tugagan = ((o.delivered_qty or 0) >= o.qty
               and domain.manosi(o.status) in ("tayyor", "ishlab_chiqarish"))

    ogoh = None
    if tugagan:
        ogoh = (f"Тираж топширилган миқдорга ({o.delivered_qty} {domain.profil().birlik}) тенглашди. "
                f"Буюртмани ёпиш учун «Якунлаш» тугмасини босинг — шунда архивга ўтади."
                ).replace(",", " ")
    elif domain.manosi(o.status) == "ishlab_chiqarish":
        ogoh = "Диққат: бу буюртма цехга берилган, хомашё аллақачон ечилган. Миқдор ўзгарса омбор қолдиғи мос келмаслиги мумкин."
    db.add(m.AuditLog(who=user.name, action="Buyurtma tuzatildi",
                      detail=f"Буюртма #{o.id} · {o.client.company} · "
                             f"{qty} дона · {float(o.total):,.0f}".replace(",", " ")))
    db.commit()
    out = order_out(o)
    out["ogoh"] = ogoh
    return out


@router.post("/{oid}/reorder")
def reorder(oid: int, qty: int | None = None, db: Session = Depends(get_db),
            user=Depends(require_roles("Menejer"))):
    """Takroriy buyurtma — eski parametrlar, yangi tiraj, joriy narxlar (TZ 1.1)."""
    old = db.get(m.Order, oid)
    if not old:
        raise HTTPException(404, "Буюртма топилмади")
    # Soha maydonlari `attributes` dan KO'CHIRILADI — qaysi maydon
    # borligini bu yer bilmasligi kerak. Ilgari bu yerda karton ustunlari
    # sanab chiqilgan edi, ya'ni non zavodida takroriy buyurtma
    # og'irligini ham, un navini ham yo'qotardi.
    data = OrderIn(
        client_id=old.client_id, product_name=old.product_name,
        attributes=dict(old.attributes or {}),
        qty=qty or float(old.qty), note=f"Takroriy (#{old.id} asosida)",
    )
    return create_order(data, db, user)


# VALID_FLOW va ROLE_PERMISSIONS jadvallari OLIB TASHLANDI — endi ular
# modul ta'rifida (app/modules/*.json), chunki ish tartibi biznes turiga
# qarab o'zgaradi: sexda "Sexda kesilmoqda", savdoda "Yig'ilmoqda",
# servisda "Tuzatilmoqda". Yadro NOMNI emas, MA'NOni biladi.


@router.get("/{oid}/check-stock")
def check_stock(oid: int, db: Session = Depends(get_db), user=Depends(get_user)):
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
    
    xom, marka = domain.xomashyo_kerak(o)
    if xom is None:
        # Bu soha ombordan avtomatik xomashyo yechmaydi — tekshiradigan
        # narsa yo'q, «yetarli» deb javob beramiz.
        return {"ok": True, "missing_kg": 0.0, "xomashyo_hisobi": False}

    brak = Decimal("1") + s.dset(db, "brak_percent") / 100
    need_m2 = (xom * brak).quantize(Decimal("0.0001"))

    # fifo_writeoff simulyatsiyasi: har lotning o'z grammaji bilan m2->kg o'giriladi
    remaining_m2 = need_m2
    lots = db.query(m.RawLot).filter(m.RawLot.grade == marka, m.RawLot.remaining_kg > 0).order_by(m.RawLot.received_at, m.RawLot.id).all()
    
    missing_kg = Decimal("0")
    for lot in lots:
        if remaining_m2 <= 0:
            break
        kg_per_m2 = Decimal(lot.grammage) / Decimal("1000")
        need_kg_for_lot = remaining_m2 * kg_per_m2
        take_kg = min(Decimal(lot.remaining_kg), need_kg_for_lot)
        
        m2_covered = take_kg / kg_per_m2
        remaining_m2 -= m2_covered
        
    if remaining_m2 > Decimal("0.001"):
        # Not enough stock for the remaining m2. Let's estimate the kg needed using an average grammage (e.g. 120g).
        missing_kg = remaining_m2 * (Decimal("120") / Decimal("1000"))
        
    return {"ok": missing_kg <= 0, "missing_kg": float(missing_kg)}

class SmetaIn(BaseModel):
    """Universal smeta so'rovi — har soha uchun."""
    attributes: dict = {}
    qty: float = 1
    client_id: int | None = None


@router.post("/smeta")
def smeta(data: SmetaIn, db: Session = Depends(get_db), user=Depends(get_user)):
    """HAR SOHA uchun smeta — buyurtma yaratmasdan.

    Eski `/quote` faqat kartonga yaraydi (m² formulasi). Bu esa profil
    qaysi usulni e'lon qilgan bo'lsa o'shani ishlatadi, ya'ni non zavodi
    ham, mebel sexi ham o'z kalkulyatoriga ega bo'ladi.
    """
    tayyor, miqdor = tekshir_yoki_400(dict(data.attributes), data.qty)

    category = "Standart"
    if data.client_id:
        c = db.get(m.Client, data.client_id)
        if c:
            category = c.category

    p = domain.profil()
    usul = p.narx.get("usul", "qolda")
    if usul == "qolda":
        return {"usul": "qolda", "birlik": p.birlik, "qty": float(miqdor),
                "izoh": "Bu profilda formula yo'q — narx qo'lda kiritiladi"}

    if usul == "karton_formula":
        res = s.quote(db, tayyor["length_mm"], tayyor["width_mm"],
                      tayyor["height_mm"], tayyor["layers"], tayyor["grade"],
                      tayyor["colors"], miqdor, category)
        chiqish = {k: (float(v) if isinstance(v, Decimal) else v)
                   for k, v in res.items()}
        chiqish.update({"usul": usul, "birlik": p.birlik, "category": category})
        return chiqish

    h = retsept_narxi(db, tayyor, miqdor, category)
    jami = (h["unit_price"] * miqdor).quantize(Decimal("0.01"))
    qqs = s.qqs_hisobla(db, jami)
    return {
        "usul": usul, "birlik": p.birlik, "qty": float(miqdor),
        "category": category,
        "material_jami": float(h["material_jami"]),
        "material_1dona": float(h["material_1dona"]),
        "ish_haqi_1dona": float(h["ish_haqi_1dona"]),
        "qoshimcha_xarajat_1dona": float(h["qoshimcha_xarajat_1dona"]),
        "unit_cost": float(h["unit_cost"]),
        "ustama_foiz": float(h["ustama_foiz"]),
        "unit_price": float(h["unit_price"]),
        "jami": float(jami),
        "qqs_stavka": float(qqs["stavka"]), "qqs": float(qqs["qqs"]),
        "jami_qqs_bilan": float(qqs["jami"]),
        "materiallar": [{"material": q["material"], "birlik": q["birlik"],
                         "miqdor": float(q["miqdor"]), "summa": float(q["summa"])}
                        for q in h["qatorlar"]],
        "ogohlantirish": h["ogohlantirish"],
    }


@router.get("/{oid}/retsept")
def order_retsept(oid: int, db: Session = Depends(get_db), user=Depends(get_user)):
    """Buyurtmaga qancha material ketishi — ishlab chiqarishdan OLDIN.

    Menejer «sexga berish» tugmasini bosishdan oldin nima yetishmasligini
    ko'rishi kerak. Ilgari buni faqat status o'zgartirib, 409 xatosini
    olib bilish mumkin edi.
    """
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")

    qatorlar = domain.retsept_qatorlari(o)
    if not qatorlar:
        return {"order_id": oid, "retsept_bor": False, "qatorlar": [],
                "yetadi": True}

    natija = []
    yetadi = True
    for q in qatorlar:
        mat = s.material_top(db, q["material"])
        qator = {"material": q["material"], "birlik": q["birlik"],
                 "kerak": float(q["miqdor"]), "xato": q.get("xato")}
        if mat is None:
            qator.update({"omborda": 0.0, "yetadi": False,
                          "izoh": "ombor kartochkasi yo'q"})
            yetadi = False
        else:
            try:
                koef = s._konversiya(mat, q["birlik"])
            except ValueError as e:
                qator.update({"omborda": float(mat.stock_qty or 0),
                              "yetadi": False, "izoh": str(e)})
                yetadi = False
                natija.append(qator)
                continue
            kerak_mat = Decimal(str(q["miqdor"])) * koef
            bor = Decimal(str(mat.stock_qty or 0))
            qator.update({
                "material_birligi": mat.unit,
                "kerak_material_birligida": float(kerak_mat),
                "omborda": float(bor),
                "yetadi": bor >= kerak_mat,
            })
            if bor < kerak_mat:
                yetadi = False
        natija.append(qator)

    # Har qatorning PULI ham kerak, faqat miqdori emas. Qo'lda narx
    # qo'yiladigan sohalarda (avto servis, texnika ta'miri, montaj) usta
    # narxni boshidan yozadi, ehtiyot qism esa ombordan ketadi — ikkalasi
    # solishtirilmasa zarariga sotilgani hech qayerda ko'rinmaydi.
    tannarx = s.retsept_tannarx(db, qatorlar)
    pul = {t["material"]: t for t in tannarx["qatorlar"]}
    for qator in natija:
        t = pul.get(qator["material"])
        if t is not None:
            qator["summa"] = float(t["summa"])

    xomashyo = Decimal(str(tannarx["jami"]))
    qqssiz = Decimal(str(o.total or 0)) - Decimal(str(o.qqs_summa or 0))
    javob = {"order_id": oid, "retsept_bor": True, "qatorlar": natija,
             "yetadi": yetadi, "xomashyo_summasi": float(xomashyo),
             "qqssiz_summa": float(qqssiz)}
    if xomashyo > qqssiz:
        javob["zarar_ogoh"] = (
            f"Зарарига сотилмоқда: хомашё {xomashyo:,.0f} сўм, "
            f"буюртма (ҚҚСсиз) {qqssiz:,.0f} сўм. Нархни қайта кўринг.")
    return javob


@router.post("/{oid}/status")
def set_status(oid: int, status: str, db: Session = Depends(get_db), user=Depends(get_user)):
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
        
    md = domain.modul()
    yangi = md.status(status)
    if yangi is None:
        raise HTTPException(400, f"'{status}' — bu ish tartibida yo'q maqom. "
                                 f"Mumkin: {', '.join(md.nomlar)}")

    if user.role != "Rahbar" and user.role not in yangi.rollar:
        raise HTTPException(403, f"{user.role} roliga '{status}' maqomini o'rnatish ruxsat etilmaydi")

    joriy = md.status(o.status)
    if joriy is None or status not in joriy.keyingi:
        raise HTTPException(400, f"'{o.status}' dan '{status}' ga o'tib bo'lmaydi")

    eski_mano = joriy.mano
    yangi_mano = yangi.mano

    if yangi_mano == "bekor" and eski_mano == "ishlab_chiqarish":
        # sexda bekor qilinsa yechilgan xomashyo omborga qaytariladi
        moves = db.query(m.StockMove).filter(m.StockMove.order_id == o.id).all()
        returned = Decimal("0")
        for mv in moves:
            if mv.kg > 0:
                lot = db.get(m.RawLot, mv.lot_id)
                if lot:
                    lot.remaining_kg = Decimal(lot.remaining_kg) + Decimal(mv.kg)
                    returned += Decimal(mv.kg)
                    db.add(m.StockMove(lot_id=lot.id, order_id=o.id, kg=-mv.kg, cost=-mv.cost))
        db.add(m.AuditLog(who=user.name, action="Xomashyo qaytarildi",
                          detail=f"Buyurtma #{o.id} bekor — {float(returned):.1f} kg omborga qaytdi"))
    if yangi_mano == "ishlab_chiqarish":
        # Ishlab chiqarishga berilganda xomashyo yechiladi. Ikki yo'l:
        #   RETSEPT (umumiy)  — istalgan material, har soha uchun
        #   m2_marka (karton) — eski, qog'ozga xos yo'l
        # Retsept bo'lsa u ustun: umumiy dvigatel puxtaroq (qisman
        # yechmaydi, yetmasa umuman tegmaydi).
        qatorlar = domain.retsept_qatorlari(o)
        material_qiymati = Decimal("0")
        if qatorlar:
            try:
                material_qiymati = s.retsept_yechish(
                    db, o, qatorlar, note=f"Buyurtma #{o.id} retsept bo'yicha")
            except ValueError as e:
                raise HTTPException(409, str(e))
        xom, marka = domain.xomashyo_kerak(o)
        if not qatorlar and xom is not None:
            brak = Decimal("1") + s.dset(db, "brak_percent") / 100
            need = (xom * brak).quantize(Decimal("0.0001"))
            try:
                material_qiymati = s.fifo_writeoff(
                    db, marka, need, order_id=o.id,
                    note=f"Buyurtma #{o.id} spisaniya (5% brak bilan)") or Decimal("0")
            except ValueError as e:
                raise HTTPException(409, str(e))

        # BOSH KITOB — material ishlab chiqarishga berildi: Дт2010 Кт1010.
        # Busiz 2810 (tayyor mahsulot) sotilganda MANFIY bo'lib ketardi —
        # omborga kirmagan mahsulot sotilgan bo'lib ko'rinardi.
        from ..hisob import ulash as gl_ulash
        if material_qiymati and material_qiymati > 0:
            gl_ulash.material_ishlab_chiqarishga(db, material_qiymati,
                                                 date.today(), o.id, user.name)
    if yangi_mano == "tayyor":
        # Tayyor mahsulot omborga kirdi: Дт2810 Кт2010.
        # Tannarx `unit_cost` dan olinadi — sotilganda ham shu summa
        # 2810 dan chiqadi, ya'ni schet nolga qaytadi.
        from ..hisob import ulash as gl_ulash
        tannarx = Decimal(str(o.unit_cost or 0)) * Decimal(str(o.qty or 0))
        if tannarx > 0:
            gl_ulash.mahsulot_tayyor(db, tannarx, date.today(), o.id, user.name)

    if yangi_mano == "topshirildi":
        o.delivered_at = date.today()
        # DIQQAT: bu yerda `delivered_qty` ATAYLAB o'zgartirilmaydi va
        # GL ga ham yozilmaydi. Sabab: qarz eski usulda ham
        # `delivered_qty` dan hisoblanadi (`services.client_balance`).
        # Agar GL bu yerda yozsa, ikkalasi bir-biriga mos kelmay
        # qolardi — parallel davrning butun ma'nosi shu moslikda.
        # Mol berish `/topshir` orqali qayd etiladi va GL o'sha yerda
        # yoziladi.
    o.status = status
    db.add(m.AuditLog(who=user.name, action="Status o'zgardi",
                      detail=f"Buyurtma #{o.id} → {status}"))
    db.commit()
    return order_out(o)


@router.get("/{oid}/topshirishlar")
def delivery_history(oid: int, db: Session = Depends(get_db), user=Depends(get_user)):
    """Bu buyurtma bo'yicha mol qachon, soat nechada va necha dona berilgani.

    Ma'lumot audit jurnalidan olinadi (u yerda har topshirish vaqti bilan
    saqlanadi) — shuning uchun qo'shimcha jadval/migratsiya kerak emas va
    eski yozuvlar ham ko'rinadi.
    """
    import re
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")

    boshlanish = f"Буюртма #{oid} ·"
    rows = (db.query(m.AuditLog)
            .filter(m.AuditLog.action == "Mijozga topshirildi",
                    m.AuditLog.detail.like(f"{boshlanish}%"))
            .order_by(m.AuditLog.at).all())

    out = []
    for r in rows:
        d = r.detail or ""
        dona = None
        # "· 1 000 дона" / "· 520 дона" ko'rinishidan sonni ajratamiz
        mm = re.search(r"·\s*([\d\s ]+?)\s*дона", d)
        if mm:
            try:
                dona = int(re.sub(r"[^\d]", "", mm.group(1)))
            except ValueError:
                dona = None
        pul = None
        mp = re.search(r"олинган пул:\s*([\d\s ]+)", d)
        if mp:
            try:
                pul = float(re.sub(r"[^\d]", "", mp.group(1)) or 0)
            except ValueError:
                pul = None
        v = s.mahalliy_vaqt(r.at)      # bazada UTC — Toshkent vaqtiga o'giramiz
        out.append({
            "at": v.isoformat(),
            "sana": v.strftime("%d.%m.%Y"),
            "vaqt": v.strftime("%H:%M"),
            "kim": r.who,
            "dona": dona,
            "pul": pul,
            "toliq": "(тўлиқ)" in d,
            "izoh": d,
        })
    return {"order_id": oid, "qty": o.qty, "delivered_qty": o.delivered_qty or 0,
            "topshirishlar": out}


@router.post("/{oid}/yakunla")
def finish_order(oid: int, db: Session = Depends(get_db),
                 user=Depends(require_roles("Rahbar", "Menejer", "Sklad mudiri"))):
    """Zakazni yakunlash — tiraj buyurtmadan kam chiqqan holat uchun.

    Masalan: 10 000 dona buyurtma qilingan, ishlab chiqarishda 9 250 chiqqan va
    hammasi mijozga berilgan. Oldin bunday zakaz "qoldi 750" bo'lib faol ro'yxatda
    abadiy osilib qolardi. Yakunlansa — berilgan miqdor yakuniy hisoblanadi va
    zakaz arxivga o'tadi.

    Qarz o'zgarmaydi: u allaqachon faqat BERILGAN mol bo'yicha hisoblanadi.
    """
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
    berildi = o.delivered_qty or 0
    if berildi <= 0:
        raise HTTPException(400, "Ҳали мол берилмаган — якунлаб бўлмайди. "
                                 "Аввал мижозга топширинг.")
    if domain.manosi(o.status) == "bekor":
        raise HTTPException(400, "Бекор қилинган буюртмани якунлаб бўлмайди")
    if berildi >= o.qty:
        # Hammasi berilgan, lekin status yangilanmay qolgan (masalan tiraj keyin
        # tuzatilgan) — bunda faqat statusni yopamiz, miqdorga tegmaymiz.
        if domain.manosi(o.status) == "topshirildi":
            raise HTTPException(400, "Буюртма аллақачон якунланган")
        o.status = domain.status_nomi("topshirildi")
        o.delivered_at = o.delivered_at or date.today()
        db.add(m.AuditLog(
            who=user.name, action="Буюртма якунланди",
            detail=f"Буюртма #{o.id} · {berildi} дона тўлиқ берилган эди, "
                   f"статус якунланди (архивга ўтди)"))
        db.commit()
        return order_out(o)

    eski_qty = o.qty
    o.qty = berildi                                    # ҳақиқий чиққан тираж
    o.total = Decimal(str(o.unit_price)) * berildi     # жами шунга мослашади
    o.status = domain.status_nomi("topshirildi")
    o.delivered_at = date.today()
    db.add(m.AuditLog(
        who=user.name, action="Буюртма якунланди",
        detail=f"Буюртма #{o.id} · {eski_qty} дона буюртма эди, {berildi} дона "
               f"чиқди ва берилди — якунланди (архивга ўтди)"))
    db.commit()
    return order_out(o)


class PhotoIn(BaseModel):
    data: str    # "data:image/jpeg;base64,...." ko'rinishida (telefonda olingan rasm)


@router.post("/{oid}/photo")
def upload_photo(oid: int, body: PhotoIn, db: Session = Depends(get_db),
                 user=Depends(require_roles("Menejer", "Sex boshlig'i", "Sklad mudiri"))):
    """Mahsulot rasmini saqlash — sexda telefonda olinadi, keyin buyurtma ichida ko'rinadi."""
    import base64
    import binascii
    from pathlib import Path

    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")

    raw = body.data or ""
    if "," in raw and raw.strip().startswith("data:"):
        header, raw = raw.split(",", 1)
        if "image/" not in header:
            raise HTTPException(400, "Фақат расм юклаш мумкин")
    try:
        blob = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "Расм бузуқ — қайтадан уриниб кўринг")
    if not blob:
        raise HTTPException(400, "Расм бўш")
    if len(blob) > 8 * 1024 * 1024:
        raise HTTPException(400, "Расм жуда катта (8 МБ дан ошмасин)")
    # haqiqatan rasmmi — fayl imzosi tekshiriladi (JPEG/PNG/WEBP)
    if not (blob[:3] == b"\xff\xd8\xff" or blob[:8] == b"\x89PNG\r\n\x1a\n"
            or blob[8:12] == b"WEBP"):
        raise HTTPException(400, "Фақат JPEG, PNG ёки WEBP расм бўлиши керак")

    # bir buyurtmada ko'pi bilan 10 ta rasm
    if len(o.photos) >= 10:
        raise HTTPException(400, "Бир буюртмага кўпи билан 10 та расм")

    # AKKAUNT PAPKASIGA saqlanadi — bir akkaunt rasmi boshqasiga
    # ko'rinmasin (ijarachiliksiz rejimda papka "_yagona").
    from .. import tenancy
    upload_dir = (Path(__file__).resolve().parent.parent.parent
                  / "uploads" / tenancy.kalit())
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = "png" if blob[:8] == b"\x89PNG\r\n\x1a\n" else "webp" if blob[8:12] == b"WEBP" else "jpg"
    name = f"order_{oid}_{int(datetime.now().timestamp() * 1000)}.{ext}"
    (upload_dir / name).write_bytes(blob)

    db.add(m.OrderPhoto(order_id=o.id, filename=name))
    if not o.photo:            # eski bitta rasm maydoni — birinchi rasm bo'lsin (moslik)
        o.photo = name
    db.add(m.AuditLog(who=user.name, action="Mahsulot rasmi",
                      detail=f"Buyurtma #{oid} ga rasm qo'shildi"))
    db.commit()
    photos = db.query(m.OrderPhoto).filter(m.OrderPhoto.order_id == o.id).order_by(m.OrderPhoto.id).all()
    return {"ok": True, "photo": name, "url": f"/uploads/{name}",
            "photos": [f"/uploads/{p.filename}" for p in photos]}


@router.delete("/{oid}/photo")
def delete_photo(oid: int, filename: str | None = None, db: Session = Depends(get_db),
                 user=Depends(require_roles("Menejer", "Sex boshlig'i", "Sklad mudiri"))):
    """filename berilsa — o'sha rasm; berilmasa — hammasi o'chiriladi."""
    from pathlib import Path
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
    upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads"

    def rm(fn):
        if fn:
            (upload_dir / Path(fn).name).unlink(missing_ok=True)

    if filename:
        ph = next((p for p in o.photos if p.filename == filename), None)
        if ph:
            rm(ph.filename)
            db.delete(ph)
        if o.photo == filename:
            db.flush()
            o.photo = o.photos[0].filename if o.photos else ""
    else:
        for p in list(o.photos):
            rm(p.filename)
            db.delete(p)
        rm(o.photo)
        o.photo = ""
    db.commit()
    photos = db.query(m.OrderPhoto).filter(m.OrderPhoto.order_id == oid).order_by(m.OrderPhoto.id).all()
    return {"ok": True, "photos": [f"/uploads/{p.filename}" for p in photos]}


class DeliverIn(BaseModel):
    qty: int = 0                  # topshirilayotgan dona (0 — qolgan hammasi)
    paid_amount: float = 0        # mijoz shu safar bergan pul (0 bo'lsa — qarzga ketdi)
    method: str = "Naqd"
    note: str = ""
    # O'tgan kunda berilgan mol keyin kiritilsa — o'sha sana yoziladi (YYYY-MM-DD).
    # Bo'sh bo'lsa bugungi sana. Kelajak sana va buyurtma yaratilishidan oldingi
    # sana qabul qilinmaydi.
    sana: str | None = None


@router.post("/{oid}/deliver")
def deliver_to_client(oid: int, data: DeliverIn, db: Session = Depends(get_db),
                      user=Depends(require_roles("Menejer", "Buxgalter", "Sklad mudiri"))):
    """Mollarni mijozga topshirish — qisman ham bo'lishi mumkin.
    qty (topshirilayotgan dona) berilmasa — hammasi topshiriladi.
    Hammasi topshirilsa status 'Yetkazib berildi', qisman bo'lsa 'Omborga tushdi' da qoladi.
    Pul kiritilmasa (0) — mol qarzga berilgan bo'ladi."""
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
    if domain.manosi(o.status) not in ("tayyor", "ishlab_chiqarish"):
        raise HTTPException(400, "Фақат тайёр (омбордаги) ёки цехдаги буюртмани топшириш мумкин "
                                 f"(ҳозир: {o.status})")

    qolgan = o.qty - (o.delivered_qty or 0)
    if qolgan <= 0:
        raise HTTPException(400, "Бу буюртманинг ҳаммаси аллақачон топширилган")

    # topshirilayotgan dona: berilmasa yoki 0 bo'lsa — qolgan hammasi
    beriladi = int(data.qty) if data.qty and data.qty > 0 else qolgan
    if beriladi > qolgan:
        raise HTTPException(400, f"Фақат {qolgan:,} дона қолган, {beriladi:,} топшириб бўлмайди"
                            .replace(",", " "))
    if data.paid_amount < 0:
        raise HTTPException(400, "Сумма манфий бўлмасин")
    if data.paid_amount > float(o.total) * 1.5:
        raise HTTPException(400, "Сумма буюртма жамисидан ҳаддан ташқари катта")

    # --- topshirish sanasi (o'tgan kunda berilgani keyin kiritilishi mumkin) ---
    kun = date.today()
    if data.sana:
        try:
            kun = datetime.strptime(data.sana.strip(), "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Сана формати нотўғри. Кўриниши: 2026-07-22")
        if kun > date.today():
            raise HTTPException(400, "Келажак санани кўрсатиб бўлмайди")
        yaratilgan = o.created_at.date() if o.created_at else None
        if yaratilgan and kun < yaratilgan:
            raise HTTPException(
                400, f"Буюртма {yaratilgan.strftime('%d.%m.%Y')} да яратилган — ундан "
                     f"олдинги санада мол берилган бўлиши мумкин эмас")

    o.delivered_qty = (o.delivered_qty or 0) + beriladi
    hammasi_berildi = o.delivered_qty >= o.qty
    if hammasi_berildi:
        o.status = domain.status_nomi("topshirildi")
        o.delivered_at = kun
    # qisman bo'lsa status o'zgarmaydi — yana kelib qolganini olib ketishi mumkin

    if data.paid_amount > 0:
        tolov = m.Payment(client_id=o.client_id, order_id=o.id,
                          amount=Decimal(str(data.paid_amount)), method=data.method,
                          paid_at=kun,
                          note=data.note or f"Буюртма #{o.id} учун")
        db.add(tolov)
        db.flush()
        ks.mijoz_tolovi(db, tolov, user.name)
        db.add(m.AuditLog(who=user.name, action="To'lov qabul qilindi",
                          detail=f"{o.client.company} · {data.paid_amount:,.0f} so'm · "
                                 f"{data.method}".replace(",", " ")))
    # Kechikib kiritilgan bo'lsa — audit yozuviga haqiqiy sana ham qo'shiladi,
    # aks holda tarixda faqat kiritilgan kun ko'rinib chalkashtiradi.
    # BOSH KITOB — parallel yozuv (eski hisob-kitob tegilmaydi).
    # Xato bo'lsa amal to'xtamaydi, faqat logga tushadi.
    from ..hisob import ulash as gl_ulash
    gl_ulash.buyurtma_topshirildi(db, o, Decimal(str(beriladi)), kun, user.name)
    if data.paid_amount > 0:
        gl_ulash.mijoz_tolovi(db, tolov, user.name)

    kech = kun != date.today()
    db.add(m.AuditLog(who=user.name, action="Mijozga topshirildi",
                      detail=f"Буюртма #{o.id} · {o.client.company} · {beriladi:,} дона"
                             f"{' (тўлиқ)' if hammasi_berildi else f' (қолди {o.qty - o.delivered_qty})'}"
                             f" · олинган пул: {data.paid_amount:,.0f}".replace(",", " ")
                             + (f" · берилган сана: {kun.strftime('%d.%m.%Y')} (кейин киритилди)" if kech else "")))
    db.commit()
    out = order_out(o)
    bal = s.client_balance(db, o.client_id)
    out["client_debt"] = float(bal["debt"])
    out["berildi"] = beriladi
    out["qolgan"] = o.qty - o.delivered_qty
    return out


class TopshirIn(BaseModel):
    """Bir nechta buyurtmani birga topshirish (yig'ib olib ketish)."""
    order_ids: list[int]
    paid_amount: float = 0
    method: str = "Naqd"
    note: str = ""


@router.post("/topshir-batch")
def deliver_batch(data: TopshirIn, db: Session = Depends(get_db),
                  user=Depends(require_roles("Menejer", "Buxgalter", "Sklad mudiri"))):
    """Mijozning bir nechta buyurtmasini birga topshirish — bitta to'lov bilan.
    Har biri to'liq topshiriladi (qisman emas). To'lov birinchi mijozga yoziladi."""
    if not data.order_ids:
        raise HTTPException(400, "Буюртма танланмади")
    orders = [db.get(m.Order, oid) for oid in data.order_ids]
    orders = [o for o in orders if o]
    if not orders:
        raise HTTPException(404, "Буюртмалар топилмади")
    client_ids = {o.client_id for o in orders}
    if len(client_ids) > 1:
        raise HTTPException(400, "Барча буюртмалар битта мижозники бўлиши керак")
    for o in orders:
        if domain.manosi(o.status) not in ("tayyor", "ishlab_chiqarish"):
            raise HTTPException(400, f"№{o.id} буюртма тайёр эмас (ҳозир: {o.status})")

    client_id = orders[0].client_id
    jami = sum(Decimal(str(o.qty)) - Decimal(str(o.delivered_qty or 0)) for o in orders)
    from ..hisob import ulash as gl_ulash
    for o in orders:
        qoldi = Decimal(str(o.qty)) - Decimal(str(o.delivered_qty or 0))
        o.delivered_qty = o.qty
        o.status = domain.status_nomi("topshirildi")
        o.delivered_at = date.today()
        # Bosh kitob — har buyurtma bo'yicha alohida provodka
        gl_ulash.buyurtma_topshirildi(db, o, qoldi, date.today(), user.name)
    if data.paid_amount > 0:
        tolov = m.Payment(client_id=client_id, order_id=orders[0].id,
                          amount=Decimal(str(data.paid_amount)), method=data.method,
                          note=data.note or f"{len(orders)} та буюртма учун")
        db.add(tolov)
        db.flush()
        ks.mijoz_tolovi(db, tolov, user.name)
    nomlar = ", ".join(f"#{o.id}" for o in orders)
    db.add(m.AuditLog(who=user.name, action="Mijozga topshirildi (yig'ib)",
                      detail=f"{orders[0].client.company} · {nomlar} · {jami:,} дона · "
                             f"пул: {data.paid_amount:,.0f}".replace(",", " ")))
    db.commit()
    bal = s.client_balance(db, client_id)
    return {"ok": True, "count": len(orders), "client_debt": float(bal["debt"])}


@router.post("/{oid}/accept-stamp")
def accept_stamp(oid: int, db: Session = Depends(get_db), user=Depends(get_user)):
    """Bot orqali 'Qabul qildim' — aktga elektron tasdiq stempeli (TZ 5.1)."""
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
    o.accepted_stamp = True
    db.add(m.AuditLog(who=o.client.company, action="Mijoz qabul qildi (bot)",
                      detail=f"Buyurtma #{o.id} elektron tasdiqlandi"))
    db.commit()
    return order_out(o)
