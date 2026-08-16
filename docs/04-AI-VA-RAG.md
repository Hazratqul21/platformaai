# 4. AI AGENT VA RAG QUVURI

> Maqsad: oddiy odam AI bilan gaplashib o'ziga tizim yasab olsin.
> Bu hujjat — AI ni shu darajaga qanday chiqarish.

---

## 4.1 ENG MUHIM QAROR: RAG nimaga kerak, nimaga kerak emas

Bu yerda ko'p loyiha adashadi va katta pul yo'qotadi.

### ❌ Bazani vektorlashtirmaymiz

Ba'zilar butun ERP bazasini embedding qiladi va «AI ma'lumotni
biladi» deb o'ylaydi. Bu **noto'g'ri**:

| Muammo | Nima bo'ladi |
|---|---|
| Raqam noaniq | «taxminan 850 mln» — buxgalteriyada bu yaroqsiz |
| Eskiradi | to'lov kiritildi, vektor eski qoldi |
| Qimmat | har o'zgarishda qayta indekslash |
| Filtr yo'q | «60 kundan oshgan qarz» — vektor buni qila olmaydi |

**ERP ma'lumotiga ASBOB bilan boriladi** — SQL/API orqali, aniq
raqam bilan. Bugungi 12 asbob aynan shunday ishlaydi va **to'g'ri
yo'l shu**.

### ✅ RAG MATNGA kerak

RAG — bazaga emas, **hujjatlarga**:

```
┌────────────────────────────────────────────────────────┐
│  RAG BAZASI (matn, kamdan-kam o'zgaradi)               │
├────────────────────────────────────────────────────────┤
│  1. QONUNCHILIK                                        │
│     Soliq kodeksi, BHMS standartlari, 522/943-qarorlar │
│     → «QQS stavkasi qancha?» «EHF qachon majburiy?»    │
│                                                        │
│  2. SOHA BILIMI                                        │
│     retsept me'yorlari, brak foizlari, texnologiya     │
│     → «non uchun un me'yori qancha?»                   │
│                                                        │
│  3. TIZIM YO'RIQNOMASI                                 │
│     har bo'lim qanday ishlaydi, qanday sozlanadi       │
│     → «qarz yoshi qanday hisoblanadi?»                 │
│                                                        │
│  4. MIJOZNING O'Z HUJJATLARI                           │
│     shartnomalar, narx ro'yxatlari, ichki qoidalar     │
│     → «bu mijoz bilan shartnomada chegirma bormi?»     │
└────────────────────────────────────────────────────────┘
```

### Qoida

> **Raqam — asbobdan. Bilim — RAG dan. Ikkalasi aralashmaydi.**

AI «Deликатес qarzi qancha?» deganda `qarzdorlar` asbobini chaqiradi
(aniq raqam). «Bu qarzni hisobdan chiqarsam soliq qanday bo'ladi?»
deganda RAG dan Soliq kodeksini o'qiydi.

---

## 4.2 RAG quvurining texnik ta'rifi

```
HUJJAT → bo'laklash → embedding → pgvector → qidiruv → agent
```

**Baza:** PostgreSQL + `pgvector`. Alohida vektor bazasi (Pinecone,
Qdrant) kerak emas — bizda allaqachon PostgreSQL bor, hujjat hajmi
kichik (o'n minglab bo'lak), va bitta baza = bitta zaxira.

**Bo'laklash:** sarlavha bo'yicha, 500–800 token, 100 token ustma-ust.
Har bo'lakka **manba** yoziladi (qaysi hujjat, qaysi bo'lim) —
foydalanuvchi tekshira olishi uchun.

**Embedding:** provayder-neytral (bugungi `llm.py` kabi). Gemini
`text-embedding-004`, OpenAI `text-embedding-3-small`. Model
almashsa qayta indekslash kerak — shuning uchun qaysi model bilan
indekslangani bazada saqlanadi.

**Qidiruv — GIBRID:** faqat vektor yetarli emas. «943-son qaror» degan
aniq raqamni vektor topa olmasligi mumkin. Shuning uchun:
`vektor qidiruv + PostgreSQL to'liq matnli qidiruv`, natijalar
birlashtiriladi.

**Yangi asbob:** `bilim_qidir(savol, soha)` — agent buni xuddi
boshqa asboblar kabi chaqiradi.

### Manba ko'rsatish MAJBURIY

Har RAG javobida qaysi hujjatdan olingani yoziladi. Buxgalter «AI
shunday dedi» bilan ishlay olmaydi — «Soliq kodeksi 248-modda»
kerak. GenUI da bu `hujjat` primitivida ko'rsatiladi.

---

## 4.3 Agentni «Claude Code darajasi»ga chiqarish

Hozirgi agent — **bir qadamli**: savol → asbob → javob. Sizning
maqsadingiz esa: «biznesimni ayt, tizim yasab ber». Bu **ko'p qadamli
reja** talab qiladi.

### Kerak bo'lgan to'rt narsa

**1. REJA (planning)**

Agent murakkab vazifani qadamlarga bo'lib, foydalanuvchiga ko'rsatishi
kerak:

```
Mijoz: «Mebel sexim bor, tizim yasab ber»

AGENT REJASI:
  1. Sohani aniqlash (savollar berish)      ← hozir
  2. O'xshash profilni topish                ← hozir
  3. Maydonlarni moslash                     ← hozir
  4. Retseptni tuzish                        ← hozir
  5. Sinov buyurtmasi bilan tekshirish       ← hozir
  6. Qobiliyatlarni yoqish (savdo+ombor)     ← YO'Q
  7. Boshlang'ich ma'lumot (ombor, mijoz)    ← YO'Q
  8. Foydalanuvchilar va rollar              ← YO'Q
  9. Hujjat rekvizitlari                     ← YO'Q
```

Reja ekranda ko'rinadi, har qadam bajarilgach belgilanadi. Bu —
`profil_oynasi` GenUI primitivining kengaytirilgan shakli.

**2. XOTIRA**

Hozir har suhbat noldan. Kerak:
- **suhbat xotirasi** — bu suhbatda nima kelishildi
- **doimiy xotira** — «bu korxona QQS to'lovchisi», «narxlar USD da»
- Amalga oshirish: `mijoz_xotira` jadvali, agent boshida yuklanadi

**3. KO'PROQ YOZISH — lekin tasdiq bilan**

Hozir 5 ta yozadigan amal. Konstruktor uchun kerak: mijoz qo'shish,
buyurtma yaratish, ombor kirimi, narx o'zgartirish, foydalanuvchi
yaratish, qobiliyat yoqish...

**Qoida o'zgarmaydi:** agent o'zi yozmaydi, taklif qiladi, odam
tugma bosadi, auditga odam yoziladi. Bu — «AI xato qilsa nima
bo'ladi» degan savolga yagona to'g'ri javob.

Amallar ko'payganda **guruhli tasdiq** kerak: «Quyidagi 5 amalni
bajaraymi?» — bittalab bosib chiqish charchatadi.

**4. O'Z-O'ZINI TEKSHIRISH**

Agent profil yasagach `sinov_buyurtma` bilan o'zi tekshiradi — bu
allaqachon bor va to'g'ri naqsh. Kengaytirish kerak: retsept
birliklarida ziddiyat yo'qmi, narx tannarxdan pastmi, majburiy
maydonlar to'g'rimi.

---

## 4.4 Har vertikalga o'z agenti

Bugun 4 agent bor. Vertikal qo'shilgani sayin:

| Agent | Nima qiladi |
|---|---|
| sozlash | tizimni yig'adi (bor) |
| ombor / moliya / buyurtma | bor |
| **buxgalter** | provodka, hisobot, soliq deklaratsiyasi |
| **sotuvchi** | CRM: lid, voronka, keyingi qadam |
| **kassir** | POS: smena, chek, qaytarish |
| **kadrlar** | HR: davomat, oylik |
| **o'qituvchi** | LMS: kurs, dars, baho |

Har agent — **tizim ko'rsatmasi + asboblar qismi + rol cheklovi**.
Yangi agent qo'shish arzon, chunki halqa bitta (`suhbat_oqim`).

**Nega bitta katta agent emas:** 40 ta asbob berilsa model qaysi
birini chaqirishni chalkashtiradi va aniqlik tushadi. Bu amalda
tekshirilgan.

---

## 4.5 Model tanlash strategiyasi

Bugun: uch provayder, kvota tugasa keyingisiga o'tadi. Kengaytirish:

| Vazifa | Model |
|---|---|
| Oddiy savol («qancha qarz?») | arzon/tez (flash, mini) |
| Profil yasash, murakkab reja | kuchli (pro, opus) |
| Embedding | maxsus embedding modeli |

Sabab: profil yasash — bir marta, murakkab, xato qimmat. Kundalik
savol — tez-tez, sodda. Bittasiga kuchli model ishlatib pulni
yoqmaslik kerak.

---

## 4.6 Sinash — AI ni qanday tekshirish

AI javobi har safar boshqacha. Shuning uchun **oddiy test yetarli
emas**. Kerak:

1. **Oltin to'plam** — 50–100 savol va kutilgan natija:
   «Kim eng ko'p qarzdor?» → `qarzdorlar` asbobi chaqirilishi SHART,
   javobdagi raqam bazadagiga TENG bo'lishi shart
2. **Asbob chaqiruvi tekshiruvi** — matnni emas, qaysi asbob
   chaqirilganini tekshirish (barqaror)
3. **Raqam tekshiruvi** — AI aytgan raqam bazadagi bilan bir xilmi
   (aynan shu tekshiruv «AI 1 457 mln, ekran 853 mln» xatosini
   topgan bo'lardi)
4. **Regressiya** — model yoki ko'rsatma o'zgarganda qayta yurgizish

Bu `tests/ai_oltin_toplam.py` sifatida `sinov.sh` ga qo'shiladi.
