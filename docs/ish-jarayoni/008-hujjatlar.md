# 008 — HUJJATLAR (reja bosqichi)

**Sana:** 2026-08-15 … 2026-08-18
**Fayllar:** `docs/` — 12 fayl

---

## Nima qilindi

Kod yozishdan oldin **reja tuzildi**. Sabab: loyiha bitta sex ERP
idan ERP+POS+CRM+LMS+WMS+buxgalteriya platformasiga o'sdi. Rejasiz
bunday kengayish adashishga olib boradi.

---

## Yozilgan hujjatlar

| # | Hujjat | Asosiy fikri |
|---|---|---|
| 00 | STRATEGIYA | bo'shliq: chuqur + oson + mahalliy + AI bilan yig'iladigan — hech kimda yo'q |
| 01 | HOZIRGI HOLAT | nima bor, nima yo'q — raqamlar bilan |
| 02 | QONUNCHILIK | EHF (522-qaror), fiskal (943, Davlat reyestri), BHMS №21 |
| 03 | ARXITEKTURA | uchinchi o'q — QOBILIYAT; Bosh kitob; ijarachilik |
| 04 | AI VA RAG | **raqam — asbobdan, bilim — RAG dan** |
| 05 | INTEGRATSIYALAR | to'lov → EHF → fiskal → telefoniya |
| 06 | YO'L XARITASI | A→G, vaqtlar, qaror nuqtalari |
| 07 | TARQATISH | **SaaS qarori** (18-avgustda o'zgardi) |
| 08 | FRONTEND | F1–F6, qayta yozishsiz |
| — | KOD XARITASI | har faylda nima bor, tegilganda nima buziladi |
| — | A-IJARACHILIK | joriy bosqichning TZ si |
| — | README | hamma reja bir sahifada |

---

## Eng muhim uch qaror

### 1. RAG bazaga emas, HUJJATGA

Ko'p loyiha butun ERP bazasini embedding qiladi. Bu noto'g'ri:
raqam noaniq chiqadi («taxminan 850 mln» — buxgalteriyada yaroqsiz),
to'lov kiritilsa vektor eskiradi, «60 kundan oshgan qarz» kabi
filtrni vektor qila olmaydi.

> **Raqam — asbobdan. Bilim — RAG dan. Aralashmaydi.**

### 2. SaaS (18-avgust — qaror o'zgardi)

Avval «mijoz o'z serveriga o'rnatadi + litsenziya + AI shlyuzi»
rejalashtirilgan edi. Bekor qilindi.

Sabab: on-premise ning har og'ir muammosi (AI kalitini himoyalash,
sarfni hisoblash, yangilash, qo'llab-quvvatlash, xato topish) SaaS da
**o'z-o'zidan yo'qoladi**. Ular mijozga qiymat emas edi — faqat
tarqatishning narxi edi.

On-premise bekor emas, **kechiktirildi** — 3–5 mijozdan keyin.

### 3. Tartib: A (ijarachilik) → B (Bosh kitob) → C (AI/RAG)

A birinchi, chunki ikkinchi mijozni qabul qila olmasak qolgani
behuda. Va keyinroq qo'shish qimmatroq.

---

## Inventarizatsiyada topilgan noaniqliklar

Kod xaritasini yozishda raqamlar **repodan o'lchandi** va to'rttasi
noto'g'ri chiqdi:

| Aytilgan edi | Aslida |
|---|---|
| 32 jadval | 33 |
| 117 endpoint | 125 |
| 18 `<script>` | 24 |
| `style.css` «24K qator» | 402 qator / 24 KB |

Oxirgisi rejaga ta'sir qildi: CSS ajratish o'ylanganidan **ancha
yengil** ish ekan.

> Saboq: hujjatdagi raqam o'lchanmasa, u taxmin bo'lib qoladi va
> keyin qaror shu taxminga asoslanadi.

---

## Asosiy natija

**17 151 qatordan ijarachilikda jiddiy o'zgaradigani ~1 000 qator.**
125 endpoint, `services.py` va `genui.py` tegilmaydi — `Depends`
naqshi va «services global holatsiz» qoidasi tufayli.

Bu tasodif emas: `db.py` da 2-bosqich oldindan aytilgan, `domain.py`
da kesh haqida ogohlantirish yozilgan. Reja koddan oldin emas,
kod bilan birga o'ylangan.
