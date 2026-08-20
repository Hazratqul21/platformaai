# 033 — HAR AKKAUNT O'Z TELEGRAM BOTI VA MINI APP

**Sana:** 2026-08-20
**Holat:** ✅ ishlaydi — egasi o'z tokenini qo'yadi, bot darhol ishga tushadi

---

## Muammo

`bot.py` bitta `.env` dagi `BOT_TOKEN` bilan, bitta thread'da, bitta
bazaga yozardi. Ko'p akkauntda bu **noto'g'ri**: har korxona
mijozlariga **o'z nomidan** yozishi kerak, umumiy bot emas. Mini App
ham har akkauntning subdomeniga ochilishi kerak.

Bu A-bosqichda belgilangan uchta global holatdan biri edi
([../A-IJARACHILIK.md](../A-IJARACHILIK.md) §A.4).

---

## Yechim

### 1. Token boshqaruv bazasida

`Akkaunt.bot_token` + `Akkaunt.webapp_url`.

**Nega boshqaruv bazasida (mijoz bazasida emas):** bot menejeri
startupda HAMMA akkauntning tokenini bir joydan o'qiy olishi kerak —
aks holda har mijoz bazasini navbatma-navbat ochib chiqish kerak
bo'lardi.

### 2. Har akkauntga alohida thread + kontekst

```python
def runner():
    tenancy.ornat(akkaunt)        # KONTEKST SHU THREAD UCHUN
    asyncio.run(run_bot(token, webapp_url))
```

**Nozik joy:** `contextvars` **thread bo'yicha ajratilgan**, va
asyncio vazifalari yaratilganda kontekstni nusxalaydi. Shuning uchun
thread boshida bir marta o'rnatilgan akkaunt handler ichidagi
`sessiya()` ga avtomat yetadi — har handler'ga argument uzatish
kerak emas.

`bot.py` dagi hamma `SessionLocal()` → `sessiya()` (tenant-aware).

### 3. `notify_order` ham akkaunt tokenidan

`joriy_token()` — so'rov ichida (tenancy o'rnatilgan) joriy
akkauntning tokenini oladi. Akkaunt bor, lekin token qo'ymagan
bo'lsa — jim o'tkazadi (xato emas).

### 4. Ekran: Sozlamalar → Обуна ва AI сарфи

BotFather yo'riqnomasi (3 qadam), token maydoni, Mini App manzili
(subdomen avtomat taklif qilinadi), holat yorlig'i (ishlayapti /
to'xtagan / qo'yilmagan), o'chirish tugmasi.

---

## Xavfsizlik

| Qaror | Sabab |
|---|---|
| Token **to'liq qaytarilmaydi** — faqat `…ghij` (oxirgi 4) | ekranni ko'rgan odam botni o'g'irlab keta olmasin |
| Token shakli tekshiriladi (`\d{6,}:[A-Za-z0-9_-]{30,}`) | noto'g'ri token bilan bot **jim yiqilardi** — endi darhol aytiladi |
| Faqat `Rahbar` | bot — akkaunt darajasidagi infratuzilma |

---

## Isbot

```
noto'g'ri token       -> 400 «Token shakli noto'g'ri…»
to'g'ri shakl (soxta) -> {"ok":true,"ishga_tushdi":true}
holat                 -> bor:True oxiri:…ghij ishlayapti:True
bo'sh token           -> «Bot o'chirildi»
```

Boshqaruv bazasiga `bot_token`/`webapp_url` ustunlari qo'shildi
(`ALTER TABLE … IF NOT EXISTS`).

himoya_audit 164/164.

---

## Qoldi

- Bot to'xtatish (hozir eski thread token o'zgarganda ham ishlab
  turadi — daemon thread, jarayon qayta ishga tushganda tozalanadi).
  Toza to'xtatish uchun `dp.stop_polling()` signali kerak.
