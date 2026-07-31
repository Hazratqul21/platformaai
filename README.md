# TIZIM — Ishlab Chiqarish Sexi uchun Mini-ERP

Texnik topshiriq (INNASOFT, v1.0) bo'yicha qurilgan tizim: CRM + smeta kalkulyatori,
ombor (FIFO, 5% brak), HR/ishbay oylik, unit-ekonomika, debitor/kreditor, eksport
va Telegram bot (tasdiqlash zanjiri + Mini App).

## Ishga tushirish

Talab: **Python 3.10+** (run.sh o'zi eng yangisini topadi).

```bash
./run.sh               # STANDART: Excel ma'lumotlaringiz bilan boshlanadi
SEED_DEMO=1 ./run.sh   # DEMO: sinov ma'lumotlari bilan (o'rganish uchun)
SEED_EMPTY=1 ./run.sh  # BO'SH: noldan boshlash
```

Birinchi ishga tushirishda mijozning ikkala Excel'i avtomatik yuklanadi
(106 xarid + 91 kassa yozuvi) — hech narsani qaytadan kiritish shart emas,
Excel'dagi ishni tizimda davom ettirasiz.

**Poligrafiya modullari (2026-07-14):** Materiallar katalogi (bo'limlar bo'yicha:
qog'oz, karton, kley, lak — grammaj va o'lchov birligi bilan), Xarid/Zakup moduli
(kg/dona/rulon da olish, naqd yoki qarzga, yetkazib beruvchi qarzi + to'lov),
sozlanadigan xizmatlar (laminatsiya, noj, tisneniye, lak turlari) va formulalar
(sebestoyimost) — hammasi Sozlamalar bo'limida admin tomonidan sozlanadi.
SEED_REAL rejimi mijozning ikkala Excel'ini aynan takrorlaydi (совокупность
tekshirilgan): «макс стар» (qog'oz xaridi: 491,8 mln / qarz 106,7 mln) va
«приход-расход» (kassa jurnali: 91 yozuv, 2 firma, USD bilan).

**Kassa jurnali (2026-07-14):** kirim-chiqim daftari — har pul harakati bitta
jurnalda (kimdan keldi / kimga-nimaga ketdi), sex/filial bo'yicha ajratiladi,
so'm va USD, kunlik yig'indilar, Excel eksport (приход-расход formatida).

Brauzer: **http://localhost:8000** · API hujjatlari: **/docs**

Prod rejimda birinchi qadamlar (tizim o'zi yo'naltiradi):
1. Kirish (admin/1234) → Sozlamalarda parolni almashtiring
2. Ombor → Yetkazib beruvchi qo'shing → Kirim (qog'oz partiyasi)
3. Mijozlar → Birinchi mijoz → Smeta → Buyurtma
4. Xodimlar → Xodim qo'shing → Ish qaydi

Kirish: **`admin` / `1234`** — bitta boshqaruvchi hamma narsani boshqaradi.
Kerak bo'lsa xodimlarga login-parolni boshqaruvchining o'zi **Sozlamalar →
Foydalanuvchilar** bo'limida yaratadi va huquq darajasini tanlaydi
(Menejer / Sklad mudiri / Sex boshlig'i / Buxgalter / Rahbar).

Bazani noldan boshlash: `gofra_erp.db` faylini o'chirib qayta ishga tushiring.

## Telegram bot + Mini App

1. BotFather'dan token oling → `.env` ga `BOT_TOKEN=...`
2. Server HTTPS manzilini `WEBAPP_URL=...` ga yozing (VDS/ngrok)
3. Serverni qayta ishga tushiring — bot polling'da ishlaydi, menyuga
   "ERP ochish" Mini App tugmasi qo'yiladi.

Bot oqimi (TZ 1.3): mijoz telefon yuboradi → profilga bog'lanadi → menejer buyurtma
yaratganda smeta botga boradi → "Tasdiqlash" bosilsa status **Sexda kesilmoqda**
ga o'tadi va xomashyo FIFO bo'yicha (5% brak bilan) yechiladi → "Muzokara" bosilsa
menejerga qaytadi.

## Modullar xaritasi (TZ bo'limlariga moslik)

| TZ | Qayerda |
|---|---|
| 1.1 Mijoz kartasi, kredit limit, qora ro'yxat, takroriy buyurtma | CRM sahifasi, `app/routers/clients.py`, `orders.py::reorder` |
| 1.2 Smeta kalkulyatori (FEFCO 0201, menejer marja ko'radi) | Kalkulyator sahifasi, `services.py::quote` |
| 1.3 Bot tasdiqlash zanjiri, status treker | `app/bot.py`, buyurtmalar sahifasi |
| 2.1 Lot/partiya, FIFO, 2 bosqichli ombor, min qoldiq | Ombor sahifasi, `services.py::fifo_writeoff, low_stock_alerts` |
| 2.2 Avtomatik brak (×1.05), inventarizatsiya | status→Sexda spisaniya; `warehouse.py::inventory_check` |
| 3.1 Sdelshina + QC, real vaqt kunlik pul | HR sahifasi, `hr.py::add_work` |
| 3.2 Podotchyot kassa | `hr.py::cash` |
| 3.3 Oylik = ishbay − avans | `services.py::payroll` |
| 4.1 Dinamik tannarx | `services.py::unit_cost` (FIFO joriy narxdan) |
| 4.2 Debitor, aging, sverka, limit bloklash | Moliya sahifasi, `services.py::debt_aging` |
| 4.3 Kreditor, to'lov grafigi, cash flow | Ombor→yetkazib beruvchilar, `cash_flow_forecast` |
| 4.4 Rahbar dashboard | Boshqaruv sahifasi |
| 5.1 Akt PDF + e-tasdiq stempeli | `reports.py::act_pdf` |
| 5.2 Excel eksport (sklad, sverka, kassa, oylik) | `reports.py` |
| 6 Rollar | `auth.py::require_roles`, nav filtrlash |

## Tezkor amallar

Telefonda pastki panel sex uchun eng keraklilarga moslangan:
**Asosiy · Buyurtmalar · [+] · Ombor · Yana**. O'rtadagi **[+]** tugmasi
tezkor amallarni ochadi: Yangi zakaz, To'lov olish, Ish qaydi, Pul berish,
Xomashyo kirim, Xarajat yozish. Kompyuterda xuddi shu tugmalar Asosiy
sahifaning tepasida turadi.

## Testlar

Server ishlab turganda:

```bash
.venv/bin/python tests/e2e_test.py   # 100 ta biznes-logika testi
.venv/bin/python tests/audit.py      # barcha modullar auditi (35+ endpoint)
```

Diqqat: testlar bazaga sinov yozuvlarini kiritadi va idempotent emas —
har run oldidan bazani (`*.db`) o'chirib serverni qayta ishga tushiring.

## Texnologiyalar

FastAPI · SQLAlchemy 2 (DECIMAL) · SQLite→PostgreSQL (`DATABASE_URL`) ·
aiogram 3 · openpyxl · reportlab · Vanilla JS SPA (liquid glass UI, mobile-first,
Telegram WebApp SDK).

© INNASOFT MChJ · 2026
