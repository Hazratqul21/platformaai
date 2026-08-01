"""SOHA QATLAMI — biznes turiga xos maydonlar va matnlar.

YADRO (Order, Client, Payment, kassa, ombor...) bu maydonlarning MA'NOSINI
bilmaydi. U shunchaki `order.attributes` ni saqlaydi, ko'rsatadi va eksport
qiladi. «Uzunlik 300 mm» nimani anglatishini faqat shu qatlam biladi.

PROFIL KODDA EMAS, BAZADA (`SohaProfil` jadvali). `app/profiles/*.json`
fayllari faqat BOSHLANG'ICH shablon — birinchi ishga tushishda bazaga
ko'chiriladi, keyin haqiqat bazada bo'ladi. Shuning uchun yangi soha
qo'shish uchun **kod yozish kerak emas**: yozuv qo'shiladi, xolos.
AI agent (4-bosqich) aynan shu yozuvni to'ldiradi.

KESHLASH HAQIDA — 2-BOSQICH UCHUN OGOHLANTIRISH:
Faol profil modul darajasida keshlanadi (`_KESH`), chunki har so'rovda
JSON qayta tahlil qilish isrof. Bu **bitta jarayon = bitta baza** deb
faraz qiladi. 2-bosqichda («har mijozga alohida baza») agar bitta jarayon
bir nechta mijozga xizmat qilsa, kesh mijoz bo'yicha kalitlanishi SHART —
aks holda bir mijozning profili boshqasiga ko'rinadi.
"""
import json
import logging
import os
from decimal import Decimal

log = logging.getLogger("gofra.domain")

SHABLON_PAPKA = os.path.join(os.path.dirname(__file__), "profiles")
MODUL_PAPKA = os.path.join(os.path.dirname(__file__), "modules")

# ---------------------------------------------------------------------
# MODUL — buyurtmaning HAYOT SIKLI (statuslar, o'tishlar, rollar)
#
# Nega profildan alohida: «non zavodi» va «mebel sexi» — ikki xil SOHA,
# lekin bitta ISH TARTIBI (buyurtma -> sexga -> tayyor -> topshirildi).
# Agar status har profilda takrorlansa, 20 profilda 20 marta bir xil
# oqim yozilardi va bittasida xato bo'lsa topib bo'lmasdi.
#
# Odoo'da bu «app», 1C da «конфигурация», SAP da «industry solution».
# Bizda: MODUL = ish tartibi, PROFIL = mahsulot ta'rifi.
#
# Yadro status NOMINI emas, MA'NOSINI biladi:
#   boshlanish  muzokara  ishlab_chiqarish  tayyor  topshirildi  bekor
# Shu tufayli «Sexda kesilmoqda» ham, «Yig'ilmoqda» ham, «Tuzatilmoqda»
# ham bir xil ishlaydi — xomashyo o'sha yerda yechiladi.
# ---------------------------------------------------------------------

MANOLAR = ("boshlanish", "muzokara", "ishlab_chiqarish", "tayyor",
           "topshirildi", "bekor")


class Status:
    def __init__(self, nom: str, mano: str, keyingi=None, rollar=None):
        if mano not in MANOLAR:
            raise ValueError(f"'{nom}': noma'lum ma'no '{mano}'. "
                             f"Mumkin: {', '.join(MANOLAR)}")
        self.nom = nom          # foydalanuvchi ko'radigan va bazaga yoziladigan
        self.mano = mano        # yadro shu bo'yicha qaror qabul qiladi
        self.keyingi = keyingi or []
        self.rollar = rollar or []


class Modul:
    def __init__(self, tarif: dict):
        self.kalit = tarif["kalit"]
        self.nom = tarif.get("nom", self.kalit)
        self.izoh = tarif.get("izoh", "")
        self.statuslar = [Status(**s) for s in tarif["statuslar"]]
        self._nom_indeks = {s.nom: s for s in self.statuslar}
        self._mano_indeks = {}
        for s in self.statuslar:
            self._mano_indeks.setdefault(s.mano, s)
        yetishmaydi = {"boshlanish", "bekor"} - set(self._mano_indeks)
        if yetishmaydi:
            raise ValueError(f"'{self.kalit}' modulida majburiy ma'no yo'q: "
                             f"{', '.join(sorted(yetishmaydi))}")

    def status(self, nom: str) -> Status | None:
        return self._nom_indeks.get(nom)

    def mano(self, nom: str) -> str | None:
        s = self._nom_indeks.get(nom)
        return s.mano if s else None

    def mano_boyicha(self, mano: str) -> Status | None:
        return self._mano_indeks.get(mano)

    @property
    def nomlar(self) -> list[str]:
        return [s.nom for s in self.statuslar]


def modullar() -> dict[str, dict]:
    """app/modules/*.json — ish tartibi ta'riflari."""
    natija = {}
    if not os.path.isdir(MODUL_PAPKA):
        return natija
    for nom in sorted(os.listdir(MODUL_PAPKA)):
        if nom.endswith(".json"):
            with open(os.path.join(MODUL_PAPKA, nom), encoding="utf-8") as f:
                tarif = json.load(f)
            Modul(tarif)   # buzuq modul ishga tushishda bilinsin
            natija[tarif["kalit"]] = tarif
    return natija


ZAXIRA_MODUL = "ishlab_chiqarish"

# Maydon turlari va ularning JSON dagi ko'rinishi:
#
#   "butun"  -> int      JSON: son
#   "matn"   -> str      JSON: satr
#   "mantiq" -> bool     JSON: true/false
#   "kasr"   -> Decimal  JSON: SATR ("12.3400")
#
# Nega `kasr` satr sifatida saqlanadi: JSON da faqat float bor, float esa
# aniqlikni yo'qotadi. Bu loyihada pul va o'lchov ataylab `Decimal` —
# `models.py` da "barcha pul summalari uchun DECIMAL — float ishlatilmaydi"
# deb yozilgan. JSON ga float qilib tashlasak o'sha qoida buzilardi.
TURLAR = ("butun", "matn", "mantiq", "kasr")


class Maydon:
    """Bitta soha maydonining ta'rifi."""

    def __init__(self, kalit: str, nom: str, tur: str, birlik: str = "",
                 standart=None, min=None, max=None, variantlar=None,
                 majburiy: bool = False, hisoblanadi: bool = False, **_):
        if tur not in TURLAR:
            raise ValueError(f"'{kalit}': noma'lum tur '{tur}'. "
                             f"Mumkin: {', '.join(TURLAR)}")
        self.kalit = kalit      # attributes dagi kalit
        self.nom = nom          # foydalanuvchiga ko'rinadigan nom
        self.tur = tur
        self.birlik = birlik    # mm, m², g, dona... (bo'sh bo'lishi mumkin)
        self.standart = standart      # foydalanuvchi bermasa shu ishlatiladi
        self.min = min                # raqamli chegara (ikkalasi ixtiyoriy)
        self.max = max
        self.variantlar = variantlar  # ruxsat etilgan qiymatlar ro'yxati
        self.majburiy = majburiy      # bo'sh bo'lmasin
        # `hisoblanadi` — foydalanuvchi kiritmaydi, tizim hisoblaydi
        # (karton: m2_per_box formuladan). Validatsiya bunday maydonni
        # so'ramaydi, aks holda «majburiy maydon yo'q» deb rad etardi.
        self.hisoblanadi = hisoblanadi

    def tekshir(self, qiymat) -> str | None:
        """Xato matnini qaytaradi, xato bo'lmasa None."""
        if qiymat is None or qiymat == "":
            return f"«{self.nom}» to'ldirilsin" if self.majburiy else None
        try:
            qiymat = self.json_dan(qiymat)
        except (ValueError, TypeError, ArithmeticError):
            return f"«{self.nom}» qiymati noto'g'ri"
        if self.majburiy and self.tur == "matn" and not str(qiymat).strip():
            return f"«{self.nom}» to'ldirilsin"
        if self.variantlar is not None and qiymat not in self.variantlar:
            mumkin = ", ".join(str(v) for v in self.variantlar)
            return f"«{self.nom}» noto'g'ri. Mumkin: {mumkin}"
        if self.min is not None and qiymat < self.min:
            return f"«{self.nom}» {self.min} dan kam bo'lmasin"
        if self.max is not None and qiymat > self.max:
            return f"«{self.nom}» {self.max} dan katta bo'lmasin"
        return None

    def json_ga(self, qiymat):
        """Python qiymatini JSON saqlashga yaroqli holga keltiradi."""
        if qiymat is None:
            return None
        if self.tur == "kasr":
            return str(Decimal(str(qiymat)))
        if self.tur == "butun":
            return int(qiymat)
        if self.tur == "mantiq":
            return bool(qiymat)
        return str(qiymat)

    def json_dan(self, qiymat):
        """JSON dagi qiymatni Python turiga qaytaradi."""
        if qiymat is None:
            return None
        if self.tur == "kasr":
            return Decimal(str(qiymat))
        if self.tur == "butun":
            return int(qiymat)
        if self.tur == "mantiq":
            return bool(qiymat)
        return str(qiymat)


class Profil:
    """Bitta soha profili — maydonlar + mahsulotni so'z bilan tasvirlash."""

    def __init__(self, tarif: dict):
        self.kalit = tarif["kalit"]
        self.nom = tarif.get("nom", self.kalit)
        self.izoh = tarif.get("izoh", "")
        self.maydonlar = [Maydon(**md) for md in tarif["maydonlar"]]
        self.matnlar = tarif.get("matnlar", {})
        self.hosila = tarif.get("hosila", {})
        self.narx = tarif.get("narx", {"usul": "qolda"})
        # Xomashyo iste'moli. Bo'sh bo'lsa — bu soha uchun ombordan
        # avtomatik spisaniya YO'Q (non zavodi: un hisobi hali yozilmagan).
        # Yadro shunda spisaniyani o'tkazib yuboradi, buyurtma esa
        # oddiy ishlayveradi.
        self.xomashyo = tarif.get("xomashyo", {})
        # Qaysi ish tartibi bilan ishlaydi (app/modules/*.json)
        self.modul_kaliti = tarif.get("modul", ZAXIRA_MODUL)
        self.modul: Modul | None = None   # yuklanganda to'ldiriladi
        self._indeks = {md.kalit: md for md in self.maydonlar}
        if len(self._indeks) != len(self.maydonlar):
            raise ValueError(f"'{self.kalit}' profilida takroriy maydon kaliti bor")

    @property
    def kalitlar(self) -> list[str]:
        return [md.kalit for md in self.maydonlar]

    def maydon(self, kalit: str) -> Maydon:
        md = self._indeks.get(kalit)
        if md is None:
            raise KeyError(f"'{kalit}' — '{self.kalit}' profilida yo'q maydon")
        return md


# ---------------------------------------------------------------------
# Shablonlar va faol profil
# ---------------------------------------------------------------------

def shablonlar() -> dict[str, dict]:
    """app/profiles/*.json — boshlang'ich shablonlar (bazaga ko'chiriladi)."""
    natija = {}
    if not os.path.isdir(SHABLON_PAPKA):
        return natija
    for nom in sorted(os.listdir(SHABLON_PAPKA)):
        if not nom.endswith(".json"):
            continue
        with open(os.path.join(SHABLON_PAPKA, nom), encoding="utf-8") as f:
            tarif = json.load(f)
        Profil(tarif)   # tuzilishini darrov tekshiramiz — buzuq shablon
        natija[tarif["kalit"]] = tarif   # ishga tushishda bilinsin
    return natija


ZAXIRA_KALIT = "karton"   # baza bo'sh bo'lsa ishlatiladigan profil

_KESH: Profil | None = None


def qayta_yukla(db=None) -> Profil:
    """Faol profilni bazadan o'qib keshga qo'yadi. Baza bo'sh bo'lsa —
    shablondan (`ZAXIRA_KALIT`)."""
    global _KESH
    tarif = None
    if db is not None:
        from . import models as m
        yozuv = db.query(m.SohaProfil).filter(m.SohaProfil.faol.is_(True)).first()
        if yozuv:
            tarif = json.loads(yozuv.tarif_json)
    if tarif is None:
        tarif = shablonlar().get(ZAXIRA_KALIT)
        if tarif is None:
            raise RuntimeError(
                f"Faol profil ham, '{ZAXIRA_KALIT}' shabloni ham topilmadi")
    p = Profil(tarif)
    hamma_modul = modullar()
    modul_tarif = hamma_modul.get(p.modul_kaliti) or hamma_modul.get(ZAXIRA_MODUL)
    if modul_tarif is None:
        raise RuntimeError(f"'{p.modul_kaliti}' moduli ham, zaxira "
                           f"'{ZAXIRA_MODUL}' ham topilmadi")
    p.modul = Modul(modul_tarif)
    _KESH = p
    log.info("Soha profili: %s (%s) · ish tartibi: %s",
             p.nom, p.kalit, p.modul.nom)
    return _KESH


def profil() -> Profil:
    """Hozirgi faol profil."""
    if _KESH is None:
        return qayta_yukla(None)
    return _KESH


def modul() -> Modul:
    """Hozirgi ish tartibi (statuslar)."""
    return profil().modul


def manosi(status_nomi: str) -> str | None:
    """Bazadagi status nomining MA'NOsi. Yadro shu bo'yicha qaror qiladi.

    `None` qaytishi mumkin: buyurtma boshqa modulda yozilgan status bilan
    qolgan bo'lsa (profil almashtirilgan). Chaqiruvchi buni «noma'lum»
    deb qabul qilishi kerak, yiqilmasligi.
    """
    return modul().mano(status_nomi)


def status_nomi(mano: str) -> str | None:
    """Ma'noga mos status nomi — «ishlab_chiqarish» -> «Sexda kesilmoqda»."""
    s = modul().mano_boyicha(mano)
    return s.nom if s else None


def boshlangich_status() -> str:
    """Yangi buyurtma qaysi maqomdan boshlanadi."""
    return status_nomi("boshlanish")


def statuslar(*manolar: str) -> list[str]:
    """Berilgan ma'nolarga mos status NOMLARI — SQL filtrlari uchun.

    Masalan `statuslar("ishlab_chiqarish", "tayyor", "topshirildi")`
    kartonda `["Sexda kesilmoqda","Omborga tushdi","Yetkazib berildi"]`,
    savdoda `["Yig'ilmoqda","Jo'natishga tayyor","Topshirildi"]` beradi.
    """
    kerak = set(manolar)
    return [s.nom for s in modul().statuslar if s.mano in kerak]


# ---------------------------------------------------------------------
# Kiruvchi qiymatlarni tayyorlash: standart -> hosila -> tekshiruv
#
# Ilgari bularning hammasi `orders.py` da karton uchun qattiq yozilgan edi
# (`validate_box`, `tur_layers`, `is_offset=(tur=="Офсет")`). Endi profil
# ma'lumoti hal qiladi — yadro qaysi soha ekanini bilmaydi.
# ---------------------------------------------------------------------

def standartlar(qiymatlar: dict) -> dict:
    """Berilmagan maydonlarga profil standartini qo'yadi."""
    natija = dict(qiymatlar)
    for md in profil().maydonlar:
        if natija.get(md.kalit) is None and md.standart is not None:
            natija[md.kalit] = md.standart
    return natija


def hosila_hisobla(qiymatlar: dict) -> dict:
    """Boshqa maydondan kelib chiqadigan qiymatlarni to'ldiradi.

    Ikki qoida yetarli bo'ldi:
      "jadval" — manba qiymatiga qarab lug'atdan olinadi
                 (karton: tur "3 слой" -> layers 3)
      "teng"   — manba shu qiymatga tengmi (mantiq)
                 (karton: tur=="Офсет" -> is_offset)

    Hosila maydon HAR DOIM qayta hisoblanadi: foydalanuvchi `tur` ni
    o'zgartirsa `layers` eskisi bo'lib qolmasligi kerak.
    """
    natija = dict(qiymatlar)
    for kalit, qoida in profil().hosila.items():
        manba = natija.get(qoida.get("manba"))
        if "jadval" in qoida:
            natija[kalit] = qoida["jadval"].get(manba, qoida.get("standart"))
        elif "teng" in qoida:
            natija[kalit] = (manba == qoida["teng"])
    return natija


def tayyorla(qiymatlar: dict) -> tuple[dict, str | None]:
    """standart -> TEKSHIRUV -> hosila. `(qiymatlar, xato)` qaytaradi.

    Tartib muhim: tekshiruv hosiladan OLDIN. Aks holda foydalanuvchi
    yuborgan noto'g'ri qiymat (masalan karton uchun `layers=4`) hosila
    hisoblashda jimgina to'g'ri qiymatga almashib, xato bildirilmay
    qolardi. Avval yuborilgani rad etiladi, keyin hosila yasaladi.
    """
    q = standartlar(qiymatlar)
    xato = tekshir(q)
    if xato:
        return q, xato
    return hosila_hisobla(q), None


def tekshir(qiymatlar: dict) -> str | None:
    """Profil qoidalari bo'yicha tekshiradi. Birinchi xato matnini qaytaradi."""
    for md in profil().maydonlar:
        if md.hisoblanadi:
            continue
        xato = md.tekshir(qiymatlar.get(md.kalit))
        if xato:
            return xato
    return None


# ---------------------------------------------------------------------
# Order bilan ishlash
# ---------------------------------------------------------------------

def soha_yoz(order, qiymatlar: dict | None = None) -> None:
    """Soha maydonlarini `attributes` ga yozadi.

    `qiymatlar` berilsa — o'shandan; berilmasa eski ustunlardan (2-qadam
    «ikki joyga yozish» rejimi, ustunlar o'chirilgunicha).
    """
    if order.attributes is None:
        order.attributes = {}
    for md in profil().maydonlar:
        if qiymatlar is not None:
            xom = qiymatlar.get(md.kalit)
        else:
            xom = getattr(order, md.kalit, None)
        order.attributes[md.kalit] = md.json_ga(xom)


def soha_oqi(order, kalit: str, standart=None):
    """Soha maydonini `attributes` dan o'qiydi, to'g'ri Python turida.

    Profilda bunday maydon bo'lmasa — XATO EMAS, `standart` qaytadi.
    Sabab: profil endi o'zgaruvchan. «Non zavodi profilida `grade` yo'q»
    degani buzilish emas, oddiy hol — chaqiruvchi kod (ombor ro'yxati,
    mijoz kartochkasi) shunchaki bo'sh katak ko'rsatadi. Ilgari bu yerda
    `KeyError` ko'tarilardi va butun sahifa 500 bilan yiqilardi.
    """
    try:
        md = profil().maydon(kalit)
    except KeyError:
        return standart
    xom = (order.attributes or {}).get(kalit)
    if xom is None:
        return standart
    return md.json_dan(xom)


def soha_hammasi(order) -> dict:
    """Hamma soha maydonlari, Python turlarida."""
    return {md.kalit: soha_oqi(order, md.kalit) for md in profil().maydonlar}


def xomashyo_kerak(order):
    """Buyurtma uchun ombordan yechiladigan xomashyo — `(miqdor, marka)`.

    Profil `xomashyo` ni e'lon qilmagan bo'lsa `(None, None)` qaytadi va
    chaqiruvchi spisaniyani BUTUNLAY o'tkazib yuboradi. Non zavodida un
    hisobi hali yozilmagan — buyurtma esa shundan qat'i nazar ishlashi
    kerak, aks holda «har sohada ishlaydi» degani yolg'on bo'lardi.

    Brak foizi bu yerda QO'SHILMAYDI — u yadro sozlamasi (`brak_percent`),
    har sohada bor.
    """
    xs = profil().xomashyo
    if not xs:
        return None, None
    olcham = soha_oqi(order, xs.get("olcham_maydoni", ""))
    marka = soha_oqi(order, xs.get("marka_maydoni", ""))
    if olcham is None:
        return None, None
    return olcham * order.qty, marka


# ---------------------------------------------------------------------
# Mahsulotni SO'Z bilan tasvirlash — shablon bo'yicha
#
# Yadro (hisobot, chek, bot xabari, ombor ro'yxati) matnni O'ZI YIG'MAYDI,
# shu funksiyalardan so'raydi. Ilgari `f"{o.length_mm}×{o.width_mm}×..."`
# naqshi kod bo'ylab 8 joyda takrorlangan edi — har biri kartonni bilishga
# majbur edi.
# ---------------------------------------------------------------------

def _tuldir(shablon: str, qiymatlar: dict) -> str:
    """«{a}-қават, {b}, {c} рангли» shablonini to'ldiradi.

    QOIDA: vergul bilan ajratilgan bo'lak ichidagi biror maydon bo'sh
    (0, "", None) bo'lsa — o'sha bo'lak TUSHIB QOLADI. Shu tufayli
    «ranglar soni 0» bo'lganda «0 рангли босма» deb yozilmaydi, bo'lak
    umuman chiqmaydi. Ilgari buni har joyda `if o.colors` bilan qo'lda
    yozishga to'g'ri kelardi.
    """
    bolaklar = []
    for bolak in shablon.split(", "):
        kalitlar = [k.split("}")[0] for k in bolak.split("{")[1:]]
        if any(not qiymatlar.get(k) for k in kalitlar):
            continue
        try:
            bolaklar.append(bolak.format(**qiymatlar))
        except KeyError:
            continue   # profilda yo'q maydon — bo'lak tashlanadi
    return ", ".join(bolaklar)


def olcham_matni(order, ajratgich: str | None = None) -> str:
    """Karton: «300×200×150». Non: «600 g». Profil hal qiladi."""
    matn = _tuldir(profil().matnlar.get("olcham", ""), soha_hammasi(order))
    if ajratgich is not None:
        matn = matn.replace("×", ajratgich)
    return matn


def tur_matni(order) -> str:
    """Buyurtma turi. Bo'sh bo'lsa profil zaxira shablonidan tiklanadi
    (karton: eski yozuvlarda `tur` yo'q — qavatdan yasaladi)."""
    q = soha_hammasi(order)
    p = profil()
    return (_tuldir(p.matnlar.get("tur", ""), q)
            or _tuldir(p.matnlar.get("tur_zaxira", ""), q))


def tarkib_matni(order) -> str:
    """Karton: «3-қават, K1, 2 рангли босма». Non: «Bug'doy noni, oliy un»."""
    return _tuldir(profil().matnlar.get("tarkib", ""), soha_hammasi(order))


def mahsulot_matni(order, kalit: str = "hujjat_mahsulot") -> str:
    """Hujjatdagi to'liq mahsulot nomi — «Гофра қути 300×200×150 мм, ...».

    Mahsulot ATAMASI ham soha bilimi: karton «қути», non zavodida esa
    «нон». Ilgari bu so'z `reports.py` ga qattiq yozilgan edi, shuning
    uchun non buyurtmasining hujjatida ham «Картон қути» chiqardi.

    Shablonda maydonlardan tashqari `{olcham}` va `{tarkib}` ham
    ishlatiladi — ular yuqoridagi funksiyalardan keladi.
    """
    q = soha_hammasi(order)
    q["olcham"] = olcham_matni(order)
    q["tarkib"] = tarkib_matni(order)
    return _tuldir(profil().matnlar.get(kalit, ""), q)
