"""IJARACHILIK — so'rovni MIJOZGA bog'lash.

MUAMMO. Bugungi kod «bitta jarayon = bitta baza» deb faraz qiladi:
`db.py` da modul darajasidagi `engine`, `domain.py` da modul
darajasidagi `_KESH`. Ikki mijoz bir jarayonda ishlaganda bu
ma'lumotni ARALASHTIRIB yuboradi — va xato bermaydi, JIMGINA noto'g'ri
ishlaydi. Eng yomon nuqson turi shu.

YECHIM. Joriy firma `contextvars` da saqlanadi. Sabab: `profil()` 26
joyda chaqiriladi va hammasiga qo'shimcha argument uzatishda bittasi
albatta unutiladi. `contextvars` da imzolar o'zgarmaydi, lekin har
so'rov (va har `asyncio` vazifasi) o'z qiymatini ko'radi.

ORQAGA MOSLIK. `IJARACHILIK` yoqilmagan bo'lsa hamma narsa avvalgidek
ishlaydi — bitta baza, bitta profil. Shuning uchun mavjud 125
endpoint, `sinov.sh` va Rustam akaning nusxasi buzilmaydi.
"""
import os
import threading
from contextvars import ContextVar
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

# Ijarachilik yoqilganmi. O'chiq bo'lsa — eski xatti-harakat.
def yoqilganmi() -> bool:
    return os.getenv("IJARACHILIK", "").strip() in ("1", "true", "ha")


@dataclass(frozen=True)
class Firma:
    """So'rov davomida kerak bo'ladigan MINIMUM. To'liq yozuv boshqaruv
    bazasida — bu yerda faqat marshrutlash uchun kerak bo'lgani."""
    id: int
    kod: str
    baza_nomi: str
    yozish_mumkinmi: bool = True


# `default=None` — firma o'rnatilmagan holat ham to'g'ri holat
# (fon vazifalari, testlar, ijarachiliksiz rejim).
_JORIY: ContextVar[Firma | None] = ContextVar("joriy_firma", default=None)


def ornat(firma: Firma | None):
    """So'rov boshida chaqiriladi. Qaytgan tokenni `tozala` ga bering."""
    return _JORIY.set(firma)


def tozala(token) -> None:
    _JORIY.reset(token)


def joriy() -> Firma | None:
    return _JORIY.get()


def kalit() -> str:
    """Kesh kaliti. Firma yo'q bo'lsa — yagona rejimning kaliti.

    Bu funksiya `domain.py` keshi uchun ham ishlatiladi: kesh shu
    kalit bo'yicha ajratiladi va bir mijozning profili boshqasiga
    ko'rinmaydi."""
    f = joriy()
    return f.baza_nomi if f else "_yagona"


# ---------------------------------------------------------------------
# ENGINE REGISTRI
#
# Har mijozga alohida `Engine` kerak, lekin ularni cheksiz ochib
# bo'lmaydi: 50 mijoz × (pool_size 10 + overflow 20) = 1500 ulanish,
# PostgreSQL standarti esa 100. Shuning uchun ikki chegara:
#   1. har mijozga KICHIK hovuz
#   2. ochiq `Engine` lar soniga LRU chegarasi
# ---------------------------------------------------------------------
def _pool_olchami() -> tuple[int, int]:
    return (int(os.getenv("MIJOZ_POOL", "2")),
            int(os.getenv("MIJOZ_POOL_OVERFLOW", "3")))


def _max_engine() -> int:
    return int(os.getenv("MAX_ENGINE", "50"))


def baza_url(baza_nomi: str) -> str:
    """Ulanish satri SHABLONDAN yasaladi.

    Parol boshqaruv bazasida SAQLANMAYDI — u serverning `.env` ida.
    Bazada faqat baza nomi turadi.

    Namunalar:
      MIJOZ_DB_SHABLON=postgresql://inna:parol@db:5432/{baza}
      MIJOZ_DB_SHABLON=sqlite:////yol/{baza}.db        (sinov uchun)
    """
    shablon = os.getenv("MIJOZ_DB_SHABLON", "")
    if not shablon:
        raise RuntimeError(
            "MIJOZ_DB_SHABLON o'rnatilmagan — ijarachilik rejimida "
            "mijoz bazasining ulanish shabloni majburiy")
    url = shablon.replace("{baza}", baza_nomi)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


_qulf = threading.Lock()
_ENGINELAR: dict[str, Engine] = {}      # baza_nomi -> Engine
_SESSIYALAR: dict[str, sessionmaker] = {}
_NAVBAT: list[str] = []                 # LRU: oxirida — eng yaqinda ishlatilgan


def _lru_yangila(baza_nomi: str) -> None:
    if baza_nomi in _NAVBAT:
        _NAVBAT.remove(baza_nomi)
    _NAVBAT.append(baza_nomi)


def _eskisini_yop() -> None:
    """Chegaradan oshsa eng kam ishlatilganini yopadi.

    Kechasi ishlamaydigan mijoz ulanish band qilib turmasin."""
    while len(_NAVBAT) > _max_engine():
        eski = _NAVBAT.pop(0)
        eng = _ENGINELAR.pop(eski, None)
        _SESSIYALAR.pop(eski, None)
        if eng is not None:
            eng.dispose()


def firma_engine(baza_nomi: str) -> Engine:
    with _qulf:
        eng = _ENGINELAR.get(baza_nomi)
        if eng is None:
            url = baza_url(baza_nomi)
            if url.startswith("sqlite"):
                eng = create_engine(url, connect_args={"check_same_thread": False})
            else:
                olcham, overflow = _pool_olchami()
                eng = create_engine(url, pool_size=olcham,
                                    max_overflow=overflow, pool_pre_ping=True,
                                    pool_recycle=1800)
            _ENGINELAR[baza_nomi] = eng
            _SESSIYALAR[baza_nomi] = sessionmaker(bind=eng, autoflush=False,
                                                  expire_on_commit=False)
        _lru_yangila(baza_nomi)
        _eskisini_yop()
        return _ENGINELAR[baza_nomi]


def firma_sessiya(baza_nomi: str):
    firma_engine(baza_nomi)          # yaratilganiga ishonch hosil qiladi
    return _SESSIYALAR[baza_nomi]()


def ochiq_enginelar() -> int:
    return len(_ENGINELAR)


def hammasini_yop() -> None:
    """Testlar va o'chirish uchun."""
    with _qulf:
        for eng in _ENGINELAR.values():
            eng.dispose()
        _ENGINELAR.clear()
        _SESSIYALAR.clear()
        _NAVBAT.clear()


# ---------------------------------------------------------------------
# SO'ROVDAN FIRMANI ANIQLASH
#
# Tartib: subdomen -> `X-Firma` sarlavhasi.
#
# ESLATMA — token bo'yicha aniqlash ATAYLAB YO'Q. ERP tokeni MIJOZ
# bazasida yotadi, ya'ni uni o'qish uchun avval qaysi bazaga borishni
# bilish kerak. Subdomen bu tugunni ochadi va tokenlarni ko'chirishga
# hojat qolmaydi. `platforma_tokenlar` esa boshqa narsa uchun —
# ro'yxatdan o'tish va hisob-kitob kabinetiga kirish.
# ---------------------------------------------------------------------
_ASOSIY_DOMEN = None


def asosiy_domen() -> str:
    return os.getenv("ASOSIY_DOMEN", "innasoft.uz").lower()


def kod_ajrat(host: str) -> str | None:
    """`mebelsex.innasoft.uz` -> `mebelsex`. Mos kelmasa `None`."""
    if not host:
        return None
    host = host.split(":")[0].strip().lower()
    domen = asosiy_domen()
    if not host.endswith("." + domen):
        return None
    kod = host[: -(len(domen) + 1)]
    # `www.innasoft.uz` firma emas; ichma-ich subdomen ham qabul qilinmaydi
    if not kod or "." in kod or kod in ("www", "app", "api", "admin"):
        return None
    return kod


# Firma yozuvi kamdan-kam o'zgaradi, so'rov esa ko'p. Kesh bo'lmasa
# har so'rov boshqaruv bazasiga bitta qo'shimcha zapros qilardi.
_FIRMA_KESH: dict[str, Firma] = {}


def firma_keshini_tozala(kod: str | None = None) -> None:
    """Holat/tarif o'zgarganda chaqiriladi (masalan muzlatilganda)."""
    if kod:
        _FIRMA_KESH.pop(kod, None)
    else:
        _FIRMA_KESH.clear()


def firma_top(kod: str) -> Firma | None:
    """Kod bo'yicha firmani boshqaruv bazasidan topadi."""
    if kod in _FIRMA_KESH:
        return _FIRMA_KESH[kod]
    from .platforma.db import BoshqaruvSession
    from .platforma import models as pm
    db = BoshqaruvSession()
    try:
        y = db.query(pm.Firma).filter(pm.Firma.kod == kod).first()
        if y is None or y.holat == "ochirilgan":
            return None
        f = Firma(id=y.id, kod=y.kod, baza_nomi=y.baza_nomi,
                  yozish_mumkinmi=y.yozish_mumkinmi)
        _FIRMA_KESH[kod] = f
        return f
    finally:
        db.close()


def sorovdan_firma(host: str, sarlavha_kod: str = "") -> Firma | None:
    kod = kod_ajrat(host) or (sarlavha_kod or "").strip().lower() or None
    return firma_top(kod) if kod else None
