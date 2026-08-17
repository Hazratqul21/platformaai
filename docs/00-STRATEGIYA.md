# 0. STRATEGIYA — biz nima qilyapmiz

> Bu hujjat qolgan hammasining boshi. Bir savolga javob beradi:
> **nima uchun bizni tanlashadi?**

---

## 0.1 Maqsad

Oddiy odam AI bilan gaplashib o'ziga tizim yasab olsin — ERP, POS,
CRM, WMS, LMS, buxgalteriya. Har sohada, dasturchisiz.

## 0.2 Kim bilan raqobat

| Raqobatchi | Kuchi | Zaifligi (bizning imkoniyatimiz) |
|---|---|---|
| **1C** | O'zbekistonda hukmron, buxgalteriya kuchli | joriy qilish oylar, dasturchi kerak, eski interfeys |
| **Odoo** | modul ko'p, ochiq kod | mahalliy qonunchilik yo'q, sozlash uchun mutaxassis kerak |
| **SAP** | yirik korxona | narxi va murakkabligi kichik biznesga to'g'ri kelmaydi |
| **amoCRM / Bitrix24** | CRM kuchli | faqat CRM, ishlab chiqarish va ombor yo'q |
| **MoySklad** | sodda, tez | konstruktor emas, chuqurlik yo'q |

### Ular birgalikda qoldirgan bo'shliq

```
1C     — chuqur, lekin qiyin va sekin
MoySklad — oson, lekin sayoz
Odoo   — moslashuvchan, lekin mahalliy emas
```

**Hech biri: chuqur + oson + mahalliy + AI bilan yig'iladigan.**

---

## 0.3 Bizning ikki ustunligimiz

### 1. AI konstruktor — «yig'ib beriladi, sozlanmaydi»

Odoo yoki 1C ni joriy qilish = mutaxassis oylab sozlaydi. Bizda mijoz
biznesini **aytadi**, tizim yig'iladi.

Bu shior emas — arxitekturada allaqachon bor: 22 soha **bitta kod**
bilan ishlaydi, yangi soha = JSON, AI shu JSON ni to'ldiradi.

### 2. Mahalliylik

EHF, fiskal, Payme/Click/Uzum, so'm, BHMS, o'zbek tili — Odoo va SAP
da bularning hech biri yo'q, har biri alohida loyiha bo'ladi.

> **Ikkisi birga:** «O'zbekiston qonunchiligini biladigan, AI yig'ib
> beradigan tizim». Bu bo'shliqda hozircha hech kim yo'q.

---

## 0.3b QABUL QILINGAN QARORLAR (2026-08-15)

Bular muhokama qilingan va **o'zgartirilmaydi**. Qolgan hamma reja
shularga bo'ysunadi.

| # | Qaror | Nimaga ta'sir qiladi |
|---|---|---|
| 1 | **Hammasi qonuniy bo'ladi.** Sertifikatlashdan o'tamiz | POS, EHF, fiskal — chetlab o'tilmaydi |
| 2 | **AI xarajati mijozdan ALOHIDA olinadi** | hisoblash va cheklash mexanizmi kerak |
| 3 | ~~Mijoz o'z serverida ishlata oladi~~ → **2026-08-18 da o'zgardi**, pastga qarang | — |
| 4 | **Loyiha umumiy** — Odoo/1C kabi, bitta sohaga xos emas | qobiliyatlar o'lchovi majburiy bo'ladi |

### 3-QAROR O'ZGARDI (2026-08-18): BITTA WEB PLATFORMA (SaaS)

```
❌ ESKI:  mijoz o'z serveriga o'rnatadi, litsenziya kaliti, AI shlyuzi
✅ YANGI: hamma narsa bitta web platformada — app.innasoft.uz
```

Firma ro'yxatdan o'tadi → AI bilan gaplashadi → tizim yig'iladi.
Serverni, yangilanishni, zaxirani **biz boshqaramiz**.

**Nega:** on-premise ning har bir og'ir muammosi (AI kalitini
himoyalash, sarfni hisoblash, yangilash, qo'llab-quvvatlash, xato
topish) SaaS da o'z-o'zidan yo'qoladi. Ular mijozga qiymat emas
edi — faqat tarqatishning narxi edi.

**2 va 3-qarordagi ziddiyat shu bilan yopildi:** AI kodi bizning
serverda, demak kalit bizda va har so'rov loglanadi. Shlyuz keraksiz.

**On-premise bekor emas — kechiktirildi.** Platforma 3–5 mijozda
barqaror ishlagandan keyin qilinadi. Tafsilot:
[07-TARQATISH.md](07-TARQATISH.md).

---

## 0.4 ENG MUHIM QAROR: qayerdan boshlash

Odoo+SAP+1C+amoCRM+Bitrix24+call-center — bu **minglab odam-oy**.
Hammasini birdan boshlash = hech biri tugamaydi.

### Nima uchun ISHLAB CHIQARISH + SAVDO dan boshlaymiz

1. **Bizda allaqachon ishlaydi** — 22 soha, haqiqiy mijozda sinalgan
2. **Eng og'ir qism** — retsept, tannarx, FIFO, brak. CRM yoki LMS
   ga qaraganda ancha murakkab. Og'irini qilganmiz.
3. **Raqobat kam** — 1C dan boshqa hech kim ishlab chiqarishni
   normal qilmaydi
4. **Mijoz bor** — Rustam akaning tizimi ishlab turibdi

### Kengayish tartibi va sababi

```
1. ISHLAB CHIQARISH + SAVDO    ← bor, mustahkam
2. BUXGALTERIYA (Bosh kitob)   ← hammasining ostidagi poydevor
3. CHAKANA / POS               ← eng katta bozor, lekin sertifikat kerak
4. CRM                         ← savdo ustiga tabiiy qo'shiladi
5. WMS (chuqur ombor)          ← mavjud ombor kengaytiriladi
6. LMS                         ← eng uzoq, boshqa bozor
```

**Nega buxgalteriya ikkinchi:** POS ham, CRM ham, WMS ham oxir-oqibat
pulga borib taqaladi. Bosh kitob bo'lmasa har vertikal o'z hisobini
yozadi va ular bir-biriga to'g'ri kelmaydi. Bu allaqachon bir marta
bo'lgan — oltita xato aynan shundan chiqqan edi.

---

## 0.5 Nima bizni o'ldirishi mumkin

Ochiq gapiramiz.

| Xavf | Nima bo'ladi | Qanday oldini olamiz |
|---|---|---|
| **Hammasini birdan qilish** | hech biri tugamaydi | qat'iy tartib, har bosqich yakunlanadi |
| **AI noto'g'ri raqam berishi** | bir marta yetadi — ishonch yo'qoladi | raqam faqat asbobdan, RAG bilan aralashmaydi |
| **AI o'zi yozib qo'yishi** | mijoz bazasi buziladi | tasdiq tugmasi, auditga odam yoziladi |
| **Sertifikat kutish** | tayyor kod oylab yotadi | ariza koddan OLDIN boshlanadi |
| **Ijarachiliksiz sotish** | har mijozga alohida server | 2-bosqichda hal qilinadi |
| **Buxgalteriyasiz «uchetka» va'da qilish** | mijoz aldangan bo'ladi | GL tayyor bo'lgunicha bunday va'da yo'q |
| **AI xarajati** | har savol pul | arzon model oddiy savolga, kuchli — murakkabga |

---

## 0.6 Nimani VA'DA QILMAYMIZ (hozircha)

Halollik — sotuvda ham muhim:

- ❌ «To'liq buxgalteriya» — Bosh kitob yo'q ekan, aytilmaydi
- ❌ «Qonuniy POS» — reyestrdan o'tmagan ekan, aytilmaydi
- ❌ «Yuridik kuchga ega hujjat» — EHF ulanmagan ekan, aytilmaydi
- ❌ «Ko'p mijozli bulut» — ijarachilik yo'q ekan, aytilmaydi

Bugun halol va'da: **«Ishlab chiqarish va savdo uchun AI yig'adigan
ERP. 22 soha tayyor, sizniki ro'yxatda bo'lmasa AI yasab beradi.»**

Bu ham kam emas — 1C da bunday yo'q.

---

## 0.7 Muvaffaqiyat o'lchovi

Har bosqich shu savollarga javob berishi kerak:

1. **Vaqt:** yangi mijoz nol holatdan ishlaydigan tizimgacha necha
   soatda yetadi? (Maqsad: 1 kun. Odoo/1C da — haftalar)
2. **Dasturchisiz:** mijoz o'zi sozlay oldimi, yoki bizni chaqirdimi?
3. **To'g'rilik:** `butunlik.py` toza o'tadimi?
4. **AI aniqligi:** oltin to'plamda necha foiz to'g'ri?

---

## 0.8 Hujjatlar ro'yxati

| Hujjat | Nima haqida |
|---|---|
| [01-HOZIRGI-HOLAT.md](01-HOZIRGI-HOLAT.md) | nima bor, nima yo'q — raqamlar bilan |
| [02-QONUNCHILIK.md](02-QONUNCHILIK.md) | EHF, fiskal, BHMS — majburiy talablar |
| [03-ARXITEKTURA.md](03-ARXITEKTURA.md) | qobiliyatlar, Bosh kitob, ijarachilik |
| [04-AI-VA-RAG.md](04-AI-VA-RAG.md) | agent, RAG quvuri, sinash |
| [05-INTEGRATSIYALAR.md](05-INTEGRATSIYALAR.md) | to'lov, soliq, telefoniya |
| [06-YOL-XARITASI.md](06-YOL-XARITASI.md) | bosqichlar, tartib, qaror nuqtalari |
| [07-TARQATISH.md](07-TARQATISH.md) | SaaS qarori, ma'lumot ajratish, AI sarfi, tarif |
| [08-FRONTEND.md](08-FRONTEND.md) | hozirgi holat, modernizatsiya tartibi |
| [A-IJARACHILIK.md](A-IJARACHILIK.md) | **A bosqichining ish hujjati** — jadval, endpoint, sinov mezoni |
