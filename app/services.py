"""Biznes-logika: smeta, FIFO spisaniya, tannarx, balanslar, oylik, cash flow."""
import ast
import operator
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func
from sqlalchemy.orm import Session
from . import models as m
from . import domain

try:
    from zoneinfo import ZoneInfo
    TOSHKENT = ZoneInfo("Asia/Tashkent")
except Exception:                      # zoneinfo bazasi yo'q bo'lsa — qat'iy UTC+5
    TOSHKENT = timezone(timedelta(hours=5))


def mahalliy_vaqt(dt: datetime | None) -> datetime | None:
    """Bazada UTC saqlangan vaqtni Toshkent vaqtiga o'giradi.

    Audit jurnali va boshqa vaqt maydonlari `datetime.utcnow` bilan yoziladi
    (bu to'g'ri — server ko'chsa ham vaqt buzilmaydi). Foydalanuvchiga esa
    Toshkent vaqti ko'rsatilishi kerak, aks holda hamma soat 5 soat orqada
    ko'rinadi.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TOSHKENT)

TWO = Decimal("0.01")

# ============================================================
#  Xavfsiz formula dvigateli (poligrafiya sebestoyimost uchun)
#  Admin formulani o'zgartira oladi: masalan "x*y*g*q*n"
# ============================================================
_ALLOWED_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
}
# Vergul ATAYLAB ruxsat etilmagan: "3,3" Python'da ikkita son (tuple) bo'lib qoladi
# va formula jimgina ishlamay qo'yadi. Kasr son nuqta bilan yoziladi: 3.3
_VAR_RE = re.compile(r"^[a-zA-Z0-9_+\-*/().\s]+$")

# Formulalarda ishlatish mumkin bo'lgan harflar (foydalanuvchiga ham shu ko'rsatiladi)
FORMULA_VARS = {
    "formula_m2": {
        "l": "uzunlik, mm", "w": "kenglik, mm", "h": "balandlik, mm",
    },
    "formula_sebestoimost": {
        "m": "1 quti m²", "p": "qog'oz narxi, so'm/m²", "b": "brak koeffitsienti (1.05)",
        "l": "ish haqi, so'm/dona", "c": "bosma ranglar soni", "k": "1 rang narxi, so'm",
    },
}


def safe_formula_check(expr: str) -> bool:
    """Formulada faqat o'zgaruvchi/raqam/amal borligini tekshiradi."""
    if not expr or not _VAR_RE.match(expr):
        return False
    try:
        ast.parse(expr, mode="eval")
        return True
    except SyntaxError:
        return False


def _eval_node(node, vars_, strict=False):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, vars_, strict)
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in vars_:
            # noma'lum harfni jimgina 0 qilib yubormaymiz — butun formula
            # noto'g'ri hisoblanib ketadi va hech kim sezmaydi
            raise ValueError(f"'{node.id}' — noma'lum harf")
        return float(vars_[node.id])
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.left, vars_, strict),
                                           _eval_node(node.right, vars_, strict))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_eval_node(node.operand, vars_, strict))
    if isinstance(node, ast.Tuple):
        raise ValueError("Kasr son nuqta bilan yoziladi (3.3), vergul bilan emas (3,3)")
    raise ValueError("Formulada ruxsat etilmagan amal")


def eval_formula(expr: str, **vars_) -> float:
    """Formulani xavfsiz hisoblaydi. Masalan eval_formula('x*y*n', x=0.5, y=0.7, n=1000)."""
    if not safe_formula_check(expr):
        raise ValueError("Formula noto'g'ri")
    try:
        return float(_eval_node(ast.parse(expr, mode="eval"), vars_))
    except ZeroDivisionError:
        return 0.0


def formula_xato(expr: str, key: str) -> str | None:
    """Formulani saqlashdan oldin tekshiradi. Xato bo'lsa — tushunarli xabar,
    to'g'ri bo'lsa — None. Shunday qilib noto'g'ri formula bazaga umuman tushmaydi."""
    expr = (expr or "").strip()
    if not expr:
        return "Формула бўш"
    if "," in expr:
        return "Каср сон нуқта билан ёзилади: 3.3 (вергул билан эмас: 3,3)"
    if not _VAR_RE.match(expr):
        yomon = sorted(set(re.findall(r"[^a-zA-Z0-9_+\-*/().\s]", expr)))
        return f"Рухсат этилмаган белги: {' '.join(yomon)}"
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return "Формула нотўғри ёзилган (қавслар тенг эмасми?)"

    ruxsat = FORMULA_VARS.get(key, {})
    ishlatilgan = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    notanish = sorted(ishlatilgan - set(ruxsat))
    if notanish:
        royxat = ", ".join(f"{h} — {t}" for h, t in ruxsat.items())
        return (f"'{', '.join(notanish)}' — номаълум ҳарф. "
                f"Фақат шулар ишлатилади: {royxat}. "
                f"Катта-кичик ҳарфга эътибор беринг (L эмас, l).")
    # namuna qiymatlar bilan hisoblab ko'ramiz
    namuna = {"l": 400, "w": 300, "h": 250, "m": 0.8, "p": 1700, "b": 1.05,
              "c": 1, "k": 120}
    try:
        natija = _eval_node(tree, {v: namuna.get(v, 1) for v in ruxsat})
    except ValueError as e:
        return str(e)
    except ZeroDivisionError:
        return "Формула нолга бўлиняпти"
    except Exception:
        return "Формулани ҳисоблаб бўлмади"
    if natija < 0:
        return f"Формула манфий сон беряпти ({natija:.2f}) — текширинг"
    return None
GLUE_FLAP_MM = 40  # yelimlash qanoti (FEFCO 0201)

DEFAULT_SETTINGS = {
    "brak_percent": "5",            # texnologik brak %
    "color_cost_per_box": "120",    # flekso 1 rang uchun so'm/dona
    "labor_per_box": "150",         # 1 qutiga o'rtacha ish haqi so'm
    "margin_vip": "18",             # narx ustamasi % (toifa bo'yicha)
    "margin_standart": "25",
    "margin_yangi": "30",
    "credit_mode": "warn",          # warn | block — limit oshganda
    "min_stock_days": "4",          # tugashiga necha kun qolganda ogohlantirish
    "bonus_low_brak": "5",          # brak past bo'lsa bonus %
    "formula_m2": "((l+w)*2+40)*(h+w)/1000000",
    "formula_sebestoimost": "m*p*b+l+c*k",
    "paper_grades": "K1,K2,T-22,T-23",      # Qog'oz markalari (vergul bilan)

    # --- QQS (НДС) ---
    # rejim:  yoq     — korxona QQS to'lovchisi emas (ko'p kichik biznes)
    #         ustiga  — kiritilgan narx QQSSIZ, QQS ustiga qo'shiladi
    #         ichida  — kiritilgan narx QQS BILAN, ichidan ajratiladi
    # Standart "yoq": QQS to'lovchi bo'lmagan korxonada hujjatda QQS
    # qatori umuman chiqmasligi kerak.
    "qqs_rejimi": "yoq",
    "qqs_stavka": "12",   # O'zbekiston, 2023 yildan 12%

    # --- Hujjat rekvizitlari (akt, nakladnoy, sverka shapkasi uchun) ---
    # Ikki firma alohida: mijozning firmasi bo'yicha avtomat tanlanadi.
    # Bo'sh qoldirilsa — hujjatda o'sha qator umuman chiqmaydi (buzilmaydi).
    "rekvizit_firma1_kalit": "интран",      # qaysi firmaga tegishli (mijoz.firm bilan solishtiriladi)
    "rekvizit_firma1_nomi": "",
    "rekvizit_firma1_stir": "",
    "rekvizit_firma1_manzil": "",
    "rekvizit_firma1_tel": "",
    "rekvizit_firma1_bank": "",
    "rekvizit_firma1_hisob": "",
    "rekvizit_firma1_rahbar": "",

    "rekvizit_firma2_kalit": "макс стар",
    "rekvizit_firma2_nomi": "",
    "rekvizit_firma2_stir": "",
    "rekvizit_firma2_manzil": "",
    "rekvizit_firma2_tel": "",
    "rekvizit_firma2_bank": "",
    "rekvizit_firma2_hisob": "",
    "rekvizit_firma2_rahbar": "",

    "hujjat_footer": "",   # hujjat pastidagi qo'shimcha yozuv (bo'sh = hech narsa)
}


def rekvizit(db: Session, firm: str | None) -> dict:
    """Mijoz firmasiga mos hujjat rekvizitlarini qaytaradi.

    Firma topilmasa yoki bo'sh bo'lsa — birinchi firma rekviziti olinadi.
    Bo'sh maydonlar hujjatda chiqmaydi (shuning uchun to'ldirilmagan bo'lsa ham
    hujjat avvalgidek ishlayveradi).
    """
    nom = (firm or "").strip().lower()
    tanlangan = "firma1"
    for idx in ("firma1", "firma2"):
        kalit = get_setting(db, f"rekvizit_{idx}_kalit").strip().lower()
        if kalit and nom and (kalit == nom or kalit in nom or nom in kalit):
            tanlangan = idx
            break
    out = {}
    for maydon in ("nomi", "stir", "manzil", "tel", "bank", "hisob", "rahbar"):
        out[maydon] = get_setting(db, f"rekvizit_{tanlangan}_{maydon}").strip()
    out["footer"] = get_setting(db, "hujjat_footer").strip()
    return out


def get_setting(db: Session, key: str) -> str:
    row = db.get(m.Setting, key)
    return row.value if row else DEFAULT_SETTINGS.get(key, "0")


def dset(db: Session, key: str) -> Decimal:
    return Decimal(get_setting(db, key))


# ---------------- Smeta kalkulyatori (TZ 1.2) ----------------

def m2_per_box(db: Session, length_mm: int, width_mm: int, height_mm: int) -> Decimal:
    """Quti zagotovkasi m2 si (sozlamalardagi formula bo'yicha)."""
    val, _ = m2_per_box_ogoh(db, length_mm, width_mm, height_mm)
    return val


def m2_per_box_ogoh(db: Session, length_mm: int, width_mm: int,
                    height_mm: int) -> tuple[Decimal, str | None]:
    """m² va ogohlantirish. Sozlamadagi formula ishlamasa zaxira (FEFCO) ishlatiladi,
    lekin bu haqda ogohlantirish qaytariladi — jimgina o'tib ketmasin."""
    expr = get_setting(db, "formula_m2")
    try:
        val = eval_formula(expr, l=length_mm, w=width_mm, h=height_mm)
        if val > 0:
            return Decimal(str(val)).quantize(Decimal("0.0001")), None
        xato = "формула 0 ёки манфий сон беряпти"
    except Exception as e:
        xato = str(e)
    # Zaxira: standart FEFCO 0201
    blank_l = Decimal(2 * (length_mm + width_mm) + GLUE_FLAP_MM)
    blank_w = Decimal(height_mm + width_mm)
    zaxira = (blank_l * blank_w / Decimal(1_000_000)).quantize(Decimal("0.0001"))
    return zaxira, (f"Созламалардаги м² формулангиз ишламаяпти ({xato}). "
                    f"Ҳозирча стандарт формула ишлатилди. Созламалар > "
                    f"Тизим созламалари бўлимида тузатинг.")


def _grammaj_raqami(text: str) -> Decimal | None:
    """'270 гр', '140гр', '115' kabi yozuvdan grammaj raqamini ajratadi."""
    if not text:
        return None
    raqam = re.search(r"\d+", str(text))
    if not raqam:
        return None
    g = Decimal(raqam.group())
    return g if 1 <= g <= 2000 else None


# Qog'oz nomi buyurtmada kirillcha, omborda lotincha yozilgan bo'lishi mumkin
# ("Хитой 140гр" va "Xitoy" bitta qog'oz). Solishtirishdan oldin ikkisi ham
# bitta yozuvga keltiriladi.
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "",
    "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o", "қ": "q",
    "ғ": "g", "ҳ": "h",
}


def _norm(text: str) -> str:
    """Nomni solishtirish uchun bir ko'rinishga keltiradi: kichik harf,
    kirill -> lotin, ortiqcha bo'shliqsiz. «Хитой» va «Xitoy» teng bo'ladi."""
    s = (text or "").strip().lower()
    return "".join(_TRANSLIT.get(ch, ch) for ch in s).replace(" ", "")


def _qogoz_kaliti(text: str) -> tuple[str, Decimal | None]:
    """Qog'oz nomini solishtirish kalitiga aylantiradi.

    Qaytaradi: (raqamsiz asos nomi, grammaj). Masalan:
      "Хитой 140гр" -> ("xitoy", 140)
      "Silver pak"  -> ("silverpak", None)
    """
    xom = (text or "").strip().lower()
    grammaj = _grammaj_raqami(xom)
    if grammaj is not None and not (30 <= grammaj <= 2000):
        grammaj = None            # o'lcham emas, tasodifiy raqam
    # Raqam va uning ortidan kelgan o'lchov birligi olib tashlanadi:
    # "Хитой 140гр" va "Xitoy" bitta qog'oz. Birlik faqat raqamdan keyin
    # o'chiriladi — aks holda nomning o'zidagi harflar ham buzilardi.
    xom = re.sub(r"\d+\s*(?:гр|гм|г/м2|г|gr|gsm|g/m2|g)?\.?", " ", xom)
    xom = "".join(_TRANSLIT.get(ch, ch) for ch in xom)
    asos = re.sub(r"[^a-z]+", "", xom)
    return asos, grammaj


def material_narxi_m2(db: Session, grade: str) -> Decimal:
    """Xarid (zakup) qilingan qog'ozning 1 m² narxi: so'm/kg × grammaj ÷ 1000.

    Nom aynan mos kelishi shart (kirill/lotin va "гр" farqi hisobga olinadi).
    Taxminiy o'xshashlik bo'yicha moslashtirilmaydi: "K1" ni "Silver pak"ka
    bog'lab qo'yish tannarxni butunlay yolg'on qilib yuboradi.
    """
    narx, _ = material_narxi_m2_manba(db, grade)
    return narx


def material_narxi_m2_manba(db: Session, grade: str) -> tuple[Decimal, str]:
    """material_narxi_m2 bilan bir xil, lekin narx qaysi materialdan
    olinganini ham qaytaradi (foydalanuvchiga ko'rsatish uchun)."""
    asos, grammaj = _qogoz_kaliti(grade)
    if not asos:
        return Decimal("0"), ""
    # Bir xil qog'oz ikki yozuv bo'lib qolgan bo'lishi mumkin ("Ekonom" va
    # "Ekonom 140гр"). Tannarx uchun eng oxirgi xarid narxi to'g'ri o'lchov,
    # shuning uchun oxirgi xarid sanasi bo'yicha tanlanadi.
    oxirgi_xarid = dict(
        db.query(m.Purchase.material_id, func.max(m.Purchase.purchased_at))
        .group_by(m.Purchase.material_id).all())
    nomzod = []
    for mat in db.query(m.Material).all():
        if not mat.last_price or Decimal(mat.last_price) <= 0:
            continue
        if (mat.unit or "kg").lower() != "kg":
            continue          # dona/rulon uchun m² narxini hisoblab bo'lmaydi
        m_asos, m_grammaj = _qogoz_kaliti(mat.name)
        m_grammaj = _grammaj_raqami(mat.grammaj) or m_grammaj
        if not m_grammaj or m_asos != asos:
            continue
        # grammaji aynan mos kelgani ustun; ko'rsatilmagan bo'lsa ayni paytda
        # eng ko'p qoldig'i bor grammaj — sex aslida shu qog'oz bilan ishlayapti
        aniq = 1 if (grammaj is not None and m_grammaj == grammaj) else 0
        sana = oxirgi_xarid.get(mat.id) or date.min
        nomzod.append((aniq, sana, float(mat.stock_qty or 0), mat, m_grammaj))
    if not nomzod:
        return Decimal("0"), ""
    # grammaj ko'rsatilgan, lekin o'sha grammajdagi material yo'q — narx berilmaydi,
    # chunki 140гр o'rniga 300гр narxini olish tannarxni ikki barobar buzadi
    if grammaj is not None and not any(a for a, *_ in nomzod):
        return Decimal("0"), ""
    nomzod.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    _, _, _, mat, m_grammaj = nomzod[0]
    narx = (Decimal(mat.last_price) * m_grammaj / Decimal("1000")).quantize(TWO, ROUND_HALF_UP)
    return narx, f"{mat.name} ({m_grammaj:.0f} гр, {float(mat.last_price):,.0f} со'м/кг)".replace(",", " ")


def current_material_price(db: Session, grade: str, layers: int = 1) -> Decimal:
    """Joriy xomashyo narxi (1 m² uchun)."""
    narx, _, _ = qogoz_narxi(db, grade)
    return narx


def qogoz_narxi(db: Session, grade: str) -> tuple[Decimal, str, str | None]:
    """Qog'ozning 1 m² narxi, narx qaysi manbadan olingani va ogohlantirish.

    1) Ombordagi ochiq partiya (FIFO) — narxi bor bo'lsa;
    2) Bo'lmasa — o'sha markadagi oxirgi ombor kirimi;
    3) Bo'lmasa — zakupdagi shu nomli qog'ozning oxirgi xarid narxi.
    Narxi 0 bo'lgan partiyalar hisobga olinmaydi (masalan avtomatik 'QARZ' loti),
    aks holda tannarx qog'ozsiz — noto'g'ri chiqadi.

    Narx topilmasa — jimgina 0 qaytarmaydi, ogohlantirish beradi: aks holda
    tannarx faqat ish haqi va bosmadan iborat bo'lib, foyda soxta ko'rinadi.
    """
    asos, _ = _qogoz_kaliti(grade)
    lots = [lt for lt in db.query(m.RawLot).all()
            if _qogoz_kaliti(lt.grade)[0] == asos and Decimal(lt.price_per_kg or 0) > 0]

    ochiq = sorted((lt for lt in lots if Decimal(lt.remaining_kg or 0) > 0),
                   key=lambda lt: (lt.received_at, lt.id))
    if ochiq:
        lot = ochiq[0]
        narx = (Decimal(lot.price_per_kg) * Decimal(lot.grammage) / Decimal("1000"))
        return narx.quantize(TWO, ROUND_HALF_UP), f"омбор партияси {lot.lot_no}", None

    if lots:
        lot = max(lots, key=lambda lt: (lt.received_at, lt.id))
        narx = (Decimal(lot.price_per_kg) * Decimal(lot.grammage) / Decimal("1000"))
        return (narx.quantize(TWO, ROUND_HALF_UP),
                f"омбордаги охирги кирим {lot.lot_no}", None)

    narx, manba = material_narxi_m2_manba(db, grade)
    if narx > 0:
        return narx, f"харид нархи: {manba}", None

    nom = (grade or "").strip() or "кўрсатилмаган"
    return Decimal("0"), "", (
        f"«{nom}» қоғозининг нархи топилмади — таннархга қоғоз кирмади "
        f"(фақат иш ҳақи ва бўёқ ҳисобланди). Хомашё нархи Омбор ёки Харид "
        f"бўлимида шу ном билан (грамажи ҳам) киритилиши керак.")


def unit_cost(db: Session, mpb: Decimal, grade: str, layers: int, colors: int) -> dict:
    """Tannarx hisobi: Sozlamalardagi formula bo'yicha."""
    price, narx_manba, narx_ogoh = qogoz_narxi(db, grade)
    brak_factor = Decimal("1") + dset(db, "brak_percent") / 100
    labor = dset(db, "labor_per_box")
    printing = dset(db, "color_cost_per_box") * colors
    material = (mpb * price * brak_factor).quantize(TWO, ROUND_HALF_UP)
    
    expr = get_setting(db, "formula_sebestoimost")
    try:
        # m = m2_per_box, p = material_price_m2, b = brak_factor, l = labor, c = colors, k = color_cost_per_box
        val = eval_formula(
            expr, 
            m=float(mpb), 
            p=float(price), 
            b=float(brak_factor), 
            l=float(labor), 
            c=float(colors), 
            k=float(dset(db, "color_cost_per_box"))
        )
        total = Decimal(str(val)).quantize(TWO, ROUND_HALF_UP)
    except Exception:
        # Fallback (eski hardcode formula)
        total = (material + labor + printing).quantize(TWO, ROUND_HALF_UP)

    return {
        "material_price_m2": price, "material": material,
        "labor": labor, "printing": printing, "unit_cost": total,
        "narx_manba": narx_manba, "narx_ogoh": narx_ogoh,
    }


def quote(db: Session, length_mm, width_mm, height_mm, layers, grade, colors, qty, category="Standart") -> dict:
    # `qty` Decimal ga o'giriladi: chaqiruvchi float bersa quyida
    # `Decimal * float` TypeError bo'lardi. Miqdor endi kasrli ham
    # bo'lishi mumkin (profil `olchov.kasrli`), shuning uchun bu yo'l
    # haqiqatan ochiq — himoyani chaqiruvchiga qoldirib bo'lmaydi.
    qty = Decimal(str(qty))
    mpb, ogoh = m2_per_box_ogoh(db, length_mm, width_mm, height_mm)
    cost = unit_cost(db, mpb, grade, layers, colors)
    margin_key = {"VIP": "margin_vip", "Standart": "margin_standart"}.get(category, "margin_yangi")
    margin = dset(db, margin_key)
    price = (cost["unit_cost"] * (1 + margin / 100)).quantize(TWO, ROUND_HALF_UP)
    total = (price * qty).quantize(TWO, ROUND_HALF_UP)
    need_m2 = (mpb * qty * (Decimal("1") + dset(db, "brak_percent") / 100)).quantize(Decimal("0.01"))
    stock = raw_stock_m2_for_grade(db, grade)
    return {
        "m2_per_box": mpb, "need_m2_total": need_m2, "stock_m2": stock,
        "enough_material": stock >= need_m2,
        **cost,
        "margin_percent": margin, "unit_price": price, "total": total,
        "profit": (total - cost["unit_cost"] * qty).quantize(TWO),
        "formula_ogoh": ogoh,      # formula ishlamasa — ogohlantirish
    }


# ---------------- Ombor / FIFO (TZ 2) ----------------

def raw_stock_for(db: Session, grade: str, grammage: int) -> Decimal:
    """Ombordagi xomashyo qoldig'i (kg) — marka + grammaj bo'yicha."""
    return (db.query(func.coalesce(func.sum(m.RawLot.remaining_kg), 0))
            .filter(m.RawLot.grade == grade, m.RawLot.grammage == grammage)
            .scalar())


def raw_stock_m2_for_grade(db: Session, grade: str) -> Decimal:
    """Marka bo'yicha jami qoldiq m² da — har lot o'z grammaji bilan o'giriladi."""
    total = Decimal("0")
    for lot in db.query(m.RawLot).filter(m.RawLot.grade == grade,
                                         m.RawLot.remaining_kg > 0).all():
        g = Decimal(lot.grammage or 120)
        if g > 0:
            total += Decimal(lot.remaining_kg) * Decimal("1000") / g
    return total.quantize(Decimal("0.01"))


def fifo_writeoff(db: Session, grade: str, need_m2: Decimal, order_id=None, note="") -> Decimal:
    """FIFO spisaniya. Brak allaqachon need_m2 ichida. M2 larni Kg ga (lot grammaji orqali) o'girib yechiladi."""
    remaining_m2 = need_m2
    total_cost = Decimal("0")
    lots = (
        db.query(m.RawLot)
        .filter(m.RawLot.grade == grade, m.RawLot.remaining_kg > 0)
        .order_by(m.RawLot.received_at, m.RawLot.id)
        .all()
    )
    for lot in lots:
        if remaining_m2 <= 0:
            break
        
        # Ushbu lot uchun 1 m2 necha kg ekanligini topamiz
        kg_per_m2 = Decimal(lot.grammage) / Decimal("1000")
        need_kg_for_lot = remaining_m2 * kg_per_m2
        
        take_kg = min(Decimal(lot.remaining_kg), need_kg_for_lot)
        if lot == lots[-1] and take_kg < need_kg_for_lot:
            # Agar oxirgi lot bo'lsa va yetmasa, qolgan hamma qismini (minusga kiritib) olamiz
            take_kg = need_kg_for_lot

        lot.remaining_kg = Decimal(lot.remaining_kg) - take_kg
        cost = (take_kg * Decimal(lot.price_per_kg)).quantize(TWO, ROUND_HALF_UP)
        db.add(m.StockMove(lot_id=lot.id, order_id=order_id, kg=take_kg, cost=cost, note=note))
        total_cost += cost
        
        # Olingan Kg qancha M2 ga to'g'ri kelganini hisoblab remaining_m2 dan ayiramiz
        m2_covered = take_kg / kg_per_m2
        remaining_m2 -= m2_covered

    if remaining_m2 > Decimal("0.001"):
        # Omborda umuman ijobiy qoldig'i bor lot yo'q. Istalgan bitta lotni topamiz yoki yangi minus lot yaratamiz.
        any_lot = db.query(m.RawLot).filter(m.RawLot.grade == grade).first()
        if not any_lot:
            supp = db.query(m.Supplier).first()
            if not supp:
                # DIQQAT: ilgari bu yerda `type="xomashyo"` yozilgan edi,
                # lekin modelda bunday maydon yo'q (u `kind`) — natijada
                # TypeError va 500. Bu yo'l faqat OMBOR BUTUNLAY BO'SH
                # bo'lganda ishlaydi, ya'ni aynan YANGI MIJOZDA. Eski
                # tizimda ombor hech qachon bo'sh bo'lmagani uchun xato
                # bilinmagan. `kind` standart qiymatida qoldiriladi.
                supp = m.Supplier(name="Noma'lum", phone="-")
                db.add(supp)
                db.flush()
            from datetime import date
            any_lot = m.RawLot(lot_no="QARZ", supplier_id=supp.id, grade=grade, grammage=120, qty_kg=0, remaining_kg=0, price_per_kg=0, received_at=date.today())
            db.add(any_lot)
            db.flush()
        
        kg_per_m2 = Decimal(any_lot.grammage) / Decimal("1000")
        take_kg = remaining_m2 * kg_per_m2
        
        any_lot.remaining_kg = Decimal(any_lot.remaining_kg) - take_kg
        cost = (take_kg * Decimal(any_lot.price_per_kg)).quantize(TWO, ROUND_HALF_UP)
        db.add(m.StockMove(lot_id=any_lot.id, order_id=order_id, kg=take_kg, cost=cost, note=note))
        total_cost += cost
        remaining_m2 = Decimal("0")
    return total_cost


def low_stock_alerts(db: Session) -> list[dict]:
    """Minimal qoldiq: oxirgi 30 kun sarfiga qarab necha kunga yetishini hisoblaydi."""
    warn_days = int(get_setting(db, "min_stock_days"))
    out = []
    combos = db.query(m.RawLot.grade, m.RawLot.grammage).distinct().all()
    since = date.today() - timedelta(days=30)
    for grade, grammage in combos:
        stock = raw_stock_for(db, grade, grammage)
        used = (
            db.query(func.coalesce(func.sum(m.StockMove.kg), 0))
            .join(m.RawLot, m.RawLot.id == m.StockMove.lot_id)
            .filter(m.RawLot.grade == grade, m.RawLot.grammage == grammage,
                    m.StockMove.moved_at >= since)
            .scalar()
        )
        daily = Decimal(used) / 30
        days_left = float(stock / daily) if daily > 0 else None
        if days_left is not None and days_left <= warn_days:
            out.append({"grade": grade, "grammage": grammage, "stock_kg": float(stock),
                        "days_left": round(days_left, 1)})
    return out


# ---------------- Debitor / Kreditor (TZ 4.2, 4.3) ----------------

# Mijoz qarzi = boshlang'ich qarz + FAQAT TOPSHIRILGAN mol qiymati − to'lovlar.
# Ishlab chiqilmagan yoki topshirilmagan (delivered_qty=0) buyurtma qarzga kirmaydi.
# Qisman topshirilsa — berilgan ULUSHI: total × (berilgan / jami miqdor).
# `total` dan olinishi MUHIM — u QQS bilan, ya'ni mijoz to'laydigan summa
# (`client_balances_batch` dagi izohga qarang).
def client_balance(db: Session, client_id: int) -> dict:
    c = db.get(m.Client, client_id)
    opening = Decimal(c.opening_balance) if c and c.opening_balance else Decimal("0")
    taken = (
        db.query(func.coalesce(func.sum(
            m.Order.total * m.Order.delivered_qty / m.Order.qty), 0))
        .filter(m.Order.client_id == client_id,
                m.Order.delivered_qty > 0, m.Order.qty > 0)
        .scalar()
    )
    paid = (
        db.query(func.coalesce(func.sum(m.Payment.amount), 0))
        .filter(m.Payment.client_id == client_id)
        .scalar()
    )
    taken = opening + Decimal(taken)
    return {"taken": taken, "paid": Decimal(paid), "debt": taken - Decimal(paid),
            "opening": opening}


def _firma_filtri(query, ustun, firm: str | None):
    """Firma bo'yicha filtr — bo'sh firmali yozuv HAR IKKALA firmada ham ko'rinadi.
    (Mijozlar/xodimlar ro'yxatidagi bilan bir xil qoida — hisob-kitob ham shunga mos.)"""
    if firm:
        return query.filter(ustun.in_([firm, ""]))
    return query


def client_balances_batch(db: Session, firm: str | None = None) -> dict[int, dict]:
    # OLINGAN MOL QIYMATI — `total` ga NISBATAN, `unit_price × miqdor` emas.
    #
    # Nega: `unit_price × delivered_qty` QQSSIZ summa beradi, mijozga esa
    # QQS bilan hisob yoziladi. Natijada 12% QQS qarzdan tushib qolardi —
    # ya'ni to'liq mol olib hech nima to'lamagan mijoz «12% kam qarzdor»
    # bo'lib ko'rinardi. `total` esa uchala QQS rejimida ham (yoq/ustiga/
    # ichida) mijoz TO'LAYDIGAN summa, shuning uchun ulush shundan olinadi.
    #
    # `qty > 0` sharti nolga bo'lishdan himoya.
    taken_q = (
        db.query(m.Order.client_id,
                 func.coalesce(func.sum(
                     m.Order.total * m.Order.delivered_qty / m.Order.qty), 0).label("taken"))
        .filter(m.Order.delivered_qty > 0, m.Order.qty > 0)
        .group_by(m.Order.client_id).all()
    )
    taken_map = {row.client_id: Decimal(row.taken) for row in taken_q}

    paid_q = (
        db.query(m.Payment.client_id, func.coalesce(func.sum(m.Payment.amount), 0).label("paid"))
        .group_by(m.Payment.client_id).all()
    )
    paid_map = {row.client_id: Decimal(row.paid) for row in paid_q}

    out = {}
    cq = _firma_filtri(db.query(m.Client), m.Client.firm, firm)
    for c in cq.all():
        opening = Decimal(c.opening_balance) if c.opening_balance else Decimal("0")
        t = opening + taken_map.get(c.id, Decimal(0))
        p = paid_map.get(c.id, Decimal(0))
        out[c.id] = {"taken": t, "paid": p, "debt": t - p, "opening": opening}
    return out



def debt_aging(db: Session, firm: str | None = None) -> list[dict]:
    """Qarz yoshi: to'lovlar FIFO bo'yicha eng eski buyurtmalarga yotqiziladi."""
    buckets = []
    today = date.today()
    balances = client_balances_batch(db, firm)
    
    # MEZON: mol TOPSHIRILGANMI, maqom NOMI emas.
    #
    # Ilgari bu yer `status.in_(domain.statuslar(...))` bilan filtrlanardi,
    # ya'ni FAOL PROFIL maqom nomlariga bog'liq edi. Profil almashtirilsa
    # (yoki bitta bazada bir nechta soha bo'lsa) eski buyurtmalar
    # maqomlari ro'yxatga tushmay qolardi va qarz yoshi jadvalidagi
    # bo'laklar jimgina NOLGA aylanardi — «жами қарз 496 млн» turib,
    # muddat ustunlari bo'sh chiqardi.
    #
    # Topshirilgan mol esa maqom nomidan qat'i nazar qarzdir — qarz
    # hisobi (`client_balances_batch`) ham aynan shu mezondan foydalanadi.
    all_orders = (
        db.query(m.Order)
        .filter(m.Order.delivered_qty > 0, m.Order.qty > 0)
        .order_by(m.Order.created_at)
        .all()
    )
    from collections import defaultdict
    orders_by_client = defaultdict(list)
    for o in all_orders:
        orders_by_client[o.client_id].append(o)

    for c in _firma_filtri(db.query(m.Client), m.Client.firm, firm).all():
        bal = balances.get(c.id, {"paid": Decimal(0), "debt": Decimal(0)})
        if bal["debt"] <= 0:
            continue
        
        credit = bal["paid"]
        b = {"0-15": Decimal("0"), "15-30": Decimal("0"), "30-60": Decimal("0"), "60+": Decimal("0")}

        # TIZIMDAN OLDINGI QOLDIQ. Ikki tomonlama bo'lishi mumkin:
        #
        #   MUSBAT — eski qarz. Eng eski bo'lakka tushadi. Ilgari u hech
        #     qaysi bo'lakka kirmasdi va qarzi asosan shundan iborat
        #     mijozda «жами қарз 496 млн» turib, muddat ustunlari BO'SH
        #     ko'rinardi.
        #   MANFIY — AVANS (mijoz oldindan to'lagan). U to'lov kabi
        #     ishlaydi, ya'ni bo'laklarni kamaytiradi. Bu ham hisobga
        #     olinmagani uchun haqiqiy bazada bitta mijozda bo'laklar
        #     qarzdan 2.4 mln ortiq chiqdi.
        ochilish = bal.get("opening") or Decimal("0")
        if ochilish > 0:
            qoplandi = min(credit, ochilish)
            credit -= qoplandi
            b["60+"] += ochilish - qoplandi
        elif ochilish < 0:
            credit += -ochilish

        for o in orders_by_client[c.id]:
            # TOPSHIRILGAN ULUSH, buyurtma `total` i emas. Qarz butun
            # tizimda shunday hisoblanadi (`client_balances_batch`) —
            # bo'laklar boshqacha hisoblansa, ular «жами қарз» ustuniga
            # to'g'ri kelmaydi va jadval o'z-o'ziga zid bo'ladi.
            miqdor = Decimal(str(o.qty or 0))
            berilgan = Decimal(str(o.delivered_qty or 0))
            if miqdor <= 0 or berilgan <= 0:
                continue
            t = (Decimal(str(o.total)) * berilgan / miqdor)
            covered = min(credit, t)
            credit -= covered
            rest = t - covered
            if rest <= 0:
                continue
            days = (today - o.created_at.date()).days
            key = "0-15" if days <= 15 else "15-30" if days <= 30 else "30-60" if days <= 60 else "60+"
            b[key] += rest
        buckets.append({
            "client_id": c.id, "company": c.company, "debt": float(bal["debt"]),
            "credit_limit": float(c.credit_limit), "blacklisted": c.blacklisted,
            "aging": {k: float(v) for k, v in b.items()},
        })
    buckets.sort(key=lambda x: -x["debt"])
    return buckets


def supplier_balance(db: Session, supplier_id: int, firm: str | None = None) -> dict:
    """Yetkazib beruvchi bilan hisob-kitob.

    OLINDI (mol) = zakup xaridlari + ombor partiyalari (ikkalasi ham mol kirimi).
    BERILDI (pul) = xaridda to'langani + xarid qarziga to'lovlar + to'g'ridan-to'g'ri to'lovlar.
    QARZ = olindi − berildi. Manfiy bo'lsa — bu bizning AVANSIMIZ (oldindan to'langan pul).

    firm berilsa — faqat o'sha firmaning xaridlari olinadi. DIQQAT: ombor
    partiyalari (raw_lots) va to'g'ridan-to'g'ri to'lovlarda firma ustuni yo'q,
    shuning uchun ular firma tanlangan bo'lsa ham hisobga kiraveradi (boshqa
    ro'yxatlardagi "firmasi belgilanmagan yozuv hamma joyda ko'rinadi" qoidasi bilan bir xil).
    """
    def fp(q):   # xaridlarni firma bo'yicha filtrlash
        return q.filter(m.Purchase.firm.in_([firm, ""])) if firm else q

    # --- olingan mol ---
    got_purchases = fp(
        db.query(func.coalesce(func.sum(m.Purchase.total), 0))
        .filter(m.Purchase.supplier_id == supplier_id)).scalar()
    got_lots = (
        db.query(func.coalesce(func.sum(m.RawLot.qty_kg * m.RawLot.price_per_kg), 0))
        .filter(m.RawLot.supplier_id == supplier_id).scalar()
    )
    got = Decimal(got_purchases) + Decimal(got_lots)

    # --- berilgan pul ---
    paid_at_purchase = fp(
        db.query(func.coalesce(func.sum(m.Purchase.paid_amount), 0))
        .filter(m.Purchase.supplier_id == supplier_id)).scalar()
    paid_on_debt = fp(
        db.query(func.coalesce(func.sum(m.PurchasePayment.amount), 0))
        .join(m.Purchase, m.Purchase.id == m.PurchasePayment.purchase_id)
        .filter(m.Purchase.supplier_id == supplier_id)).scalar()
    paid_direct = (
        db.query(func.coalesce(func.sum(m.SupplierPayment.amount), 0))
        .filter(m.SupplierPayment.supplier_id == supplier_id).scalar()
    )
    paid = Decimal(paid_at_purchase) + Decimal(paid_on_debt) + Decimal(paid_direct)

    debt = got - paid
    return {
        "got": got, "paid": paid, "debt": debt,
        # ortiqcha bergan pulimiz — keyingi moldan chegiriladi
        "avans": -debt if debt < 0 else Decimal("0"),
    }


def cash_flow_forecast(db: Session, days: int = 7, firm: str | None = None) -> dict:
    """Kutilayotgan kirim (debitor, to'lov muddati) - chiqim (kreditor grafigi).

    Buyurtmada firma ustuni yo'q — u mijozning firmasidan olinadi."""
    horizon = date.today() + timedelta(days=days)
    inflow = Decimal("0")
    # PUL qachon kelishi `payment_due_date` bilan belgilanadi, `due_date`
    # bilan emas: birinchisi to'lov muddati, ikkinchisi MOL tayyor bo'lish
    # muddati. Ilgari tayyorlash muddati olinardi — mol bugun tayyor,
    # to'lovi 30 kundan keyin bo'lsa ham pul «bu hafta keladi» deb
    # ko'rsatilardi. Eski yozuvlarda `payment_due_date` bo'sh bo'lishi
    # mumkin, shunda `due_date` ga qaytamiz.
    tolov_muddati = func.coalesce(m.Order.payment_due_date, m.Order.due_date)
    oq = db.query(m.Order.id, m.Order.total).filter(
        tolov_muddati.isnot(None), tolov_muddati <= horizon,
        m.Order.status.in_(domain.statuslar("ishlab_chiqarish", "tayyor", "topshirildi")),
    )
    if firm:
        oq = oq.filter(m.Order.client.has(m.Client.firm.in_([firm, ""])))
    orders = oq.all()
    if orders:
        order_ids = [o.id for o in orders]
        # FAQAT TOPSHIRILGAN mol qiymati kutiladi. Ilgari buyurtma
        # `total` i to'liq olinardi — shu sababli «7 kunda 16 mlrd
        # keladi» chiqib, holbuki mijozlarning JAMI qarzi 9 mlrd edi.
        # Kirim qarzdan katta bo'la olmaydi. Tizimning qolgan qismi
        # qarzni «topshirilgan ulush» bilan hisoblaydi (`client_balance`),
        # prognoz ham xuddi shunday bo'lishi kerak — aks holda paneldagi
        # ikki raqam bir-biriga to'g'ri kelmaydi.
        kutilgan = Decimal(
            db.query(func.coalesce(func.sum(
                m.Order.total * m.Order.delivered_qty / m.Order.qty), 0))
            .filter(m.Order.id.in_(order_ids), m.Order.delivered_qty > 0,
                    m.Order.qty > 0).scalar())
        paid_total = db.query(func.coalesce(func.sum(m.Payment.amount), 0)).filter(
            m.Payment.order_id.in_(order_ids)
        ).scalar()
        inflow = max(Decimal("0"), kutilgan - Decimal(paid_total))
    # CHIQIM ikki manbadan. Ilgari faqat `PaymentSchedule` (qo'lda
    # kiritilgan to'lov grafigi) hisoblanardi — natijada panel
    # «yetkazib beruvchilarga 6.8 mlrd qarzimiz bor» deb turib, 7 kunlik
    # prognozda chiqim 0 chiqardi. Rahbar uchun bu chalg'ituvchi.
    grafik = Decimal(
        db.query(func.coalesce(func.sum(m.PaymentSchedule.amount), 0))
        .filter(m.PaymentSchedule.paid.is_(False),
                m.PaymentSchedule.due_date <= horizon)
        .scalar()
    )
    # To'lanmagan xaridlar: muddati shu oraliqda yoki allaqachon o'tgan.
    # Muddati ko'rsatilmagan qarz prognozga kirmaydi — qachon to'lanishi
    # noma'lum, taxmin qilib qo'yish raqamni yolg'on aniq qilardi.
    xarid_qarzi = Decimal(
        db.query(func.coalesce(
            func.sum(m.Purchase.total - m.Purchase.paid_amount), 0))
        .filter(m.Purchase.due_date.isnot(None),
                m.Purchase.due_date <= horizon,
                m.Purchase.total > m.Purchase.paid_amount)
        .scalar()
    )
    outflow = grafik + xarid_qarzi
    return {"days": days, "expected_in": float(inflow), "expected_out": float(outflow),
            "forecast_balance": float(inflow - outflow)}


# ---------------- Kredit limiti tekshiruvi (TZ 1.1 / 4.2) ----------------

def credit_check(db: Session, client: m.Client, new_total: Decimal) -> dict:
    bal = client_balance(db, client.id)
    would_be = bal["debt"] + new_total
    limit = Decimal(client.credit_limit)
    over = limit > 0 and would_be > limit
    mode = get_setting(db, "credit_mode")
    return {
        "current_debt": float(bal["debt"]), "limit": float(limit),
        "would_be": float(would_be), "over_limit": over,
        "blocked": (over and mode == "block") or client.blacklisted,
        "blacklisted": client.blacklisted,
    }


# ---------------- HR / oylik (TZ 3) ----------------

def payroll(db: Session, year: int, month: int, firm: str | None = None) -> list[dict]:
    start = date(year, month, 1)
    end = date(year + (month == 12), (month % 12) + 1, 1)
    
    work_stats = (
        db.query(
            m.WorkEntry.employee_id,
            func.coalesce(func.sum(m.WorkEntry.amount), 0).label("earned"),
            func.coalesce(func.sum(m.WorkEntry.qty), 0).label("boxes")
        )
        .filter(m.WorkEntry.qc_passed.is_(True),
                m.WorkEntry.worked_at >= start, m.WorkEntry.worked_at < end)
        .group_by(m.WorkEntry.employee_id).all()
    )
    work_map = {row.employee_id: {"earned": row.earned, "boxes": row.boxes} for row in work_stats}

    cash_stats = (
        db.query(m.CashEntry.employee_id, func.coalesce(func.sum(m.CashEntry.amount), 0).label("advances"))
        .filter(m.CashEntry.kind == "Avans",
                m.CashEntry.entry_at >= start, m.CashEntry.entry_at < end)
        .group_by(m.CashEntry.employee_id).all()
    )
    cash_map = {row.employee_id: row.advances for row in cash_stats}

    out = []
    eq = db.query(m.Employee).filter(m.Employee.active.is_(True))
    if firm:
        eq = eq.filter(m.Employee.firm.in_([firm, ""]))
    for e in eq.all():
        w = work_map.get(e.id, {"earned": Decimal(0), "boxes": 0})
        advances = cash_map.get(e.id, Decimal(0))
        earned = w["earned"]
        boxes = w["boxes"]
        
        out.append({
            "employee_id": e.id, "name": e.name, "position": e.position,
            "brigade": e.brigade, "boxes": int(boxes),
            "earned": float(earned), "advances": float(advances),
            "net": float(Decimal(earned) - Decimal(advances)),
        })
    return out


# =====================================================================
# UMUMIY OMBOR — retsept bo'yicha istalgan materialni FIFO bilan yechish
#
# `fifo_writeoff` dan farqi: u faqat QOG'OZ uchun (grade + m²->kg
# grammaj orqali). Bu esa istalgan material bilan ishlaydi va birlikni
# `Material.konversiya` orqali o'giradi.
# =====================================================================

def material_top(db: Session, nom: str):
    """Materialni nomi bo'yicha topadi — katta/kichik harf va kirill/lotin
    farqiga qaramay. Ombor kartochkalari qo'lda kiritilgani uchun nom
    aynan mos kelishiga tayanib bo'lmaydi."""
    nom_t = (nom or "").strip()
    if not nom_t:
        return None
    hammasi = db.query(m.Material).filter(m.Material.active.is_(True)).all()
    kalit = _norm(nom_t)
    for mat in hammasi:
        if _norm(mat.name) == kalit:
            return mat
    return None


def _konversiya(mat, birlik: str) -> Decimal:
    """1 `birlik` necha `mat.unit` ga teng. Birlik bir xil bo'lsa — 1."""
    if not birlik or _norm(birlik) == _norm(mat.unit):
        return Decimal("1")
    xarita = mat.konversiya or {}
    for k, v in xarita.items():
        if _norm(k) == _norm(birlik):
            return Decimal(str(v))
    raise ValueError(
        f"«{mat.name}» {mat.unit} da saqlanadi, retsept {birlik} so'rayapti — "
        f"o'girish koeffitsienti kiritilmagan")


def retsept_yechish(db: Session, order, qatorlar: list[dict],
                    note: str = "") -> Decimal:
    """Retsept qatorlarini ombordan FIFO bilan yechadi. Jami tannarx qaytadi.

    Yetmasa `ValueError` — buyurtma statusi o'zgarmaydi (chaqiruvchi 409
    qaytaradi). Ataylab QISMAN yechilmaydi: yarim yechilgan xomashyo
    ombor qoldig'ini jimgina buzardi.
    """
    # 1) Avval HAMMASI yetarlimi — tekshirib chiqamiz (hech narsa yechmasdan)
    reja = []
    for q in qatorlar:
        if q.get("xato"):
            raise ValueError(f"«{q['material']}»: {q['xato']}")
        mat = material_top(db, q["material"])
        if not mat:
            raise ValueError(f"«{q['material']}» materiali omborda topilmadi")
        koef = _konversiya(mat, q["birlik"])
        kerak = (Decimal(str(q["miqdor"])) * koef).quantize(Decimal("0.0001"))
        lots = (db.query(m.MaterialLot)
                .filter(m.MaterialLot.material_id == mat.id,
                        m.MaterialLot.remaining > 0)
                .order_by(m.MaterialLot.received_at, m.MaterialLot.id).all())
        bor = sum(Decimal(str(l.remaining)) for l in lots)
        if bor < kerak:
            raise ValueError(
                f"«{mat.name}» yetarli emas: kerak {kerak} {mat.unit}, "
                f"omborda {bor} {mat.unit}")
        reja.append((mat, kerak, lots))

    # 2) Hammasi yetarli — endi yechamiz
    jami = Decimal("0")
    for mat, kerak, lots in reja:
        qolgan = kerak
        for lot in lots:
            if qolgan <= 0:
                break
            olinadi = min(Decimal(str(lot.remaining)), qolgan)
            narx = (olinadi * Decimal(str(lot.price_per_unit))).quantize(Decimal("0.01"))
            lot.remaining = Decimal(str(lot.remaining)) - olinadi
            qolgan -= olinadi
            jami += narx
            db.add(m.MaterialWriteoff(
                lot_id=lot.id, order_id=getattr(order, "id", None),
                qty=olinadi, cost=narx, note=note))
        mat.stock_qty = Decimal(str(mat.stock_qty or 0)) - kerak
    return jami


# =====================================================================
#  QQS (НДС)
#
#  `Order.total` — MIJOZ TO'LAYDIGAN summa, ya'ni QQS BILAN. Butun
#  moliya (qarz, to'lov, kassa, sverka) shunga tayangan, shuning uchun
#  uning ma'nosi o'zgartirilmadi — QQS qo'shilganda ham eski hisoblar
#  to'g'ri qolaveradi.
# =====================================================================

def qqs_hisobla(db: Session, summa: Decimal,
                stavka: Decimal | None = None) -> dict:
    """Kiritilgan summadan QQSsiz / QQS / jami ni ajratadi.

    `summa` — foydalanuvchi kiritgan narx × miqdor.
    `stavka` berilsa sozlamadagi o'rniga o'sha ishlatiladi (eksport 0%,
    yoki eski buyurtmani qayta hisoblashda o'sha paytdagi stavka).
    """
    summa = Decimal(str(summa))
    rejim = (get_setting(db, "qqs_rejimi") or "yoq").strip().lower()
    if stavka is None:
        stavka = dset(db, "qqs_stavka")
    stavka = Decimal(str(stavka))

    if rejim == "yoq" or stavka <= 0:
        return {"rejim": "yoq", "stavka": Decimal("0"),
                "qqssiz": summa, "qqs": Decimal("0"), "jami": summa}

    if rejim == "ichida":
        # Narx QQS bilan aytilgan: 112 000 dan 12% ni AJRATAMIZ
        qqssiz = (summa / (Decimal("1") + stavka / 100)).quantize(TWO, ROUND_HALF_UP)
        qqs = summa - qqssiz          # ayirma bilan — tiyin yo'qolmasin
        jami = summa
    else:   # "ustiga"
        qqssiz = summa
        qqs = (summa * stavka / 100).quantize(TWO, ROUND_HALF_UP)
        jami = qqssiz + qqs

    return {"rejim": rejim, "stavka": stavka,
            "qqssiz": qqssiz, "qqs": qqs, "jami": jami}


def retsept_tannarx(db: Session, qatorlar: list[dict]) -> dict:
    """Retsept qatorlarining OMBORDAGI narxi — FIFO bo'yicha, YECHMASDAN.

    Smeta buyurtma yaratilishidan OLDIN kerak, ya'ni hali hech narsa
    yechilmagan paytda. Shuning uchun bu funksiya faqat HISOBLAYDI:
    lotlarni eng eskisidan boshlab «xayolan» oladi va narxini yig'adi.

    Ombordagi qoldiq yetmasa — qolgani `Material.last_price` (oxirgi
    xarid narxi) bilan hisoblanadi va ogohlantiriladi. Aks holda yangi
    korxonada (ombor bo'sh) tannarx nol chiqib, narx ham nol bo'lardi.
    """
    jami = Decimal("0")
    tafsilot = []
    ogohlantirish = []

    for q in qatorlar:
        if q.get("xato"):
            ogohlantirish.append(f"«{q['material']}»: {q['xato']}")
            continue
        mat = material_top(db, q["material"])
        kerak_asl = Decimal(str(q["miqdor"]))
        if mat is None:
            ogohlantirish.append(
                f"«{q['material']}» ombor kartochkasi yo'q — narxi hisobga kirmadi")
            tafsilot.append({"material": q["material"], "birlik": q["birlik"],
                             "miqdor": kerak_asl, "summa": Decimal("0")})
            continue
        try:
            koef = _konversiya(mat, q["birlik"])
        except ValueError as e:
            ogohlantirish.append(str(e))
            continue

        kerak = kerak_asl * koef
        qolgan = kerak
        summa = Decimal("0")
        lots = (db.query(m.MaterialLot)
                .filter(m.MaterialLot.material_id == mat.id,
                        m.MaterialLot.remaining > 0)
                .order_by(m.MaterialLot.received_at, m.MaterialLot.id).all())
        for lot in lots:
            if qolgan <= 0:
                break
            olinadi = min(Decimal(str(lot.remaining)), qolgan)
            summa += olinadi * Decimal(str(lot.price_per_unit))
            qolgan -= olinadi
        if qolgan > 0:
            # Omborda yetmadi — qolganini oxirgi xarid narxida baholaymiz
            oxirgi = Decimal(str(mat.last_price or 0))
            summa += qolgan * oxirgi
            if oxirgi <= 0:
                ogohlantirish.append(
                    f"«{mat.name}» narxi noma'lum — tannarx to'liq emas")
            else:
                ogohlantirish.append(
                    f"«{mat.name}» omborda yetmaydi, {qolgan:.3f} {mat.unit} "
                    f"oxirgi narxda ({float(oxirgi):,.0f}) hisoblandi")

        summa = summa.quantize(TWO, ROUND_HALF_UP)
        jami += summa
        tafsilot.append({"material": mat.name, "birlik": q["birlik"],
                         "miqdor": kerak_asl, "summa": summa})

    return {"jami": jami.quantize(TWO, ROUND_HALF_UP),
            "qatorlar": tafsilot, "ogohlantirish": ogohlantirish}


def ustama_foizi(db: Session, category: str) -> Decimal:
    """Mijoz toifasiga qarab narx ustamasi. Sozlamadan olinadi."""
    kalit = {"VIP": "margin_vip", "Standart": "margin_standart"}.get(
        category, "margin_yangi")
    return dset(db, kalit)
