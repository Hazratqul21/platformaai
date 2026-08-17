# 7. TARQATISH — WEB PLATFORMA (SaaS)

> **QAROR O'ZGARDI (2026-08-18).** Oldingi reja — «mijoz o'z serveriga
> o'rnatadi + litsenziya kaliti + AI shlyuzi» — **BEKOR QILINDI**.
> Sabab va yangi reja shu hujjatda.

---

## 7.1 Nima o'zgardi

| Eski reja (bekor) | Yangi reja (amalda) |
|---|---|
| ❌ mijoz o'z serverida o'rnatadi | ✅ hamma narsa bitta web platformada |
| ❌ litsenziya kaliti bilan nazorat | ✅ obuna — bazada, tekshirish shart emas |
| ❌ AI shlyuzi (`ai.innasoft.uz`) | ✅ AI kodi serverning o'zida — shlyuz keraksiz |
| ❌ 30 kunlik oflayn muhlat, diagnostika arxivi, masofaviy tunnel | ✅ server bizda — loglar to'g'ridan-to'g'ri |

Eski reja **noto'g'ri emas edi** — u faqat **erta** edi. Mijoz
serveriga chiqarish uchun avval bitta yaxshi ishlaydigan platforma
kerak. Uni yasamasdan tarqatish mexanizmini qurish = ishlatilmaydigan
murakkablik.

---

## 7.2 Nega SaaS — muammolar ro'yxati bilan

Eski rejadagi har bir og'ir muammo SaaS da **o'z-o'zidan yo'qoladi**:

| Muammo | On-premise da | SaaS da |
|---|---|---|
| AI kalitini himoyalash | shlyuz kerak | ✅ kalit bizda, mijoz ko'rmaydi |
| AI sarfini hisoblash | shlyuz kerak | ✅ har so'rov shu yerda loglanadi |
| Yangilash | 20 ta o'rnatma, har xil versiya | ✅ bir marta — hammaga |
| Qo'llab-quvvatlash | diagnostika arxivi, tunnel | ✅ logga o'zimiz qaraymiz |
| Xato topish | mijoz aytguncha bilmaymiz | ✅ real vaqtda ko'ramiz |
| Migratsiya xatosi | mijozning bazasi buzildi | ✅ zaxira va tiklash bizda |
| Xavfsizlik yamog'i | har mijozni ko'ndirish | ✅ bir joyda |

**Xulosa:** SaaS bitta qaror bilan yetti muammoni yopadi. Ularning
hech biri mijoz uchun qiymat emas edi — faqat tarqatishning narxi edi.

---

## 7.3 SaaS arxitekturasi

```
                     app.innasoft.uz
                            │
              ┌─────────────┴─────────────┐
              │      YAGONA KOD BAZASI    │
              │  (FastAPI + AI + GenUI)   │
              └─────────────┬─────────────┘
                            │  so'rovdan mijoz aniqlanadi
        ┌───────────┬───────┴───────┬───────────┐
        ▼           ▼               ▼           ▼
   mijoz_1_db   mijoz_2_db     mijoz_3_db   ...
   (mebel)      (non)          (karton)

              ┌────────────────────────────┐
              │  platforma_boshqaruv_db    │
              │  firmalar · tarif · obuna  │
              │  AI sarfi · audit          │
              └────────────────────────────┘

              AI kalitlari — SERVER `.env` da, faqat bizda
```

Bu — **BOSQICH A (ijarachilik)** ning aynan o'zi. Ya'ni SaaS qarori
yo'l xaritasini o'zgartirmaydi, faqat **A ni yanada majburiyroq**
qiladi va B–G ni soddalashtiradi.

---

## 7.4 Mijozning yo'li (nol holatdan ishlaydigan tizimgacha)

```
1. Ro'yxatdan o'tish        telefon/email → tasdiqlash
2. Firma ma'lumoti          nom, INN, QQS to'lovchimi
3. AI BILAN SUHBAT          «mebel sexim bor, 12 xodim, 3 xil mahsulot»
4. Tizim yig'iladi          profil + retsept + qobiliyatlar + rollar
5. Sinov buyurtmasi         AI o'zi tekshiradi, raqamni ko'rsatadi
6. Xodimlarni chaqirish     rol berish
7. ISHLAYDI
```

**Maqsad: 1 kun ichida.** Odoo/1C da bu — haftalar, mutaxassis bilan.
Bu bizning asosiy o'lchovimiz ([00-STRATEGIYA.md](00-STRATEGIYA.md) §0.7).

---

## 7.5 Ma'lumot ajratish — eng muhim texnik talab

SaaS da eng katta xavf: **bir mijoz ikkinchisining ma'lumotini
ko'rishi**. Bu bir marta bo'lsa loyiha tugaydi.

### Qaror: HAR MIJOZGA ALOHIDA BAZA

Schema yoki `mijoz_id` ustuni emas — **alohida baza**. Sabab:

| Yo'l | Xavf |
|---|---|
| `mijoz_id` ustuni | bitta unutilgan `WHERE` = sirning oshkor bo'lishi |
| Alohida schema | ulanish yo'li adashsa — o'sha xavf |
| **Alohida baza** | ✅ ulanish noto'g'ri bo'lsa jadval umuman topilmaydi |

Narxi: migratsiya hamma bazada yurishi kerak, zaxira ko'p. Bu
qabul qilinadigan narx.

### Unutilmaydigan uchta joy

1. **`domain.py` profil keshi** — hozir GLOBAL. Mijoz bo'yicha
   kalitlanmasa, A mijozning profili B ga ko'rinadi. Kodda
   ogohlantirish yozilgan.
2. **Ulanishlar hovuzi** — mijoz bo'yicha, chegarali (bitta mijoz
   hammani band qilib qo'ymasin).
3. **Fon vazifalari** — cron/worker qaysi mijoz uchun ishlayotganini
   aniq bilishi shart.

### Isbot — sinovsiz «tayyor» deb aytilmaydi

`tests/ijarachilik.py`: ikki mijoz yaratiladi, ikkalasiga ma'lumot
yoziladi, keyin **har endpoint** birinchi mijozning tokeni bilan
ikkinchisining ID lariga urinib ko'riladi. Bittasi ham o'tmasligi
shart.

---

## 7.6 AI xarajati — SaaS da qanday

Qaror o'zgarmaydi: **AI xarajati mijozdan alohida olinadi.** Faqat
mexanizm soddalashadi — shlyuz kerak emas, chunki AI kodi bizning
serverda.

### Yoziladigan ma'lumot (`platforma_boshqaruv` bazasida)

| Maydon | Nima uchun |
|---|---|
| mijoz, sana/vaqt | kimga hisob |
| provayder, model | narx shundan |
| kirish/chiqish tokenlari | asosiy o'lchov |
| narx (o'sha paytdagi) | **qotiriladi** — narx keyin o'zgarsa eski hisob buzilmasin |
| agent, foydalanuvchi | mijoz ichida kim ko'p sarflaydi |

Narxni qotirish — QQS stavkasini buyurtmada qotirish bilan bir xil
naqsh. U yerda ishlagan.

### Mijoz nimani ko'radi

«AI» bo'limida, doim:

```
Bu oy: 1 240 so'rov · 4.2 mln token · 186 000 so'm
Limit: 250 000 so'm (74% ishlatilgan)

Eng ko'p: Moliya yordamchisi (42%)
Foydalanuvchi bo'yicha: Aziz (31%), Dilshod (24%)...
```

**Shaffoflik majburiy** — tushuntirishsiz kelgan hisob ishonchni
yo'qotadi.

### Limit

- Mijoz o'zi oylik limit qo'yadi
- 80% da ogohlantirish, 100% da **AI to'xtaydi — ERP ishlayveradi**
- Limitni oshirish tizim ichidan, bir tugma

### Model tanlash — pulni tejash

[04-AI-VA-RAG.md](04-AI-VA-RAG.md) §4.5 dagi qoida shu yerda pulga
aylanadi: oddiy savolga arzon model (flash/mini), profil yasashga
kuchli model. Har savolga `opus` ishlatish = zararga ishlash.

---

## 7.7 Tarif

| Tarif | Kimga | Ichida |
|---|---|---|
| **Boshlang'ich** | 1–5 foydalanuvchi | asosiy qobiliyatlar, AI cheklangan |
| **Biznes** | 5–30 | hamma qobiliyat, AI paketi |
| **Korxona** | 30+ | maxsus sozlash, ustuvor yordam |

AI — **har tarifda alohida qator**. Tarif narxiga qo'shib
yuborilmaydi, chunki sarf mijozdan mijozga o'nlab marta farq qiladi.

Obuna tugasa: **ma'lumot bloklanmaydi.** Faqat yozish to'xtaydi,
o'qish va eksport ochiq qoladi. Sabab — mijozning ma'lumoti garovga
olinmaydi. Bu qoida eski rejadan o'zgarishsiz ko'chadi.

---

## 7.8 Infratuzilma

| Nima | Qaror |
|---|---|
| VM | 1-bosqich: 8 vCPU / 16 GB / NVMe. O'sishga qarab kattalashtiriladi |
| Baza | PostgreSQL 16, alohida disk, `pgvector` (RAG uchun) |
| Zaxira | kunlik to'liq + WAL. **Tiklash oyda bir marta SINALADI** |
| Ishga tushirish | Docker Compose → keyinroq kerak bo'lsa k8s |
| Monitoring | xatolar, javob vaqti, AI sarfi, disk |
| Domen | `app.innasoft.uz`, mijoz subdomeni: `mijoz.innasoft.uz` |

**Zaxira haqida:** sinalmagan zaxira — zaxira emas. Oyda bir marta
bo'sh bazaga tiklanadi va `butunlik.py` yurgiziladi.

---

## 7.9 On-premise — KEYINROQ, bekor emas

Mijoz serveriga o'rnatish **kerak bo'ladi** — bank, davlat, yirik
korxona ma'lumot chiqishini xohlamaydi. Lekin:

**Shart:** platforma kamida 3–5 mijozda barqaror ishlagandan keyin.

O'shanda kerak bo'ladigan narsalar (eski rejadan saqlanadi):

- litsenziya kaliti, **30 kunlik oflayn muhlat** (internet uzilsa
  korxona to'xtamasin)
- AI: mijozning o'z kaliti yoki lokal model (Ollama) —
  `llm.py` `OPENAI_BASE_URL` orqali allaqachon qo'llab-quvvatlaydi
- Docker obraz, semantik versiya, avtomatik yangilanish (zaxira → 
  yangilanish → xato bo'lsa qaytarish)
- Diagnostika to'plami, salomatlik signali

Bu ro'yxat **arxiv sifatida** shu yerda turadi. Vaqti kelganda
alohida hujjat yoziladi.

---

## 7.10 Bu bosqich qachon qilinadi

SaaS — alohida bosqich EMAS. U **BOSQICH A (ijarachilik)** ning
o'zi, ustiga ro'yxatdan o'tish, tarif va AI sarfi qo'shiladi.

**Vaqt:** A (3–4 hafta) + ro'yxatdan o'tish/tarif/AI hisobi
(1–2 hafta) = **4–6 hafta**.
