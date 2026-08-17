# 1. HOZIRGI HOLAT — nima bor, nima yo'q

> Reja haqiqatga asoslanishi uchun avval bor narsani aniq sanaymiz.
> Bu yerdagi raqamlar 2026-08-15 holatiga, kod ustidan sanab olingan.

---

## 1.1 Raqamlarda

| Nima | Qancha |
|---|---|
| Kod (Python + JS + CSS + HTML) | 17 151 qator (2026-08-18 o'lchangan) |
| Baza jadvallari | 33 |
| HTTP endpointlar | 125 (hammasi himoyalangan) |
| Soha profillari | 22 |
| Ish tartibi modullari | 5 |
| AI asboblari | 12 |
| AI agentlari | 4 |
| AI yozadigan amallar | 5 (hammasi tasdiq tugmasi orqali) |
| GenUI primitivlari | 8 |
| Sinov to'plamlari | 9 (hammasi o'tadi) |

---

## 1.2 Arxitekturaning kuchli tomoni

Loyihaning eng qimmatli yutug'i — **yadro sohani bilmaydi**.

```
YADRO (kod)                  SOHA (ma'lumot)
────────────────────         ──────────────────────────
pul, ombor, mijoz,           qaysi maydonlar,
xodim, hujjat, rol           qanday retsept,
                             qanday bosqichlar
models.py, services.py       app/profiles/*.json
                             app/modules/*.json
```

Amalda tekshirilgan: 22 sohaning hammasi **bitta kod** bilan to'liq
sikldan o'tadi — non zavodi ham, beton zavodi ham, avto servis ham.
Yangi soha qo'shish = JSON qo'shish, kod yozish emas.

Frontend ham shunday: buyurtma formasi `GET /api/soha/joriy` dan
chiziladi (`static/js/core/soha.js`).

**Bu poydevor to'g'ri qo'yilgan va uni buzmaslik kerak.** Quyidagi
hamma reja shu poydevorni KENGAYTIRISH ustiga qurilgan.

---

## 1.3 Nima YO'Q — ochiq va aniq

### a) Ikki yoqlama yozuv va schetlar rejasi

Hozirgi pul modeli **sodda**: buyurtma → to'lov → kassa yozuvi. Bu
kichik sex uchun yetarli, lekin:

- **buxgalteriya hisoboti chiqmaydi** (balans, foyda-zarar)
- **soliq hisoboti chiqmaydi**
- **auditor tekshira olmaydi**

O'zbekistonda BHMS (Buxgalteriya Hisobi Milliy Standartlari) bo'yicha
ikki yoqlama yozuv MAJBURIY, schetlar rejasi BHMS №21 bilan
belgilangan va 2002-yildan amalda.

> **Xulosa:** «1C uchetka» darajasiga chiqish uchun eng katta
> arxitektura ishi shu. Batafsil: [03-ARXITEKTURA.md](03-ARXITEKTURA.md).

### b) Ijarachilik (multi-tenancy)

Bitta baza, bitta korxona. Ikkinchi mijozga sotish uchun ikkinchi
server ko'tarish kerak. Qabul qilingan qaror — **har mijozga alohida
baza** — hali amalga oshirilmagan.

### c) POS / chakana savdo

`chakana_dokon` profili bor, lekin u **buyurtma** mantiqida ishlaydi.
Haqiqiy POS uchun kerak: smena ochish/yopish, chek chop etish, fiskal
modul, shtrix-kod skaner, naqd/karta aralash to'lov, qaytarish.

### d) To'lov tizimlari

Payme, Click, Uzum — **yo'q**. Hozir to'lov faqat qo'lda yoziladi.

### e) Soliq integratsiyasi

EHF (elektron hisob-faktura) — **yo'q**. Hozirgi hujjatlar (akt,
nakladnoy) PDF/Excel, ular yuridik kuchga ega emas.

### f) CRM voronkasi

Mijoz kartochkasi bor, lekin **lid → muzokara → bitim** voronkasi,
vazifalar, eslatmalar, aloqa tarixi yo'q.

### g) Telefoniya

ATS/call-center — yo'q.

### h) LMS

Umuman yo'q.

### i) Valyuta

Faqat so'm. USD narx va kurs qotirish yo'q (kassada USD yozuvi bor,
lekin buyurtmada emas).

---

## 1.4 AI qatlami — hozirgi holat

**Bor:**
- Uch provayder (Anthropic / OpenAI / Gemini), hammasi bir vaqtda
  ulanishi mumkin, kvota tugasa keyingisiga o'tadi
- 4 bo'lim agenti, har biriga rol cheklovi
- 12 asbob — hammasi **faqat o'qiydi**
- GenUI: AI jadval, diagramma, ko'rsatkich chizadi (8 primitiv)
- Yozish faqat **tasdiq tugmasi** orqali (5 amal), auditga odam yoziladi
- Javob qadamma-qadam oqim bilan keladi, to'xtatish mumkin

**Yo'q:**
- **RAG yo'q** — AI qonunchilik, standart, yo'riqnoma bilmaydi
- Xotira yo'q — har suhbat noldan boshlanadi
- Rejalashtirish yo'q — ko'p qadamli murakkab vazifani bajara olmaydi
- Profil yaratish sinalmagan (kvota tugagani uchun uchidan uchiga
  o'tkazilmadi)

---

## 1.5 Sifat holati

| Tekshiruv | Holat |
|---|---|
| Endpoint himoyasi | 125/125 |
| 22 soha to'liq sikl | o'tadi |
| 22 soha arifmetikasi | to'g'ri |
| Baza butunligi (14 o'zgarmas) | butun |
| Haqiqiy mijoz ma'lumotida | sinalgan (53 mijoz, 81 buyurtma) |
| Jonli LLM | ishlaydi (Gemini) |

Haqiqiy ma'lumot bilan sinash **6 ta jiddiy xatoni** ochdi (QQS qarzdan
tushib qolishi, qarz yoshi jadvalining o'z-o'ziga zid bo'lishi, pul
oqimi prognozi va h.k.) — hammasi tuzatilgan va endi `butunlik.py`
ularni qayta chiqishidan qo'riqlaydi.

**Xulosa:** poydevor mustahkam va sinalgan. Muammo sifatda emas —
QAMROVDA.
