"""Telegram bot (aiogram 3) — TZ 1.3 tasdiqlash zanjiri.

BOT_TOKEN .env da bo'lsa server bilan birga polling rejimida ishga tushadi.
Mini App: bot menyusiga WEBAPP_URL tugmasi qo'yiladi.
"""
import asyncio
import logging
import os
from decimal import Decimal

from .db import SessionLocal
from . import models as m
from . import domain
from .domain import soha_oqi

log = logging.getLogger("gofra.bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")


def notify_order(order_id: int):
    """Menejer buyurtma yaratganda mijozga smeta yuborish (bot ishlayotgan bo'lsa)."""
    if not BOT_TOKEN:
        return
    from aiogram import Bot
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    async def send():
        db = SessionLocal()
        try:
            o = db.get(m.Order, order_id)
            if not o or not o.client.telegram_chat_id:
                return
            bot = Bot(BOT_TOKEN)
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


async def run_bot():
    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import CommandStart
    from aiogram.types import (
        Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
        MenuButtonWebApp, WebAppInfo,
    )

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    if WEBAPP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="ERP ochish", web_app=WebAppInfo(url=WEBAPP_URL)))

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
        db = SessionLocal()
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
        db = SessionLocal()
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
        db = SessionLocal()
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


def start_bot_bg():
    """Server startup'da alohida thread'da botni ishga tushirish."""
    if not BOT_TOKEN:
        log.info("BOT_TOKEN yo'q — bot o'chirilgan (faqat web rejim)")
        return
    import threading

    def runner():
        asyncio.run(run_bot())

    threading.Thread(target=runner, daemon=True, name="gofra-bot").start()
