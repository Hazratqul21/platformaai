# KOD XARITASI — har faylda nima bor, u nimaga bog'liq

> Kod yozishdan **oldin** yig'ilgan inventarizatsiya. Har raqam
> repodan o'lchangan (2026-08-18), taxmin yo'q.
>
> Maqsad: ijarachilikka o'tganda **qaysi faylga tegiladi va tegilganda
> nima buziladi** — buni oldindan bilish.

---

## 0. Raqamlar (o'lchangan)

| Nima | Qancha |
|---|---|
| Python | **12 716** qator (38 fayl) |
| Frontend (JS+CSS+HTML) | **4 435** qator (25 fayl) |
| Jami | **17 151** qator |
| Baza jadvallari | **33** |
| HTTP endpointlar | **125** |
| Soha profillari | **22** JSON |
| Ish tartibi modullari | **5** JSON |
| AI agentlari | **4** |
| AI asboblari | **12** (hammasi faqat o'qiydi) |
| GenUI primitivlari | **8**, tasdiqlanadigan amallar **5** |
| Sinov to'plamlari | **8** fayl (`sinov.sh` 9 bosqich) |

### Oldingi hisobotdagi uchta noaniqlik — tuzatildi

| Aytilgan edi | Aslida |
|---|---|
| 32 jadval | **33** |
| 117 endpoint | **125** |
| 18 ta `<script>` tegi | **24** |
| `style.css` — «24K qator» | **402 qator / 24 KB** |

Oxirgisi muhim: CSS 24 ming qator emas. Ya'ni CSS ni ajratish
[08-FRONTEND.md](08-FRONTEND.md) da o'ylanganidan **ancha yengil** ish.

---

## 1. Umumiy tuzilish — qatlamlar

```
                    ┌────────────────────────┐
                    │  static/  (frontend)   │
                    └───────────┬────────────┘
                                │  HTTP /api/...
                    ┌───────────▼────────────┐
   auth.py ────────▶│  routers/  (13 fayl)   │◀──── genui.py
   (kim kirdi)      │  125 endpoint          │      (AI amallari)
                    └───────────┬────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
     ┌────────────────┐ ┌──────────────┐ ┌────────────────┐
     │  services.py   │ │  domain.py   │ │ kassa_sync.py  │
     │  hisob-kitob   │ │  SOHA qatlami│ │ pul jurnali    │
     └───────┬────────┘ └──────┬───────┘ └───────┬────────┘
             │                 │                 │
             └────────┬────────┴─────────────────┘
                      ▼
             ┌──────────────────┐      ┌──────────────┐
             │   models.py      │      │  agent.py    │
             │   33 jadval      │      │  + llm.py    │
             └────────┬─────────┘      └──────────────┘
                      ▼
             ┌──────────────────┐
             │     db.py        │  ← IJARACHILIKDA ENG BIRINCHI SHU
             └──────────────────┘
```

**Asosiy qoida:** yadro (models, services, routers) **sohani
bilmaydi**. «Uzunlik 300 mm» nimani anglatishini faqat `domain.py`
biladi. Shuning uchun 22 soha bitta kod bilan ishlaydi.

---

## 2. YADRO fayllari

### `app/db.py` — 57 qator ⚠️ IJARACHILIKDA BIRINCHI O'ZGARADI

Baza ulanishi. `DATABASE_URL` dan `engine` + `SessionLocal` +
`get_db()` yasaydi. `postgres://` eski shaklini jimgina to'g'rilaydi.

- **Kimga kerak:** hamma router, hamma test, `main.py`
- **Nimaga bog'liq:** hech nimaga (eng past qatlam)
- **Hozirgi faraz:** *bitta jarayon = bitta baza*
- **Ijarachilikda:** `get_db` so'rovdan akkauntni aniqlab, o'sha
  akkauntning `Engine` ini qaytaradi. Hovuz hozir `pool_size=10,
  max_overflow=20` — 50 mijozda 1500 ulanish, PostgreSQL standarti
  100. Mijoz bo'yicha kichraytirish + LRU shart.
- Faylning o'zida PostgreSQL tanlash sababi yozilgan va «har mijozga
  alohida baza (2-bosqich)» oldindan aytilgan — ya'ni yo'l mos.

### `app/models.py` — 561 qator, 33 jadval

SQLAlchemy 2.0 modellari. Pul ustunlari `Numeric(18,2)` — float yo'q.

| Guruh | Jadvallar |
|---|---|
| Kirish | `users`, `auth_tokens` |
| Mijoz | `clients` |
| Buyurtma | `orders` (dinamik `attributes`), `order_photos` |
| To'lov | `payments`, `supplier_payments`, `purchase_payments`, `payment_schedules` |
| Ombor (eski) | `raw_lots`, `stock_moves`, `inventory_checks` |
| Ombor (umumiy) | `materials`, `material_lots`, `material_writeoffs`, `material_moves` |
| Kadrlar | `employees`, `work_entries` |
| Moliya | `cash_entries`, `kassa_entries` |
| Xarid | `purchases`, `suppliers` |
| Katalog | `units`, `positions`, `categories`, `services`, `formulas` |
| Soha | `soha_profillar`, `custom_sections`, `custom_records` |
| AI | `agent_suhbatlar` |
| Boshqa | `settings`, `audit_logs` |

- **Bog'liq:** faqat `db.py` (`Base`)
- **Ijarachilikda:** jadvallar o'zgarmaydi. `auth_tokens` esa
  **boshqaruv bazasiga ko'chadi** — tokenni tekshirish uchun avval
  qaysi bazaga borishni bilish kerak (tovuq-tuxum tuguni).

### `app/domain.py` — 626 qator ⚠️ EN XAVFLI GLOBAL HOLAT

Soha qatlami. Ikki tushuncha:
- **PROFIL** = mahsulot ta'rifi (maydonlar, retsept, birliklar)
- **MODUL** = ish tartibi (statuslar, o'tishlar, rollar)

Odoo da bu «app», 1C da «конфигурация». Bizda ikkisi ajratilgan,
chunki «non zavodi» va «mebel sexi» — ikki SOHA, lekin bitta
ISH TARTIBI.

Asosiy funksiyalar: `qayta_yukla()` · `profil()` · `modul()` ·
`manosi()` · `soha_yoz()` / `soha_oqi()` · `retsept_qatorlari()` ·
`xomashyo_kerak()` · `tekshir()` · `hosila_hisobla()`

**Status MA'NOSI bo'yicha ishlaydi**, nomi bo'yicha emas
(`boshlanish`/`ishlab_chiqarish`/`tayyor`/`topshirildi`/`bekor`) —
shuning uchun har soha statusini o'zicha atashi mumkin.

- **Bog'liq:** `models`, `services`
- **Kim ishlatadi:** `agent.py`, `routers/soha.py`, `orders.py`,
  `warehouse.py`, `clients.py`, `reports.py`, `main.py`, `seed.py`,
  `migrate.py`, `bot.py` — **26 ta `profil()` chaqiruvi**
- ⚠️ **`_KESH` — modul darajasidagi GLOBAL o'zgaruvchi.** Ikki mijoz
  bo'lsa: mebel so'rov yubordi → kesh mebel → non so'rov yubordi →
  **nonga mebel maydonlari ko'rinadi.** Faylning bosh izohida bu
  ogohlantirish allaqachon yozib qo'yilgan.
- **Yechim:** `contextvars` — 26 joyni qo'lda tuzatishda bittasi
  albatta unutiladi, `profil()` imzosi o'zgarmagani ma'qul.

### `app/services.py` — 1 077 qator, 34 funksiya

Hisob-kitobning **hammasi** shu yerda. Router faqat chaqiradi.

| Guruh | Funksiyalar |
|---|---|
| Formula | `eval_formula`, `safe_formula_check`, `formula_xato` |
| Tannarx | `unit_cost`, `quote`, `retsept_tannarx`, `ustama_foizi`, `material_narxi_m2` |
| Ombor | `fifo_writeoff`, `raw_stock_for`, `low_stock_alerts`, `material_top` |
| Qarz | `client_balance`, `client_balances_batch`, `debt_aging`, `supplier_balance`, `credit_check` |
| Pul | `cash_flow_forecast` |
| QQS | `qqs_hisobla` |
| Kadrlar | `payroll` |
| Retsept | `retsept_yechish`, `_konversiya` |

**Bu yerda oltita jiddiy xato topilgan edi** (haqiqiy mijoz
ma'lumotida): QQS qarzdan tushib qolgan, qarz yoshi status nomiga
bog'langan, `opening_balance` manfiy bo'lgani (avans) hisobga
olinmagan, pul oqimida noto'g'ri sana ustuni, yetkazib beruvchi qarzi
chiqimda yo'q, `Decimal × float`. Hammasi tuzatilgan,
`tools/butunlik.py` qaytishidan qo'riqlaydi.

- **Bog'liq:** `models`, `domain`
- **Ijarachilikda:** o'zgarmaydi (global holat yo'q) — **eng
  xavfsiz katta fayl**

### `app/auth.py` — 137 qator

Parol (`bcrypt`), token, rol tekshiruvi, brute-force cheklovi
(`login_cheklovini_tekshir` — IP bo'yicha).

`get_user` · `get_user_parolsiz` · `require_roles(*roles)` —
bularsiz endpoint yozilsa `tests/himoya_audit.py` ushlaydi.

- **Ijarachilikda:** token boshqaruv bazasiga ko'chadi, `get_user`
  akkauntni ham qaytaradi. **Ikkinchi eng muhim o'zgarish.**

### `app/main.py` — 200 qator

FastAPI ilovasi, CORS, `/api/auth/*`, statik fayllar, `lifespan`.

`lifespan` startupda: `create_all` → `run_migrations` →
`jadvalni_qayta_qur` → `profillarni_yukla` → `domain.qayta_yukla` →
`seed` → `backfill_soha` → `start_bot_bg`.

- ⚠️ Bularning **hammasi bitta bazaga**. Ijarachilikda ular
  startupdan chiqib, **akkaunt yaratilganda** va **migratsiya
  buyrug'ida** bajariladi.

### `app/migrate.py` — 236 qator

Yengil migratsiya: `create_all` faqat yangi jadval yaratadi, mavjud
jadvalga ustun qo'shmaydi — shu bo'shliqni yopadi.

`run_migrations` · `jadvalni_qayta_qur` (SQLite da ustun turini
o'zgartirish) · `profillarni_yukla` · `backfill_soha`

**Qoida:** migratsiya faqat **qo'shadi**, o'chirish alohida.

- **Ijarachilikda:** `tools/migratsiya.py --hammasi` — har bazada
  zaxira → migratsiya → `butunlik.py`, xatoda o'sha akkaunt
  qaytariladi, qolganlari davom etadi.

---

## 3. AI qatlami

### `app/llm.py` — 521 qator

Provayder-neytral qatlam. Yuqoridagi kod qaysi provayder
ishlayotganini **bilmaydi**.

- `javob_ol(xabarlar, asboblar, korsatma, qotirilgan_model)`
- `ZAXIRA_MODELLAR` — kvota tugasa keyingi modelga, keyin keyingi
  provayderga
- `kalit_shubhali()` — `sk-...` kabi o'rin egallovchini tanib oladi
- `JavobBuzildi` — `MALFORMED_FUNCTION_CALL` / `MAX_TOKENS`, qayta
  urinishga arziydi
- Gemini `thought_signature` ni echo qilish talab qiladi — shuning
  uchun model **suhbat o'rtasida qotiriladi**
- `OPENAI_BASE_URL` orqali DeepSeek/Groq/Ollama ham ishlaydi

- **Bog'liq:** hech nimaga (mustaqil)
- **Ijarachilikda:** har chaqiruvdan keyin token soni
  `ai_sarf` ga yoziladi — narx **o'sha paytdagi bo'yicha qotiriladi**

### `app/agent.py` — 921 qator

Agentik halqa. `suhbat_oqim()` — generator, `{"tur": "qadam" |
"asbob" | "asbob_ok" | "qayta_urinish" | "yakun"}` beradi.

**4 agent × o'z asboblari × rol cheklovi:**

| Agent | Asboblari | Kimga |
|---|---|---|
| sozlash | `modullarni_kor`, `profillarni_kor`, `profilni_oqi`, `profil_saqla`, `profilni_faollashtir`, `sinov_buyurtma` | Rahbar |
| ombor | `ombor_qoldigi`, `buyurtma_retsepti`, `sinov_buyurtma` | Rahbar, sklad, sex |
| moliya | `qarzdorlar`, `pul_holati`, `mijoz_hisobi` | Rahbar, buxgalter |
| buyurtma | buyurtma asboblari | Rahbar, menejer, sex |

**Nega bitta katta agent emas:** 40 asbob berilsa model qaysi birini
chaqirishni chalkashtiradi — amalda tekshirilgan.

`MAX_ASBOB_JAVOBI = 12 000` + `_javobni_qisqartir()` — model javobi
o'lchamdan oshsa qisqartirilib qayta urinadi.

Moliya asboblari `services.debt_aging` / `client_balance` ni
chaqiradi — **AI va moliya ekrani bir xil raqamni aytishi uchun**.
Bir vaqtlar agentning o'z formulasi bor edi va AI 1 457 mln, ekran
853 mln ko'rsatgan edi.

- **Bog'liq:** `domain`, `models`, `services`, `genui`, `llm`,
  `routers.finance`, `routers.orders`

### `app/genui.py` — 400 qator

Model yuborgan komponentni **tekshiradi** (model — ishonchsiz manba).

**8 primitiv, MODUL bo'yicha emas MA'LUMOT SHAKLI bo'yicha:**
`jadval` · `korsatkichlar` · `tafsilot` · `taqsimot` ·
`profil_oynasi` · `tasdiq` · `hujjat` · `ogoh`

**5 tasdiqlanadigan amal:** `profilni_faollashtir` ·
`buyurtma_maqomi` · `mijozni_bloklash` · `kredit_limiti` ·
`eng_past_qoldiq`

Chegaralar: `MAX_KOMPONENT=6`, `MAX_QATOR=60`, `MAX_USTUN=8`,
`MAX_MATN=300`. `hujjat` da faqat `/api/` havolalar qoladi.

`_buyurtma_maqomi` → `routers.orders.set_status` ni chaqiradi, o'z
mantiqini yozmaydi — **ombor yechish qoidasi ikki joyda bo'lmasin**.

> **Qoida:** agent bazaga o'zi yozmaydi. Taklif qiladi → odam tugma
> bosadi → auditga **odam** yoziladi.

---

## 4. Routerlar — 13 fayl, 125 endpoint

| Fayl | Endpoint | Nima | Bog'liq |
|---|---|---|---|
| `catalog.py` | 20 | material, birlik, lavozim, xizmat, formula | services |
| `orders.py` | 16 | buyurtma CRUD, smeta, retsept, status, topshirish | domain, services, kassa_sync, bot |
| `warehouse.py` | 12 | FIFO partiyalar, qoldiq, inventarizatsiya | domain, services, kassa_sync |
| `reports.py` | 10 | Excel/PDF/DOCX — akt, nakladnoy, sverka | domain, services |
| `hr.py` | 10 | xodim, sdelshina, ish haqi, avans | services, kassa_sync |
| `finance.py` | 10 | to'lov, qarzdor, pul oqimi, dashboard | domain, services, kassa_sync |
| `agent.py` | 8 | AI chat, oqim (NDJSON), amal, faoliyat | agent, genui, llm, services |
| `constructor.py` | 7 | no-code jadval quruvchi | models |
| `purchase.py` | 6 | xarid, yetkazib beruvchi qarzi | kassa_sync |
| `kassa.py` | 5 | kassa jurnali, ko'p akkaunt/valyuta | models |
| `clients.py` | 5 | mijoz CRUD, detalizatsiya | domain, services |
| `users.py` | 4 | RBAC, parol | models |
| `soha.py` | 4 | profil boshqaruvi, faollashtirish | domain |

**Hammasi `Depends(get_db)` va `Depends(get_user)` ishlatadi** —
shuning uchun ijarachilikda **125 endpointning birortasi
o'zgarmaydi**, almashtirish `db.py` va `auth.py` da bo'ladi. Bu —
hozirgi kodning eng qimmatli tomoni.

### `app/kassa_sync.py` — 164 qator

Pul beshta bo'limda yuriladi (mijoz to'lovi, sex xarajati, xodim
avansi, xarid to'lovi, yetkazib beruvchiga to'lov), kassa jurnali
esa bitta bo'lishi kerak. Shu ko'prik.

### `app/bot.py` — 183 qator ⚠️ GLOBAL HOLAT

Telegram bot (aiogram 3), buyurtma tasdiqlash zanjiri, Mini App
tugmasi. `main.py` startupda `threading.Thread(name="gofra-bot")`
bilan ishga tushadi.

- ⚠️ **Bitta bot → bitta baza.** Ijarachilikda bot boshqaruv
  bazasidan tokeni bor akkauntlarni o'qib, har biriga alohida ishlashi
  kerak.

### `app/seed.py` — 456 qator

Birinchi ishga tushirish: `admin` yaratiladi. `SEED_DEMO=1` bo'lsa
karton namunasi. `MUHIT=prod` da demo bilan ishga tushmaydi.

---

## 5. Ma'lumot fayllari — kod emas, DATA

### `app/profiles/*.json` — 22 soha

`avto_servis` · `beton` · `chakana_dokon` · `gisht` · `kabel` ·
`karton` · `kimyo` · `kolbasa` · `logistika` · `mebel` · `metall` ·
`montaj` · `non` · `plastik_deraza` · `poligrafiya` · `poyabzal` ·
`reklama` · `sut` · `texnika_tamiri` · `tikuvchilik` ·
`ulgurji_savdo` · `yogoch_eshik`

**Muhim:** JSON fayllar faqat **boshlang'ich shablon**. Haqiqat
bazadagi `soha_profillar` jadvalida. Shuning uchun AI yangi soha
yasaganda kod ham, fayl ham yozilmaydi — **bazaga yozuv qo'shiladi**.

### `app/modules/*.json` — 5 ish tartibi

`ishlab_chiqarish` · `savdo` · `qurilish` · `tamirlash` · `xizmat`

22 soha 5 ta ish tartibini bo'lishadi. Agar status har profilda
takrorlansa, 22 marta bir xil oqim yozilardi.

---

## 6. Frontend — `static/`, 4 435 qator

### `static/index.html` — 136 qator, **24 ta `<script>` tegi**

Bitta HTML, hamma sahifa shu yerda. 24 ta alohida so'rov —
[08-FRONTEND.md](08-FRONTEND.md) F1 (Vite) aynan shuni yopadi.

### `static/js/core/` — yadro

| Fayl | Qator | Nima |
|---|---|---|
| `globals.js` | 241 | `api()`, til (`DICT`, `t()`), akkaunt almashtirish, Telegram aniqlash |
| `router.js` | 141 | hash marshrutlash, navigatsiya (`NAV`), tez amallar |
| `genui.js` | 241 | 8 primitivni chizadi — **hamma matn `textContent`, `innerHTML` yo'q** |
| `soha.js` | 143 | `/api/soha/joriy` dan **formani chizadi** — yangi soha qo'shilganda JS ga tegilmaydi |
| `ui.js` | 131 | toast, modal, pul formati, rasm kichiklashtirish |
| `auth.js` | 49 | kirish, chiqish, majburiy parol almashtirish |

`soha.js` — frontendning ham konstruktor ekanining isboti.

### `static/js/pages/` — 15 sahifa

`settings` 488 · `orders` 405 · `ai` 379 · `crm` 272 · `hr` 239 ·
`calc` 236 · `agent` 174 · `wh` 159 · `zakup` 157 · `kassa` 89 ·
`help` 77 · `exp` 76 · `mat` 71 · `fin` 60 · `dash` 60

### `static/css/style.css` — 402 qator / 24 KB

«Light Liquid Glass». Katta emas — ajratish yengil ish.

- ⚠️ Hamma JS **global scope** da. `function toast()` yozilsa
  hamma joydan ko'rinadi. Bog'liqlik ko'rinmaydi.
- **Ijarachilikda qo'shiladi:** ro'yxatdan o'tish, AI sehrgari,
  tarif, AI sarfi, platforma admini ([08](08-FRONTEND.md) §8.4)

---

## 7. Sinovlar — `tests/`, 8 fayl

| Fayl | Qator | Nima tekshiradi | Server kerakmi |
|---|---|---|---|
| `himoya_audit.py` | 83 | har endpoint `Depends(get_user)` bormi — **AST bo'yicha** | ❌ |
| `genui_test.py` | 150 | model yuborgan komponent xavfsizmi | ❌ |
| `profil_test.py` | 219 | 22 profil to'liq siklidan o'tadimi | ✅ |
| `chuqur_sinov.py` | 486 | «200 qaytdimi» emas — **RAQAM to'g'rimi** | ✅ |
| `kochirish_test.py` | 228 | eski bazadan ma'lumot yo'qolmasdan o'tadimi | ✅ |
| `e2e_test.py` | 571 | to'liq hayotiy sikl | ✅ |
| `audit.py` | 180 | modul auditi — 38 endpoint jonli serverda | ✅ |
| `jonli_agent_test.py` | 158 | **haqiqiy LLM** bilan (kalit yo'q bo'lsa o'tkazadi) | ✅ |

`himoya_audit.py` naqshi muhim: **serversiz, kodni AST bilan
o'qiydi**. Yangi endpoint qo'shilib himoya unutilsa shu yerda
ushlanadi.

**Ijarachilikda `tests/ijarachilik.py` qo'shiladi** — o'sha naqshning
davomi: u yerda tokensiz sinalgan, bu yerda **boshqa akkauntning
tokeni bilan** ([A-IJARACHILIK.md](A-IJARACHILIK.md) §A.8).

---

## 8. Vositalar — `tools/`

| Fayl | Qator | Nima |
|---|---|---|
| `demo_data.py` | 519 | 22 sohaga to'liq demo — bo'sh bazada qarz yoshi, FIFO ko'rinmaydi |
| `kochir.py` | 293 | eski SQLite → platforma. Manba `mode=ro` — yozish **SQLite darajasida imkonsiz** |
| `butunlik.py` | 207 | **14 o'zgarmas** — hech narsa yozmaydi, prodda ham ishlaydi |

`butunlik.py` — oltita xato qaytib chiqmasligining kafolati:
qarz ikki yo'lda bir xilmi, qarz yoshi bo'laklari jamiga tengmi,
partiyalar qoldiqqa mosmi.

**Ijarachilikda qo'shiladi:** `tools/migratsiya.py --hammasi`.

---

## 9. IJARACHILIKKA O'TISHDA TEGILADIGAN FAYLLAR

Shu jadval — kod yozishning boshlanish nuqtasi.

| Fayl | O'zgarish | Xavf |
|---|---|---|
| `app/db.py` | `get_db` akkaunt bo'yicha, `Engine` hovuzi + LRU | 🔴 yuqori — hamma shundan o'tadi |
| `app/auth.py` | token boshqaruv bazasida, `get_user` akkauntni qaytaradi | 🔴 yuqori |
| `app/domain.py` | `_KESH` → `contextvars`, 26 chaqiruv | 🔴 yuqori — **jimgina buzadi** |
| `app/main.py` | `lifespan` dan startup ishlari chiqadi | 🟡 o'rta |
| `app/bot.py` | akkaunt bo'yicha ko'p bot | 🟡 o'rta |
| `app/llm.py` | sarf yozish (`ai_sarf`) | 🟢 past — qo'shimcha |
| `app/models.py` | boshqaruv bazasi modellari **alohida faylda** | 🟢 past |
| **`routers/*` (13 fayl)** | **o'zgarmaydi** | 🟢 — `Depends` tufayli |
| **`services.py`** | **o'zgarmaydi** | 🟢 — global holat yo'q |
| **`genui.py`** | **o'zgarmaydi** | 🟢 |
| `static/js/*` | yangi ekranlar qo'shiladi, mavjudlari qolаdi | 🟢 |

**Xulosa:** 17 151 qatordan **jiddiy o'zgaradigani ~1 000 qator**
(`db.py` + `auth.py` + `domain.py` keshi + `main.py`). Qolgani
o'z joyida qoladi.

Bu tasodif emas — `Depends(get_db)` naqshi va «services global
holatsiz» qoidasi boshidan shunga qaratilgan edi.

---

## 10. Global holat — to'liq ro'yxat

Ijarachilikda **faqat shular** ma'lumot sizishiga sabab bo'la oladi.
Ro'yxat to'liq, kod bo'yicha tekshirilgan:

| # | Qayerda | Nima |
|---|---|---|
| 1 | `domain.py:290` | `_KESH: Profil` — faol profil |
| 2 | `db.py` | `engine`, `SessionLocal` — modul darajasida |
| 3 | `bot.py:183` | bot threadi — bitta bazaga yozadi |
| 4 | `auth.py` | brute-force urinishlari IP bo'yicha (**bu global qolishi to'g'ri** — hujum akkauntdan qat'i nazar) |
| 5 | `main.py` `lifespan` | startupdagi bir martalik ishlar |

4-band ataylab qoldiriladi: brute-force hujumi akkaunt chegarasini
tan olmaydi.

---

## 11. Nima YO'Q — bo'shliqlar

| Yo'q | Qayerda kerak bo'ladi |
|---|---|
| Ijarachilik | [A-IJARACHILIK.md](A-IJARACHILIK.md) |
| Bosh kitob (GL) | B bosqichi — balans, soliq |
| RAG | C bosqichi — qonunchilik bilimi |
| Agent xotirasi | C bosqichi |
| To'lov tizimlari | [05-INTEGRATSIYALAR.md](05-INTEGRATSIYALAR.md) |
| EHF | 05 |
| POS / fiskal | D bosqichi + sertifikat |
| CRM voronkasi, WMS, LMS | E · F · G |
| Frontend build/test | [08-FRONTEND.md](08-FRONTEND.md) |
| Valyuta (ko'p valyutali hisob) | keyinroq |

---

## 12. Xulosa — kod yozishdan oldingi holat

**Kuchli:**
1. Yadro sohani bilmaydi — 22 soha bitta kodda, sinalgan
2. `Depends` naqshi tufayli ijarachilik 125 endpointga tegmaydi
3. `services.py` global holatsiz — eng katta fayl eng xavfsizi
4. Sinov mustahkam, haqiqiy mijoz ma'lumotida sinalgan
5. AI: tasdiq qoidasi, GenUI tekshiruvi, ko'p provayder

**Zaif:**
1. `domain._KESH` — ijarachilikning №1 xavfi, **jimgina** buzadi
2. Token mijoz bazasida — tovuq-tuxum tuguni
3. Ulanish hovuzi 50 mijozga hisoblanmagan
4. Bot bitta bazaga bog'langan
5. Frontend global scope, build va test yo'q

**Birinchi kod:** `db.py` → `auth.py` → `domain.py` keshi. Shu
uchtasi `tests/ijarachilik.py` bilan birga yozilmaguncha boshqasiga
o'tilmaydi.
