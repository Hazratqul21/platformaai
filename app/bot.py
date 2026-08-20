"""Telegram bot (aiogram 3) — TZ 1.3 tasdiqlash zanjiri.

HAR AKKAUNT O'Z BOTI bilan ishlaydi: token boshqaruv bazasidagi
`Akkaunt.bot_token` da, Mini App manzili `webapp_url` da. Sabab —
har korxona mijozlariga O'Z nomidan yozishi kerak, umumiy bot emas.

Har akkaunt uchun alohida thread + alohida asyncio halqasi ishga
tushadi va o'sha thread ichida `tenancy` konteksti O'RNATILADI —
shuning uchun handler ichidagi `sessiya()` avtomat TO'G'RI akkaunt
bazasiga boradi (contextvars thread bo'yicha ajratilgan).

Ijarachiliksiz rejimda eski yo'l saqlanadi: `.env` dagi BOT_TOKEN.
"""
import asyncio
import logging
import os
from decimal import Decimal

from .db import SessionLocal, sessiya
from . import models as m
from . import domain
from .domain import soha_oqi

log = logging.getLogger("gofra.bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")


def joriy_token() -> tuple[str, str]:
    """(bot_token, webapp_url) — JORIY akkauntniki, yo'q bo'lsa `.env` dan.

    So'rov ichida chaqiriladi (tenancy o'rnatilgan), shuning uchun
    akkauntni contextvar dan oladi."""
    try:
        from . import tenancy
        a = tenancy.joriy() if tenancy.yoqilganmi() else None
        if a:
            from .platforma.db import BoshqaruvSession
            from .platforma import models as pm
            bdb = BoshqaruvSession()
            try:
                akk = bdb.get(pm.Akkaunt, a.id)
                if akk and akk.bot_token:
                    return akk.bot_token, (akk.webapp_url or "")
            finally:
                bdb.close()
            return "", ""          # akkaunt bor, lekin token qo'ymagan
    except Exception:                                  # noqa: BLE001
        log.warning("Bot tokenini olishda xato")
    return BOT_TOKEN, WEBAPP_URL


def notify_order(order_id: int):
    """Menejer buyurtma yaratganda mijozga smeta yuborish (bot ishlayotgan bo'lsa)."""
    token, _ = joriy_token()
    if not token:
        return
    from aiogram import Bot
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    async def send():
        db = sessiya()
        try:
            o = db.get(m.Order, order_id)
            if not o or not o.client.telegram_chat_id:
                return
            bot = Bot(token)
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"ok:{o.id}"),
                InlineKeyboardButton(text="💬 Muzokara", callback_data=f"neg:{o.id}"),
            ]])
            text = (
                f"📦 Yangi smeta — Buyurtma #{o.id}\n\n"
                f"O'lcham: {domain.olcham_matni(o)} mm\n"
                f"Qavat: {soha_oqi(o, 'layers')} · Marka: {soha_oqi(o, 'grade')}\n"
                f"Soni: {o.qty:,} dona\n"
                f"Narx: {float(o.unit_price):,.0f} so'm/dona\n"
                f"💰 Jami: {float(o.total):,.0f} so'm"
            ).replace(",", " ")
            await bot.send_message(o.client.telegram_chat_id, text, reply_markup=kb)
            await bot.session.close()
        finally:
            db.close()

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send())
    except RuntimeError:
        asyncio.run(send())


async def run_bot(token: str = "", webapp_url: str = ""):
    """Bitta akkauntning botini yuritadi.

    `token` berilmasa `.env` dagi ishlatiladi (yagona rejim)."""
    token = token or BOT_TOKEN
    webapp_url = webapp_url or WEBAPP_URL
    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import CommandStart
    from aiogram.types import (
        Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
        MenuButtonWebApp, WebAppInfo,
    )

    bot = Bot(token)
    dp = Dispatcher()

    if webapp_url:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="ERP ochish",
                                         web_app=WebAppInfo(url=webapp_url)))

    @dp.message(CommandStart())
    async def start(msg: Message):
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True)
        await msg.answer(
            "Assalomu alaykum! TIZIM botiga xush kelibsiz.\n"
            "Profilingizni bog'lash uchun telefon raqamingizni yuboring:", reply_markup=kb)

    @dp.message(F.contact)
    async def contact(msg: Message):
        phone = msg.contact.phone_number.lstrip("+")
        db = sessiya()
        try:
            client = None
            for c in db.query(m.Client).all():
                if c.phone and c.phone.replace("+", "").replace(" ", "").endswith(phone[-9:]):
                    client = c
                    break
            if client:
                client.telegram_chat_id = str(msg.chat.id)
                db.commit()
                await msg.answer(f"✅ {client.company} profiliga bog'landingiz.\n"
                                 "Endi smeta va buyurtma statuslari shu yerga keladi.")
            else:
                await msg.answer("❌ Bu raqam tizimda topilmadi. Menejer bilan bog'laning.")
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("ok:"))
    async def confirm(cb: CallbackQuery):
        oid = int(cb.data.split(":")[1])
        db = sessiya()
        try:
            o = db.get(m.Order, oid)
            if not o:
                await cb.answer("Буюртма топилмади", show_alert=True)
                return
            if o.client.telegram_chat_id != str(cb.from_user.id):
                await cb.answer("Sizga tegishli emas", show_alert=True)
                return
                
            if domain.manosi(o.status) in ("boshlanish", "muzokara"):
                from . import services as s
                brak = Decimal("1") + s.dset(db, "brak_percent") / 100
                xom, marka = domain.xomashyo_kerak(o)
                if xom is None:
                    return   # bu sohada avtomatik spisaniya yo'q
                need = (xom * brak).quantize(Decimal("0.0001"))
                try:
                    s.fifo_writeoff(db, marka, need, order_id=o.id,
                                    note=f"Bot orqali tasdiqlash (Buyurtma #{o.id})")
                except ValueError as e:
                    db.add(m.AuditLog(who=o.client.company, action="Bot: xomashyo yetmadi",
                                      detail=f"Buyurtma #{o.id}: {e}"))
                    db.commit()
                    await cb.message.edit_text(cb.message.text + "\n\n⚠️ XOMASHYO YETMADI — menejerga xabar berildi")
                    await cb.answer("Xomashyo yetarli emas!", show_alert=True)
                    return
                
                o.status = domain.status_nomi("ishlab_chiqarish")
                db.add(m.AuditLog(who=o.client.company, action="Bot: tasdiqlandi",
                                  detail=f"Buyurtma #{o.id} ishlab chiqarishga berildi"))
                db.commit()
                await cb.message.edit_text(cb.message.text + "\n\n✅ TASDIQLANDI — ishlab chiqarishga berildi")
            await cb.answer("Tasdiqlandi!")
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("neg:"))
    async def negotiate(cb: CallbackQuery):
        oid = int(cb.data.split(":")[1])
        db = sessiya()
        try:
            o = db.get(m.Order, oid)
            if not o:
                await cb.answer("Буюртма топилмади", show_alert=True)
                return
            if o.client.telegram_chat_id != str(cb.from_user.id):
                await cb.answer("Sizga tegishli emas", show_alert=True)
                return
                
            if domain.manosi(o.status) == "boshlanish":
                o.status = domain.status_nomi("muzokara")
                db.add(m.AuditLog(who=o.client.company, action="Bot: muzokara",
                                  detail=f"Buyurtma #{o.id} — mijoz narxga rozi emas, menejerga xabar"))
                db.commit()
                await cb.message.edit_text(cb.message.text + "\n\n💬 MUZOKARA — menejer siz bilan bog'lanadi")
            await cb.answer("Menejerga xabar yuborildi")
        finally:
            db.close()

    log.info("Telegram bot polling boshlandi")
    # bot alohida thread'da ishlaydi — signal ushlagichlarini o'rnatib bo'lmaydi
    # (ular faqat asosiy thread'da ishlaydi), shuning uchun o'chirib qo'yiladi
    await dp.start_polling(bot, handle_signals=False)


# ---------------------------------------------------------------------
# BOT MENEJERI — har akkauntga alohida bot
# ---------------------------------------------------------------------
# Ishlab turgan botlar: baza_nomi -> thread. Token o'zgarganda eski
# thread to'xtatiladi va yangisi ishga tushadi.
_BOTLAR: dict[str, dict] = {}


def _akkaunt_boti_boshla(akkaunt, token: str, webapp_url: str) -> None:
    """Bitta akkaunt uchun bot thread'ini ishga tushiradi.

    MUHIM: `tenancy.ornat()` THREAD ICHIDA chaqiriladi — contextvars
    thread bo'yicha ajratilgan, shuning uchun handler ichidagi
    `sessiya()` avtomat shu akkauntning bazasiga boradi."""
    import threading
    from . import tenancy

    kalit = akkaunt.baza_nomi
    eski = _BOTLAR.get(kalit)
    if eski and eski.get("token") == token:
        return                       # allaqachon shu token bilan ishlayapti

    def runner():
        # Kontekst SHU thread uchun o'rnatiladi va umrbod turadi
        tenancy.ornat(akkaunt)
        try:
            asyncio.run(run_bot(token, webapp_url))
        except Exception as e:                        # noqa: BLE001
            log.warning("«%s» boti to'xtadi: %s", akkaunt.kod, str(e)[:150])

    t = threading.Thread(target=runner, daemon=True,
                         name=f"bot-{akkaunt.kod}")
    t.start()
    _BOTLAR[kalit] = {"token": token, "thread": t, "kod": akkaunt.kod}
    log.info("«%s» akkaunt boti ishga tushdi", akkaunt.kod)


def akkaunt_botlarini_boshla() -> int:
    """Boshqaruv bazasidan tokeni bor akkauntlarni olib, botlarini
    ishga tushiradi. Yangi token qo'shilganda ham chaqiriladi."""
    from . import tenancy
    from .platforma.db import BoshqaruvSession
    from .platforma import models as pm

    n = 0
    bdb = BoshqaruvSession()
    try:
        for akk in bdb.query(pm.Akkaunt).filter(
                pm.Akkaunt.bot_token != "",
                pm.Akkaunt.holat != "ochirilgan").all():
            _akkaunt_boti_boshla(
                tenancy.Akkaunt(id=akk.id, kod=akk.kod,
                                baza_nomi=akk.baza_nomi,
                                yozish_mumkinmi=akk.yozish_mumkinmi),
                akk.bot_token, akk.webapp_url or "")
            n += 1
    finally:
        bdb.close()
    return n


def start_bot_bg():
    """Server startup'da botlarni ishga tushirish.

    Ijarachilikda — har akkauntga alohida bot. Aks holda `.env`
    dagi yagona BOT_TOKEN (eski yo'l)."""
    from . import tenancy
    if tenancy.yoqilganmi():
        try:
            n = akkaunt_botlarini_boshla()
            log.info("Ijarachilik: %d akkaunt boti ishga tushdi", n)
        except Exception as e:                        # noqa: BLE001
            log.warning("Akkaunt botlari boshlanmadi: %s", str(e)[:150])
        return

    if not BOT_TOKEN:
        log.info("BOT_TOKEN yo'q — bot o'chirilgan (faqat web rejim)")
        return
    import threading

    def runner():
        asyncio.run(run_bot())

    threading.Thread(target=runner, daemon=True, name="gofra-bot").start()
