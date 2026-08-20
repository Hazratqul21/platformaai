"""Boshqaruv bazasining jadvallari — kim ro'yxatdan o'tgan, qancha sarfladi.

MIJOZNING ma'lumoti bu yerda YO'Q. Bu yerda faqat: qaysi akkaunt bor,
qaysi bazada, qaysi tarifda, AI ga qancha sarfladi.

Savol matni va AI javobi BU YERGA YOZILMAYDI — faqat metama'lumot
(model, token soni, narx). Sabab: mijozning biznes savoli bizning
markaziy bazamizda saqlanib qolmasin.
"""
from datetime import datetime

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, Numeric,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from .db import BoshqaruvBase

D = Numeric(18, 2)      # pul — float ishlatilmaydi (mijoz bazasidagi bilan bir xil)

# Akkaunt holati. `sinov` — ro'yxatdan o'tdi, hali to'lamadi.
# `muzlatilgan` — obuna tugadi: YOZISH to'xtaydi, O'QISH ochiq qoladi.
HOLATLAR = ["sinov", "faol", "muzlatilgan", "ochirilgan"]
TARIFLAR = ["boshlangich", "biznes", "korxona"]


class Akkaunt(BoshqaruvBase):
    """Bitta mijoz = bitta akkaunt = bitta ALOHIDA baza."""
    __tablename__ = "akkauntlar"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Subdomen: `mebelsex` -> mebelsex.innasoft.uz. Kichik harf, raqam, tire.
    kod: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(200))
    inn: Mapped[str] = mapped_column(String(20), default="")
    qqs_tolovchi: Mapped[bool] = mapped_column(Boolean, default=False)
    # Baza NOMI shu yerda saqlanadi, ulanish satri EMAS. Ulanish satri
    # serverning `.env` idagi shablondan yasaladi — parol bazada yotmasin.
    baza_nomi: Mapped[str] = mapped_column(String(63), unique=True)
    holat: Mapped[str] = mapped_column(String(20), default="sinov")
    tarif: Mapped[str] = mapped_column(String(20), default="boshlangich")
    yaratilgan: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    obuna_tugaydi: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Baza tayyorlanishi bir necha soniya — so'rov ichida qilinmaydi.
    # Frontend shu maydonni kuzatadi: `tayyorlanmoqda` -> `tayyor` / `xato`.
    tayyorlik: Mapped[str] = mapped_column(String(20), default="tayyorlanmoqda")
    tayyorlik_izohi: Mapped[str] = mapped_column(Text, default="")
    # TELEGRAM — har akkaunt O'Z botini qo'yadi (o'z mijozlariga o'z
    # nomidan yozadi). Token BOSHQARUV bazasida: bot menejeri hamma
    # akkauntning tokenini bir joydan o'qiy olishi kerak, aks holda
    # har mijoz bazasini ochib chiqish kerak bo'lardi.
    bot_token: Mapped[str] = mapped_column(String(120), default="")
    webapp_url: Mapped[str] = mapped_column(String(200), default="")

    @property
    def yozish_mumkinmi(self) -> bool:
        """Obuna tugagan akkaunt O'QIY oladi, lekin YOZA olmaydi.

        Ma'lumot garovga olinmaydi — bu qoida hujjatda ham yozilgan
        (docs/07-TARQATISH.md §7.7)."""
        return self.holat in ("sinov", "faol")


class PlatformaUser(BoshqaruvBase):
    """Ro'yxatdan o'tgan odam.

    MIJOZ bazasidagi `users` bilan ARALASHTIRILMAYDI: u yerda ERP
    rollari (Rahbar, Buxgalter...), bu yerda esa platformaga kirish.
    Bitta odam ikkala joyda ham bo'ladi.
    """
    __tablename__ = "platforma_userlar"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Telefon yoki email — ikkalasi ham kirish nomi bo'la oladi.
    login: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    parol_hash: Mapped[str] = mapped_column(String(128))
    ism: Mapped[str] = mapped_column(String(120), default="")
    akkaunt_id: Mapped[int | None] = mapped_column(ForeignKey("akkauntlar.id"),
                                                 nullable=True, index=True)
    platforma_roli: Mapped[str] = mapped_column(String(20), default="egasi")
    tasdiqlangan: Mapped[bool] = mapped_column(Boolean, default=False)
    yaratilgan: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlatformaToken(BoshqaruvBase):
    """Kirish tokeni BOSHQARUV bazasida turadi — mijoz bazasida emas.

    NEGA: tokenni tekshirish uchun avval QAYSI bazaga borishni bilish
    kerak, lekin buni tokendan bilamiz. Tovuq-tuxum. Token markaziy
    bazada bo'lsa, tugun yechiladi: token -> akkaunt -> akkaunt bazasi.
    """
    __tablename__ = "platforma_tokenlar"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("platforma_userlar.id"),
                                         index=True)
    akkaunt_id: Mapped[int | None] = mapped_column(ForeignKey("akkauntlar.id"),
                                                 nullable=True, index=True)
    tugaydi: Mapped[datetime] = mapped_column(DateTime)


class AiSarf(BoshqaruvBase):
    """Har AI so'rovi. Hisob shundan chiqadi.

    NARX QOTIRILADI. Provayder narxi keyin o'zgarsa ham eski hisob
    o'zgarmaydi — bu QQS stavkasini buyurtmada qotirish bilan bir xil
    naqsh, u yerda ishlagan (docs/07-TARQATISH.md §7.6).

    Savol matni saqlanmaydi.
    """
    __tablename__ = "ai_sarf"
    id: Mapped[int] = mapped_column(primary_key=True)
    akkaunt_id: Mapped[int] = mapped_column(ForeignKey("akkauntlar.id"), index=True)
    vaqt: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                           index=True)
    provayder: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(60))
    kirish_token: Mapped[int] = mapped_column(Integer, default=0)
    chiqish_token: Mapped[int] = mapped_column(Integer, default=0)
    # Qotirilgan narxlar: 1 mln token uchun so'mda, SARF PAYTIDAGI kurs bilan.
    # Ikkalasi ham saqlanadi — keyin hisobni qayta tekshirish uchun.
    kirish_narx_mln: Mapped[float] = mapped_column(D, default=0)
    chiqish_narx_mln: Mapped[float] = mapped_column(D, default=0)
    narx_som: Mapped[float] = mapped_column(D, default=0)
    agent: Mapped[str] = mapped_column(String(30), default="")
    user_login: Mapped[str] = mapped_column(String(120), default="")
    # Xato bergan so'rov ham YOZILADI — u ham token sarflaydi va pul turadi.
    muvaffaqiyat: Mapped[bool] = mapped_column(Boolean, default=True)


class AiLimit(BoshqaruvBase):
    """Akkaunt o'zi qo'yadigan oylik chegara.

    Limit tugasa AI to'xtaydi, ERP ISHLAYVERADI — bu qat'iy qoida.
    """
    __tablename__ = "ai_limitlar"
    id: Mapped[int] = mapped_column(primary_key=True)
    akkaunt_id: Mapped[int] = mapped_column(ForeignKey("akkauntlar.id"), index=True)
    oy: Mapped[str] = mapped_column(String(7))          # "2026-08"
    limit_som: Mapped[float] = mapped_column(D, default=0)   # 0 = cheklovsiz
    ogoh_yuborildi: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("akkaunt_id", "oy", name="uq_limit_oy"),)


class PlatformaAudit(BoshqaruvBase):
    """Akkaunt yaratildi/muzlatildi, tarif o'zgardi, limit oshirildi — kim qildi."""
    __tablename__ = "platforma_audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    vaqt: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                           index=True)
    akkaunt_id: Mapped[int | None] = mapped_column(ForeignKey("akkauntlar.id"),
                                                 nullable=True, index=True)
    amal: Mapped[str] = mapped_column(String(60))
    kim: Mapped[str] = mapped_column(String(120), default="")
    tafsilot: Mapped[str] = mapped_column(Text, default="")


class AgentShablon(BoshqaruvBase):
    """Platforma darajasidagi agent ko'rsatmasi — HAMMA akkauntga.

    Biz AI ni yaxshilaganda kod qayta joylanmasin: shu jadvalga yozamiz
    va hamma akkaunt yangi ko'rsatmani oladi. Akkauntning o'z sozlamasi
    bo'lsa — u ustun turadi (`app/korsatma.py`).
    """
    __tablename__ = "agent_shablon"
    id: Mapped[int] = mapped_column(primary_key=True)
    kalit: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    korsatma: Mapped[str] = mapped_column(Text)
    kim: Mapped[str] = mapped_column(String(120), default="")
    ozgartirilgan: Mapped[datetime] = mapped_column(DateTime,
                                                    default=datetime.utcnow)
