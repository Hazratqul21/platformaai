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
from ..domain import soha_yoz

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


class OrderIn(QuoteIn):
    client_id: int
    unit_price: float | None = None   # menejer qo'lda o'zgartirsa
    prepaid_percent: int = 0
    due_days: int = 15          # tayyorlash muddati
    payment_due_days: int = 15  # to'lov muddati
    note: str = ""


def validate_box(q: QuoteIn):
    if not (10 <= q.length_mm <= 5000 and 10 <= q.width_mm <= 5000 and 10 <= q.height_mm <= 5000):
        raise HTTPException(400, "Ўлчамлар 10–5000 мм оралиғида бўлсин")
    if not (1 <= q.qty <= 1_000_000):
        raise HTTPException(400, "Тираж 1 дан 1 000 000 гача бўлсин")
    if q.tur not in m.ORDER_TURLARI:
        raise HTTPException(400, f"Буюртма тури нотўғри. Мумкин: {', '.join(m.ORDER_TURLARI)}")
    if q.layers not in (1, 2, 3, 5):
        raise HTTPException(400, "Қават 1, 2, 3 ёки 5 бўлади")
    if not (q.grade or "").strip():
        raise HTTPException(400, "Қоғоз маркаси бўш бўлмасин")
    if not (0 <= q.colors <= 6):
        raise HTTPException(400, "Ранглар сони 0–6 оралиғида")


def tur_layers(tur: str) -> int:
    """Qavat soni turdan kelib chiqadi: gofra bo'lmagan materiallar bir qatlamli."""
    return m.TUR_LAYERS.get(tur, 1)


@router.post("/quote")
def make_quote(q: QuoteIn, db: Session = Depends(get_db), user=Depends(get_user)):
    """Smeta kalkulyatori. Menejer ekrani: tannarx + marja ham qaytariladi."""
    validate_box(q)
    category = "Standart"
    credit = None
    if q.client_id:
        c = db.get(m.Client, q.client_id)
        if c:
            category = c.category
    res = s.quote(db, q.length_mm, q.width_mm, q.height_mm, tur_layers(q.tur), q.grade,
                  q.colors, q.qty, category)
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
    delivered = o.delivered_qty or 0
    delivered_value = float(o.unit_price) * delivered
    paid_for_order = float(sum(Decimal(p.amount) for p in o.payments)) if o.payments else 0.0
    # Asosiy rasm sifatida ko'rsatiladigan fayl (pastdagi izohga qarang)
    asosiy_rasm = o.photo or ""
    if o.photos and asosiy_rasm not in [p.filename for p in o.photos]:
        asosiy_rasm = o.photos[0].filename
    return {
        "id": o.id, "client_id": o.client_id, "company": o.client.company,
        "product_name": o.product_name,
        "size": f"{o.length_mm}×{o.width_mm}×{o.height_mm}",
        "length_mm": o.length_mm, "width_mm": o.width_mm, "height_mm": o.height_mm,
        "tur": o.tur or f"{o.layers} слой",
        # Asosiy rasm: eski o.photo maydonidagi fayl endi mavjud bo'lmasligi mumkin
        # (fayl o'chirilgan/ko'chirilgan). Shunda mavjud rasmlardan birinchisini
        # ko'rsatamiz — aks holda buzuq rasm belgisi va 404 chiqadi.
        "photo": asosiy_rasm,
        "photo_url": f"/uploads/{asosiy_rasm}" if asosiy_rasm else None,
        "photos": [{"filename": p.filename, "url": f"/uploads/{p.filename}"} for p in o.photos]
                  or ([{"filename": asosiy_rasm, "url": f"/uploads/{asosiy_rasm}"}] if asosiy_rasm else []),
        "layers": o.layers, "grade": o.grade, "colors": o.colors, "is_offset": o.is_offset, "qty": o.qty,
        "delivered_qty": delivered, "qolgan_qty": o.qty - delivered,
        # topshirilgan mol qiymati vs shu buyurtmaga bog'langan to'lov
        "delivered_value": delivered_value, "paid_for_order": paid_for_order,
        "tolanmadi": delivered > 0 and paid_for_order + 1 < delivered_value,
        "m2_per_box": float(o.m2_per_box), "unit_cost": float(o.unit_cost),
        "unit_price": float(o.unit_price), "total": float(o.total),
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
        return o.status == m.ST_BEKOR or \
            (o.status == m.ST_YETKAZILDI and (o.delivered_qty or 0) >= o.qty)

    if archive:
        rows = [o for o in rows if tugallangan(o)]
    else:
        rows = [o for o in rows if not tugallangan(o)]
    return [order_out(o) for o in rows[:300]]


@router.post("")
def create_order(data: OrderIn, db: Session = Depends(get_db),
                 user=Depends(require_roles("Menejer"))):
    validate_box(data)
    c = db.get(m.Client, data.client_id)
    if not c:
        raise HTTPException(404, "Мижоз топилмади")
    if data.unit_price is not None and data.unit_price <= 0:
        raise HTTPException(400, "Нарх 0 дан катта бўлсин")
    layers = tur_layers(data.tur)
    res = s.quote(db, data.length_mm, data.width_mm, data.height_mm, layers,
                  data.grade, data.colors, data.qty, c.category)
    unit_price = Decimal(str(data.unit_price)) if data.unit_price else res["unit_price"]
    total = (unit_price * data.qty).quantize(Decimal("0.01"))
    check = s.credit_check(db, c, total)
    if check["blocked"]:
        reason = "qora ro'yxatda" if check["blacklisted"] else "kredit limitidan oshadi"
        raise HTTPException(409, f"Buyurtma bloklandi: mijoz {reason}. Rahbar tasdig'i kerak.")
    o = m.Order(
        client_id=c.id, length_mm=data.length_mm, width_mm=data.width_mm,
        height_mm=data.height_mm, tur=data.tur, layers=layers, grade=data.grade,
        colors=data.colors, is_offset=(data.tur == "Офсет"), qty=data.qty,
        m2_per_box=res["m2_per_box"],
        unit_cost=res["unit_cost"], unit_price=unit_price, total=total,
        prepaid_percent=data.prepaid_percent, note=data.note,
        product_name=data.product_name,
        due_date=date.today() + timedelta(days=data.due_days),
        payment_due_date=date.today() + timedelta(days=data.payment_due_days),
    )
    db.add(o)
    # flush ustun standart qiymatlarini (tur, layers...) qo'yadi — soha_yoz
    # ulardan o'qiydi, shuning uchun flush'dan KEYIN chaqirilishi shart.
    db.flush()
    soha_yoz(o)   # 2-qadam: ustunga ham, attributes ga ham
    db.add(m.AuditLog(who=user.name, action="Buyurtma yaratildi",
                      detail=f"{c.company} · {data.qty} dona · {float(total):,.0f} so'm"))
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
    product_name: str | None = None
    length_mm: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    tur: str | None = None
    grade: str | None = None
    colors: int | None = None
    qty: int | None = None
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
    if o.status in (m.ST_YETKAZILDI, m.ST_BEKOR):
        raise HTTPException(400, "Етказилган ёки бекор қилинган буюртмани таҳрирлаб бўлмайди")

    # o'lchov/tur/marka o'zgarsa — smetani qayta hisoblaymiz
    tur = data.tur if data.tur is not None else (o.tur or f"{o.layers} слой")
    if data.tur is not None and tur not in m.ORDER_TURLARI:
        raise HTTPException(400, f"Буюртма тури нотўғри. Мумкин: {', '.join(m.ORDER_TURLARI)}")
    L = data.length_mm if data.length_mm is not None else o.length_mm
    W = data.width_mm if data.width_mm is not None else o.width_mm
    H = data.height_mm if data.height_mm is not None else o.height_mm
    grade = (data.grade if data.grade is not None else o.grade)
    colors = data.colors if data.colors is not None else o.colors
    qty = data.qty if data.qty is not None else o.qty
    if not (10 <= L <= 5000 and 10 <= W <= 5000 and 10 <= H <= 5000):
        raise HTTPException(400, "Ўлчамлар 10–5000 мм оралиғида бўлсин")
    if not (1 <= qty <= 1_000_000):
        raise HTTPException(400, "Тираж 1 дан 1 000 000 гача бўлсин")
    if not (grade or "").strip():
        raise HTTPException(400, "Қоғоз маркаси бўш бўлмасин")
    if qty < (o.delivered_qty or 0):
        raise HTTPException(400, f"Тираж топширилган миқдордан ({o.delivered_qty}) кам бўлмасин")

    layers = tur_layers(tur)
    res = s.quote(db, L, W, H, layers, grade, colors, qty, o.client.category)

    o.product_name = data.product_name if data.product_name is not None else o.product_name
    o.length_mm, o.width_mm, o.height_mm = L, W, H
    o.tur, o.layers, o.grade, o.colors, o.qty = tur, layers, grade, colors, qty
    o.is_offset = (tur == "Офсет")
    o.m2_per_box = res["m2_per_box"]
    o.unit_cost = res["unit_cost"]
    o.unit_price = Decimal(str(data.unit_price)) if data.unit_price else res["unit_price"]
    o.total = (o.unit_price * qty).quantize(Decimal("0.01"))
    soha_yoz(o)   # 2-qadam: tahrirda ham ikkala joy yangilanadi
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
    tugagan = (o.delivered_qty or 0) >= o.qty and o.status in (m.ST_OMBORDA, m.ST_SEXDA)

    ogoh = None
    if tugagan:
        ogoh = (f"Тираж топширилган миқдорга ({o.delivered_qty:,} дона) тенглашди. "
                f"Буюртмани ёпиш учун «Якунлаш» тугмасини босинг — шунда архивга ўтади."
                ).replace(",", " ")
    elif o.status == m.ST_SEXDA:
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
    data = OrderIn(
        client_id=old.client_id, length_mm=old.length_mm, width_mm=old.width_mm,
        height_mm=old.height_mm, tur=old.tur or f"{old.layers} слой", layers=old.layers,
        grade=old.grade, product_name=old.product_name,
        colors=old.colors, qty=qty or old.qty, note=f"Takroriy (#{old.id} asosida)",
    )
    return create_order(data, db, user)


VALID_FLOW = {
    m.ST_KUTISHDA: [m.ST_SEXDA, m.ST_MUZOKARA, m.ST_BEKOR],
    m.ST_MUZOKARA: [m.ST_KUTISHDA, m.ST_SEXDA, m.ST_BEKOR],
    m.ST_SEXDA: [m.ST_OMBORDA, m.ST_BEKOR],
    m.ST_OMBORDA: [m.ST_YETKAZILDI],
    m.ST_YETKAZILDI: [],
    m.ST_BEKOR: [],
}

ROLE_PERMISSIONS = {
    "Menejer": [m.ST_BEKOR, m.ST_KUTISHDA, m.ST_MUZOKARA, m.ST_SEXDA],
    "Sex boshlig'i": [m.ST_OMBORDA, m.ST_BEKOR],
    "Sklad mudiri": [m.ST_YETKAZILDI]
}


@router.get("/{oid}/check-stock")
def check_stock(oid: int, db: Session = Depends(get_db), user=Depends(get_user)):
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
    
    brak = Decimal("1") + s.dset(db, "brak_percent") / 100
    need_m2 = (Decimal(o.m2_per_box) * o.qty * brak).quantize(Decimal("0.0001"))
    
    # fifo_writeoff simulyatsiyasi: har lotning o'z grammaji bilan m2->kg o'giriladi
    remaining_m2 = need_m2
    lots = db.query(m.RawLot).filter(m.RawLot.grade == o.grade, m.RawLot.remaining_kg > 0).order_by(m.RawLot.received_at, m.RawLot.id).all()
    
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

@router.post("/{oid}/status")
def set_status(oid: int, status: str, db: Session = Depends(get_db), user=Depends(get_user)):
    o = db.get(m.Order, oid)
    if not o:
        raise HTTPException(404, "Буюртма топилмади")
        
    if user.role != "Rahbar":
        allowed_statuses = ROLE_PERMISSIONS.get(user.role, [])
        if status not in allowed_statuses:
            raise HTTPException(403, f"{user.role} roliga '{status}' maqomini o'rnatish ruxsat etilmaydi")

    if status not in VALID_FLOW.get(o.status, []):
        raise HTTPException(400, f"'{o.status}' dan '{status}' ga o'tib bo'lmaydi")
        
    if status == m.ST_BEKOR and o.status == m.ST_SEXDA:
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
    if status == m.ST_SEXDA:
        # ishlab chiqarishga berilganda xomashyo FIFO bo'yicha yechiladi (brak bilan)
        brak = Decimal("1") + s.dset(db, "brak_percent") / 100
        need = (Decimal(o.m2_per_box) * o.qty * brak).quantize(Decimal("0.0001"))
        try:
            s.fifo_writeoff(db, o.grade, need, order_id=o.id,
                            note=f"Buyurtma #{o.id} spisaniya (5% brak bilan)")
        except ValueError as e:
            raise HTTPException(409, str(e))
    if status == m.ST_YETKAZILDI:
        o.delivered_at = date.today()
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
    if o.status == m.ST_BEKOR:
        raise HTTPException(400, "Бекор қилинган буюртмани якунлаб бўлмайди")
    if berildi >= o.qty:
        # Hammasi berilgan, lekin status yangilanmay qolgan (masalan tiraj keyin
        # tuzatilgan) — bunda faqat statusni yopamiz, miqdorga tegmaymiz.
        if o.status == m.ST_YETKAZILDI:
            raise HTTPException(400, "Буюртма аллақачон якунланган")
        o.status = m.ST_YETKAZILDI
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
    o.status = m.ST_YETKAZILDI
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

    upload_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
    upload_dir.mkdir(exist_ok=True)
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
    if o.status not in (m.ST_OMBORDA, m.ST_SEXDA):
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
        o.status = m.ST_YETKAZILDI
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
    kech = kun != date.today()
    db.add(m.AuditLog(who=user.name, action="Mijozga topshirildi",
                      detail=f"Буюртма #{o.id} · {o.client.company} · {beriladi:,} дона"
                             f"{' (тўлиқ)' if hammasi_berildi else f' (қолди {o.qty - o.delivered_qty:,})'}"
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
        if o.status not in (m.ST_OMBORDA, m.ST_SEXDA):
            raise HTTPException(400, f"№{o.id} буюртма тайёр эмас (ҳозир: {o.status})")

    client_id = orders[0].client_id
    jami = sum(int(o.qty - (o.delivered_qty or 0)) for o in orders)
    for o in orders:
        o.delivered_qty = o.qty
        o.status = m.ST_YETKAZILDI
        o.delivered_at = date.today()
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
