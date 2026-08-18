# 012 — INFRATUZILMA VA AI XARAJATI HISOBI

**Sana:** 2026-08-18
**Natija:** [../09-INFRATUZILMA.md](../09-INFRATUZILMA.md)

---

## Nima qilindi

VDS konfiguratsiyasi va «bitta foydalanuvchi oyiga AI ga qancha
sarflaydi» savoliga javob. **Taxmin bilan emas — o'lchab.**

---

## Qanday o'lchandi

Odatda bunday hisob «taxminan 1000 token» deb boshlanadi va natija
o'ndan bir yoki o'n barobar xato bo'ladi. Shuning uchun kodning
o'zidan o'lchandi:

| Nima | Usul | Natija |
|---|---|---|
| Agent ko'rsatmasi + asbob sxemasi | `len()` har agent uchun | moliya 2 101 · ombor 2 430 · buyurtma 2 823 · **sozlash 6 498** belgi |
| Asbob javobi | demo bazada 5 asbob chaqirildi | 181 … 4 550, o'rtacha **1 923** belgi |
| Ilova xotirasi | `uvicorn` + `ps -o rss` | **96 MB** |
| Javob vaqti | `curl -w time_total` × 3 | **1–30 ms** |
| Baza hajmi | demo (25 buyurtma) fayl hajmi | 228 KB → **≈ 9 KB/buyurtma** |

Narx `app/platforma/xizmat.py` dagi **haqiqiy funksiyadan** olindi
(`narx_mln_som`) — ya'ni hisobdagi raqam mijozga chiqadigan hisob
bilan bir xil formuladan keladi.

---

## Javob

| | Flash bilan |
|---|---|
| **Minimal** (2 savol/kun) | **≈ 3 100 so'm/oy** |
| O'rtacha (8 savol/kun) | ≈ 19 000 so'm/oy |
| Faol (20 savol/kun) | ≈ 47 500 so'm/oy |
| **Maksimal** (40 savol/kun, og'ir) | **≈ 270 000 so'm/oy** |

Sonnet bilan har biri **7 baravar** qimmat — maksimal 2,1 mln so'm.

---

## Uchta topilma

### 1. Model tanlash 7 baravar farq beradi

Flash va Sonnet orasidagi farq — 7×. `gemini-3.5-flash-lite` esa
yana 3× arzon.

**Xulosa kodga ta'sir qiladi:** `llm.py` da model tanlash vazifa
turiga qarab bo'lishi kerak, hozirgidek faqat kvota bo'yicha emas.
Kundalik savol → flash-lite, profil yasash → kuchli model.

### 2. Kirish tokeni chiqishdan ko'p — kesh eng katta tejash

Har qadamda ko'rsatma va asbob sxemasi **qayta yuboriladi**. Og'ir
stsenariyda kirish 28 204, chiqish 4 120 token — ya'ni pulning
katta qismi **bir xil matnni qayta-qayta yuborishga** ketadi.

Prompt caching (Anthropic va Gemini da bor) buni sezilarli
kamaytiradi. Bu — C bosqichiga aniq vazifa.

### 3. Diskni rasm belgilaydi, baza emas

Baza yiliga 22–650 MB. Rasmlar esa 3 600 buyurtmaga ≈ **2,5 GB**.
Ya'ni disk rejasi buyurtma soniga emas, **rasm soniga** qarab
tuziladi.

---

## Huquqiy topilma — serverning JOYI

O'zbekiston qonunchiligida fuqarolarning shaxsiy ma'lumotlari
**mamlakat hududidagi serverlarda** saqlanishi talab qilinadi.
Bizning tizimda shaxsiy ma'lumot bor: mijoz kontakti, telefon,
xodimlar, ish haqi.

**Demak Hetzner/DigitalOcean/Contabo — arzon bo'lsa ham mos emas.**
Mahalliy provayder majburiy.

Qo'shimcha foyda: Toshkentdan Germaniyaga ping 80–120 ms, mahalliyga
5–15 ms.

> Hujjatda «yuristdan tasdiq oling» deb yozib qo'ydim — bu huquqiy
> maslahat emas, texnik reja uchun ogohlantirish.

---

## Ulanishlar — PgBouncer majburiy

Kodda birinchi qatlam bor (kichik hovuz + LRU), lekin 50 mijozda
250 ulanish chiqadi, PostgreSQL standarti 100.

PgBouncer'siz **100 mijozdan oshib bo'lmaydi** — qancha RAM
qo'shilsa ham. Bu infratuzilma rejasidagi eng qattiq chegara.

---

## VDS — uch bosqich

| Bosqich | Mijoz | Konfiguratsiya |
|---|---|---|
| A | 1–10 | 4 vCPU · 8 GB · 80 GB **NVMe** |
| B | 10–50 | 8 vCPU · 16 GB · 200 GB NVMe + PgBouncer |
| C | 50–200 | ilova ×2 · baza alohida (8 vCPU/32 GB) · zaxira alohida |

NVMe majburiy: SATA SSD da `fsync` sekin va yozuv paytida butun
tizim osiladi.

---

## Ishonchlilik darajasi — halol baho

| Raqam | Ishonch |
|---|---|
| Ko'rsatma va sxema hajmi | **yuqori** — bevosita o'lchandi |
| Asbob javobi hajmi | **o'rta** — demo bazada (10 mijoz). Haqiqiy mijozda 100 mijoz bo'lsa `qarzdorlar` javobi bir necha barobar kattaroq |
| Belgi→token (3:1) | **o'rta** — o'zbek lotin uchun taxmin, aniq o'lchov `count_tokens` bilan qilinadi |
| Fikrlash tokenlari | **past** — 300–900 deb olindi, model va savolga qarab keskin o'zgaradi |
| Narx jadvali | **yuqori** — provayder e'lon qilgan, lekin o'zgaradi |

> Ya'ni «3 100 so'm» va «270 000 so'm» — **kattalik tartibi**, tiyin
> aniqligida emas. Haqiqiy sarf birinchi oyda `ai_sarf` jadvalidan
> ko'rinadi va shunda bu hujjat yangilanadi.
