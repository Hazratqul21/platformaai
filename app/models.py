from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    String, Integer, Numeric, Boolean, ForeignKey, Date, DateTime, Text, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

# PostgreSQL da JSONB — indekslanadi, ichidan qidirish mumkin va tezroq.
# SQLite da oddiy JSON. Bitta ta'rif ikkala bazada ham to'g'ri tushadi.
JSONB_ = JSON().with_variant(JSONB, "postgresql")

D = Numeric(18, 2)   # pul summalari — float ishlatilmaydi
Q3 = Numeric(18, 3)  # miqdorlar (dona, kg, m³, metr — kasrli bo'lishi mumkin)

# ---- Buyurtma statuslari (treker bosqichlari TZ 1.3) ----
ST_KUTISHDA = "Kutishda"            # smeta yuborildi, mijoz javobi kutilmoqda
ST_MUZOKARA = "Muzokara"            # mijoz narxga rozi emas
ST_SEXDA = "Sexda kesilmoqda"       # tasdiqlandi -> ishlab chiqarishga berildi
ST_OMBORDA = "Omborga tushdi"       # tayyor mahsulot omborida
ST_YETKAZILDI = "Yetkazib berildi"
ST_BEKOR = "Bekor qilindi"
STATUSES = [ST_KUTISHDA, ST_MUZOKARA, ST_SEXDA, ST_OMBORDA, ST_YETKAZILDI, ST_BEKOR]

ROLES = ["Rahbar", "Menejer", "Sklad mudiri", "Sex boshlig'i", "Buxgalter"]
GRADES = ["K0", "K1", "K2", "T-22", "T-23"]

# Buyurtma turi — mijozning o'z atamalari (kirillcha yoziladi, o'zgartirilmasin).
# Gofra qavatlari va gofra bo'lmagan materiallar bitta ro'yxatda.
ORDER_TURLARI = ["1 слой", "2 слой", "3 слой", "5 слой",
                 "Самоклейка", "Офсет", "Картон Меловка"]
# Qavat soni: gofra turlari uchun — o'z raqami, boshqalari bir qatlamli
TUR_LAYERS = {"1 слой": 1, "2 слой": 2, "3 слой": 3, "5 слой": 5}
TUR_DEFAULT = "3 слой"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(30))


class AuthToken(Base):
    """Login token bazada saqlanadi — server qayta ishga tushsa ham foydalanuvchi
    tizimdan chiqib ketmaydi (avval xotirada edi, har restartda hamma logout bo'lardi)."""
    __tablename__ = "auth_tokens"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires: Mapped[datetime] = mapped_column(DateTime)


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(150))
    contact: Mapped[str] = mapped_column(String(100), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    inn: Mapped[str] = mapped_column(String(20), default="")          # STIR
    pay_type: Mapped[str] = mapped_column(String(20), default="Naqd")  # Naqd / Pul o'tkazish
    category: Mapped[str] = mapped_column(String(20), default="Yangi")  # VIP / Standart / Yangi
    credit_limit: Mapped[Decimal] = mapped_column(D, default=Decimal("0"))
    blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    firm: Mapped[str] = mapped_column(String(60), default="")  # qaysi firmaga tegishli
    telegram_chat_id: Mapped[str] = mapped_column(String(30), default="")
    # Tizimdan oldingi (masalan 1.07.26 gacha) qarz — musbat: mijoz bizga qarzdor,
    # manfiy: biz mijozga qarzdormiz (avans/oldindan to'langan)
    opening_balance: Mapped[Decimal] = mapped_column(D, default=Decimal("0"))
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="client")
    payments: Mapped[list["Payment"]] = relationship(back_populates="client")


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(30), default="")
    # tur: "Qog'oz" / "Pechat" (ko'chada print qiladigan firma) / "Boshqa"
    kind: Mapped[str] = mapped_column(String(20), default="Qog'oz")
    lots: Mapped[list["RawLot"]] = relationship(back_populates="supplier")


class RawLot(Base):
    """Xomashyo kirimi — har bir partiya (lot) alohida, FIFO uchun."""
    __tablename__ = "raw_lots"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_no: Mapped[str] = mapped_column(String(30))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    grade: Mapped[str] = mapped_column(String(50))        # K0/K1/K2/T-22/T-23 (Qo'lda kiritiladi)
    grammage: Mapped[int] = mapped_column(Integer, default=120)  # Grammaj (gr/m2)
    qty_kg: Mapped[Decimal] = mapped_column(D)            # kirim kg
    remaining_kg: Mapped[Decimal] = mapped_column(D)      # qoldiq kg
    price_per_kg: Mapped[Decimal] = mapped_column(D)      # so'm/kg
    received_at: Mapped[date] = mapped_column(Date, default=date.today)

    supplier: Mapped["Supplier"] = relationship(back_populates="lots")


class SupplierPayment(Base):
    __tablename__ = "supplier_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    amount: Mapped[Decimal] = mapped_column(D)
    paid_at: Mapped[date] = mapped_column(Date, default=date.today)
    note: Mapped[str] = mapped_column(String(200), default="")


class PaymentSchedule(Base):
    """Yetkazib beruvchiga bo'lib-bo'lib to'lash grafigi."""
    __tablename__ = "payment_schedules"
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(D)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    product_name: Mapped[str] = mapped_column(String(100), default="")

    # ---- SOHA QATLAMI ----------------------------------------------------
    # Har biznesning o'z o'lchov maydonlari shu yerda. Karton sexi uchun
    # length_mm/grade/layers..., non zavodi uchun "non turi"/"og'irligi",
    # mebel uchun "material"/"o'lcham" — YADRO ularning ma'nosini bilmaydi,
    # shunchaki saqlaydi va ko'rsatadi.
    #
    # MutableDict: usiz `order.attributes["x"] = 1` deb o'zgartirilsa
    # SQLAlchemy buni SEZMAYDI va commit'da saqlanmaydi — jimgina yo'qoladi.
    attributes: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB_), default=dict, nullable=False)

    # ---- Quyidagi ustunlar SOHA QATLAMIGA (attributes) ko'chirilmoqda -----
    # 1-bosqich, 4-qadamda o'chiriladi. Yangi kod bularni O'QIMASIN —
    # `attributes` dan foydalaning (app/domain.py).
    # Quti parametrlari (mm)
    length_mm: Mapped[int] = mapped_column(Integer)
    width_mm: Mapped[int] = mapped_column(Integer)
    height_mm: Mapped[int] = mapped_column(Integer)
    # Buyurtma turi: "3 слой" / "Самоклейка" / "Офсет" ... (ORDER_TURLARI)
    tur: Mapped[str] = mapped_column(String(30), default=TUR_DEFAULT)
    layers: Mapped[int] = mapped_column(Integer, default=3)   # tur dan kelib chiqadi (1/2/3/5)
    grade: Mapped[str] = mapped_column(String(50), default="K1")
    colors: Mapped[int] = mapped_column(Integer, default=0)   # flekso bosma ranglar soni
    is_offset: Mapped[bool] = mapped_column(Boolean, default=False)  # eski maydon: tur=="Офсет"
    m2_per_box: Mapped[Decimal] = mapped_column(Numeric(18, 4))  # karton o'lchovi
    # ---- ko'chiriladigan ustunlar tugadi ---------------------------------

    # ---- YADRO: har biznesda bor ----------------------------------------
    # Mahsulot rasmi — sexda telefonda olinadi, keyin ko'rsatish uchun (fayl nomi)
    photo: Mapped[str] = mapped_column(String(200), default="")
    # MIQDOR KASRLI. Karton «dona» bilan o'lchanadi, lekin beton m³,
    # kabel metr, mato metr, go'sht kg bilan — 2.5 m³ beton butun songa
    # sig'maydi. O'lchov birligi profilda (`olchov.birlik`).
    qty: Mapped[Decimal] = mapped_column(Q3)                   # jami buyurtma
    delivered_qty: Mapped[Decimal] = mapped_column(Q3, default=Decimal("0"))  # topshirilgan
    # Hisob-kitob (buyurtma paytida qotiriladi). Bular YADRO: qanday
    # o'lchangani soha ishi, lekin "1 dona qancha turadi" hamma biznesda bor.
    unit_cost: Mapped[Decimal] = mapped_column(D)             # 1 dona tannarx
    unit_price: Mapped[Decimal] = mapped_column(D)            # 1 dona sotuv narxi
    total: Mapped[Decimal] = mapped_column(D)
    prepaid_percent: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default=ST_KUTISHDA)
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)        # tayyorlash muddati
    payment_due_date: Mapped[date | None] = mapped_column(Date, nullable=True) # to'lov muddati
    delivered_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    accepted_stamp: Mapped[bool] = mapped_column(Boolean, default=False)  # bot "Qabul qildim"

    client: Mapped["Client"] = relationship(back_populates="orders")
    photos: Mapped[list["OrderPhoto"]] = relationship(
        back_populates="order", cascade="all, delete-orphan",
        order_by="OrderPhoto.id")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class OrderPhoto(Base):
    """Buyurtma rasmlari — bittadan ko'p bo'lishi mumkin (sexda telefonda olinadi)."""
    __tablename__ = "order_photos"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    filename: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    order: Mapped["Order"] = relationship(back_populates="photos")


class Payment(Base):
    """Mijozdan kelgan to'lov (naqd / o'tkazma)."""
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(D)
    method: Mapped[str] = mapped_column(String(20), default="Naqd")
    paid_at: Mapped[date] = mapped_column(Date, default=date.today)
    note: Mapped[str] = mapped_column(String(200), default="")

    client: Mapped["Client"] = relationship(back_populates="payments")
    order: Mapped["Order"] = relationship(back_populates="payments")


class StockMove(Base):
    """Xomashyo spisaniyasi — FIFO, brak 5% bilan birga yechiladi."""
    __tablename__ = "stock_moves"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("raw_lots.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    kg: Mapped[Decimal] = mapped_column(Numeric(18, 4))       # brak bilan jami yechilgan kg
    cost: Mapped[Decimal] = mapped_column(D)                  # kg * lot narxi
    moved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    note: Mapped[str] = mapped_column(String(200), default="")


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    position: Mapped[str] = mapped_column(String(50), default="Stanokchi")
    phone: Mapped[str] = mapped_column(String(30), default="")
    rate_per_box: Mapped[Decimal] = mapped_column(D, default=Decimal("150"))  # so'm/dona
    brigade: Mapped[str] = mapped_column(String(50), default="")
    firm: Mapped[str] = mapped_column(String(60), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkEntry(Base):
    """Sdelshina — QC dan o'tgan qutilar bo'yicha avtomatik hisob."""
    __tablename__ = "work_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    qty: Mapped[int] = mapped_column(Integer)
    qc_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    rate: Mapped[Decimal] = mapped_column(D)
    amount: Mapped[Decimal] = mapped_column(D)   # qty * rate (QC dan o'tganlarga)
    worked_at: Mapped[date] = mapped_column(Date, default=date.today)
    
    employee: Mapped["Employee"] = relationship()


class CashEntry(Base):
    """Podotchyot kassa: avans, yo'lkira, mayda xarajatlar."""
    __tablename__ = "cash_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(20))  # Avans / Xarajat
    amount: Mapped[Decimal] = mapped_column(D)
    note: Mapped[str] = mapped_column(String(200), default="")
    firm: Mapped[str] = mapped_column(String(60), default="")
    entry_at: Mapped[date] = mapped_column(Date, default=date.today)
    
    employee: Mapped["Employee"] = relationship()


class InventoryCheck(Base):
    """Oylik inventarizatsiya: tizim qoldig'i vs haqiqiy o'lchov."""
    __tablename__ = "inventory_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    grade: Mapped[str] = mapped_column(String(50))
    grammage: Mapped[int] = mapped_column(Integer, default=120)
    system_kg: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    actual_kg: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    diff_kg: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    checked_at: Mapped[date] = mapped_column(Date, default=date.today)
    note: Mapped[str] = mapped_column(String(200), default="")


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))


class MaterialLot(Base):
    """UMUMIY xomashyo partiyasi — har qanday material uchun, FIFO.

    `RawLot` dan farqi: u faqat QOG'OZ uchun (grade + grammage + kg).
    Bu esa istalgan materialga yaraydi — un, LDSP, mato, metall, bo'yoq.
    Material o'z birligida saqlanadi (`Material.unit`), retsept boshqa
    birlikda so'rasa `Material.konversiya` orqali o'giriladi.

    Nega alohida jadval: FIFO uchun har partiyaning O'Z NARXI kerak.
    `Material.stock_qty` faqat umumiy qoldiqni biladi, qaysi partiya
    qancha turganini emas — tannarx shundan noto'g'ri chiqardi.
    """
    __tablename__ = "material_lots"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    lot_no: Mapped[str] = mapped_column(String(30), default="")
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Q3)            # kirim (material birligida)
    remaining: Mapped[Decimal] = mapped_column(Q3)      # qoldiq
    price_per_unit: Mapped[Decimal] = mapped_column(D)  # so'm / birlik
    received_at: Mapped[date] = mapped_column(Date, default=date.today)

    material: Mapped["Material"] = relationship()


class MaterialWriteoff(Base):
    """Retsept bo'yicha yechilgan xomashyo — qaysi buyurtmaga, qancha, qancha pulga."""
    __tablename__ = "material_writeoffs"
    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("material_lots.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Q3)     # material birligida (brak bilan)
    cost: Mapped[Decimal] = mapped_column(D)
    moved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    note: Mapped[str] = mapped_column(String(200), default="")


class SohaProfil(Base):
    """SOHA SHABLONI — biznes turining ta'rifi, KOD EMAS, MA'LUMOT.

    Har bazada bir nechta profil turishi mumkin, lekin faqat BITTASI faol
    (`faol=True`). Sabab: bitta baza = bitta mijoz = bitta biznes turi
    (2-bosqich, «har mijozga alohida baza» qarori).

    `tarif_json` — profilning to'liq ta'rifi:
      {"kalit","nom","maydonlar":[...],"matnlar":{...}}
    Tuzilishi va misollar: app/profiles/*.json

    AI agent (4-bosqich) aynan shu yozuvni to'ldiradi — kod yozmaydi.
    """
    __tablename__ = "soha_profillar"
    id: Mapped[int] = mapped_column(primary_key=True)
    kalit: Mapped[str] = mapped_column(String(50), unique=True)
    nom: Mapped[str] = mapped_column(String(120))
    tarif_json: Mapped[str] = mapped_column(Text)
    faol: Mapped[bool] = mapped_column(Boolean, default=False)
    # Foydalanuvchi (yoki AI agent) shu profilni TAHRIRLAGANMI.
    # Tahrirlanmagan profil dastur yangilanganda shablondan yangilanadi —
    # shunday qilib retsept/formula tuzatishlari mavjud mijozlarga ham
    # yetib boradi. Tahrirlangani esa HECH QACHON ustidan yozilmaydi,
    # aks holda mijozning sozlamasi jimgina yo'qolardi.
    ozgartirilgan: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CustomSection(Base):
    """Konstruktor: boshqaruvchi o'zi ochadigan qo'shimcha bo'lim.
    fields — JSON: [{"key":"f1","label":"Nomi","type":"matn|raqam|pul|sana"}]"""
    __tablename__ = "custom_sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    icon: Mapped[str] = mapped_column(String(10), default="📋")
    fields_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CustomRecord(Base):
    """Konstruktor bo'limidagi yozuv (ma'lumotlar JSON holida)."""
    __tablename__ = "custom_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("custom_sections.id"))
    data_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================
#  POLIGRAFIYA MODULI — kataloglar, materiallar, xarid, xizmatlar
#  (hammasi admin tomonidan sozlanadi — qattiq kodlanmagan)
# ============================================================


DEFAULT_UNITS = ["dona", "kg", "m²", "litr", "rulon", "paket", "list", "metr"]
DEFAULT_POSITIONS = ["Stanokchi", "Yordamchi", "Kleychi", "Kashirovkachi",
                     "Flekso operatori", "Kesuvchi", "Laminatchi", "Bosmachi"]
# Materiallar bo'limlari (kataloglar) — admin qo'shadi
DEFAULT_CATEGORIES = ["Qog'oz", "Karton", "Gofrokarton", "Kley", "Bo'yoq",
                      "Lak", "Plyonka", "Boshqa"]
PAYMENT_TYPES = ["Naqd", "Qarz", "Keyinroq to'lash"]


class Unit(Base):
    """O'lchov birligi — dona, kg, m², litr, rulon, paket (admin qo'shadi)."""
    __tablename__ = "units"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)


class Position(Base):
    """Xodim lavozimi — Kleychi, Kashirovkachi... (admin qo'shadi)."""
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Category(Base):
    """Materiallar bo'limi — Qog'oz, Karton, Kley, Lak... (admin qo'shadi).
    Mahsulot nomi bilan birga ko'rsatiladi."""
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Material(Base):
    """Material katalogi — qog'oz turi, karton, kley, lak...
    Bir marta yaratiladi, keyin xarid va buyurtmalarda qayta ishlatiladi."""
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))            # силвер пак, хитой сток
    category: Mapped[str] = mapped_column(String(50), default="Qog'oz")  # bo'lim
    marka: Mapped[str] = mapped_column(String(60), default="")
    manufacturer: Mapped[str] = mapped_column(String(80), default="")
    grammaj: Mapped[str] = mapped_column(String(20), default="")   # 140 гр (qog'oz)
    unit: Mapped[str] = mapped_column(String(20), default="kg")    # o'lchov birligi
    last_price: Mapped[Decimal] = mapped_column(D, default=Decimal("0"))
    stock_qty: Mapped[Decimal] = mapped_column(Q3, default=Decimal("0"))
    min_stock: Mapped[Decimal] = mapped_column(Q3, default=Decimal("0"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # BOSHQA BIRLIKKA O'GIRISH: {"m²": "0.12"} — 1 m² = 0.12 kg.
    # Qog'oz kg da saqlanadi, lekin karton retsepti m² so'raydi; mato metr
    # da saqlanib, retsept m² so'rashi mumkin. Konversiyasiz har soha
    # o'z birligiga majbur bo'lardi.
    konversiya: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSONB_), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Purchase(Base):
    """Zakup — material xaridi (Master Excel'ning o'zi).
    kg/dona/rulon... da olinadi. Naqd yoki qarzga."""
    __tablename__ = "purchases"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    qty: Mapped[Decimal] = mapped_column(Q3)
    unit: Mapped[str] = mapped_column(String(20), default="kg")
    fmt: Mapped[str] = mapped_column(String(40), default="")      # format: 85*59, ф62*85
    unit_price: Mapped[Decimal] = mapped_column(D)               # narx / birlik
    total: Mapped[Decimal] = mapped_column(D)                    # qty * unit_price
    payment_type: Mapped[str] = mapped_column(String(20), default="Naqd")
    paid_amount: Mapped[Decimal] = mapped_column(D, default=Decimal("0"))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # qarz muddati
    purchased_at: Mapped[date] = mapped_column(Date, default=date.today)
    note: Mapped[str] = mapped_column(String(200), default="")
    firm: Mapped[str] = mapped_column(String(60), default="")

    material: Mapped["Material"] = relationship()


class PurchasePayment(Base):
    """Xarid qarziga to'lov (yetkazib beruvchiga)."""
    __tablename__ = "purchase_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))
    amount: Mapped[Decimal] = mapped_column(D)
    method: Mapped[str] = mapped_column(String(20), default="Naqd")  # Naqd/Karta/O'tkazma
    paid_at: Mapped[date] = mapped_column(Date, default=date.today)
    note: Mapped[str] = mapped_column(String(200), default="")


class MaterialMove(Base):
    """Material kirim/chiqim tarixi — real vaqt qoldiq uchun."""
    __tablename__ = "material_moves"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    qty: Mapped[Decimal] = mapped_column(Q3)                 # + kirim, - chiqim
    reason: Mapped[str] = mapped_column(String(60), default="Xarid")
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Service(Base):
    """Ishlab chiqarish xizmati — laminatsiya, noj, tisneniye, lak turlari.
    Har birining narxi, o'lchovi va formulasi (admin sozlaydi)."""
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    price: Mapped[Decimal] = mapped_column(D, default=Decimal("0"))
    unit: Mapped[str] = mapped_column(String(20), default="m²")
    formula: Mapped[str] = mapped_column(String(120), default="x*y*n")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Formula(Base):
    """Sozlanadigan hisob-kitob formulasi (sebestoyimost uchun).
    Masalan: tashqi qavat = x*y*g*q*n, kley = x*y*0.1*n."""
    __tablename__ = "formulas"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    expression: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(200), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class KassaEntry(Base):
    """Kassa jurnali — kirim-chiqim daftari (приход-расход Excel'ning o'zi).
    Har yozuv: sana, yo'nalish, kimga/kimdan, izoh, summa, valyuta, sex/firma."""
    __tablename__ = "kassa_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    firm: Mapped[str] = mapped_column(String(60), default="Asosiy")   # sex/filial nomi
    direction: Mapped[str] = mapped_column(String(10))                # Kirim / Chiqim
    who: Mapped[str] = mapped_column(String(120))                     # kimga / kimdan
    note: Mapped[str] = mapped_column(String(200), default="")
    amount: Mapped[Decimal] = mapped_column(D)
    currency: Mapped[str] = mapped_column(String(10), default="so'm")  # so'm / USD
    entry_at: Mapped[date] = mapped_column(Date, default=date.today)
    created_by: Mapped[str] = mapped_column(String(100), default="")
    # --- Manbaga bog'lanish. Pul harakati o'z bo'limida yoziladi (mijoz to'lovi,
    # xarid to'lovi, avans...), kassaga esa shu yozuvning nusxasi tushadi. Bog'lanish
    # ikki ish uchun kerak: bir harakat kassaga ikki marta tushmasin, va manba
    # o'chirilganda kassadagi nusxasi ham ketsin.
    linked_cash_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_entries.id"), nullable=True)          # sex xarajati / avans
    linked_payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id"), nullable=True)              # mijoz to'lovi
    linked_purchase_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchases.id"), nullable=True)             # naqd xarid
    linked_purchase_payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_payments.id"), nullable=True)     # xarid qarziga to'lov
    linked_supplier_payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("supplier_payments.id"), nullable=True)     # yetkazib beruvchiga to'lov


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    who: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
