# 007 — SINOV VA VOSITALAR

**Sana:** retrospektiv
**Fayllar:** `tests/` (8 fayl) · `tools/` (3 fayl) · `sinov.sh`

---

## Sinov falsafasi

Ikki xil savol bor va ular **boshqa-boshqa**:

```
«200 qaytdimi?»        →  profil_test.py, audit.py
«RAQAM to'g'rimi?»     →  chuqur_sinov.py, butunlik.py
```

Ikkinchisi muhimroq. Moliyaviy tizimda 200 qaytarib **noto'g'ri
raqam** berish — 500 xatosidan yomonroq, chunki hech kim sezmaydi.

---

## `himoya_audit.py` — eng arzon va eng foydali

**Server kerak emas.** Kodni AST bilan o'qiydi va `Depends(get_user)`
siz endpointni topadi.

Bir marta shunday xato bo'lgan — endpoint qo'shilib himoya unutilgan.
Endi bu test uni ushlaydi. **125/125 himoyalangan.**

> Bu naqsh takrorlanadi: ijarachilikda `tests/ijarachilik.py` xuddi
> shunday, lekin **boshqa firmaning tokeni bilan** sinaydi.

---

## `profil_test.py` — 22 soha avtomat

Yangi soha qo'shilganda uni qo'lda sinash kerak bo'lmasin. Profil
qo'shildi → test avtomat tekshiradi: forma chizildimi, buyurtma
yaratildimi, status o'tdimi, retsept ishladimi.

---

## `chuqur_sinov.py` — raqam tekshiruvi

Har sohada: smeta to'g'ri hisoblandimi, QQS to'g'rimi, FIFO qaysi
partiyadan yechdi, qarz qancha bo'ldi.

**Bu test ikki marta o'zim xato qilganimni ko'rsatdi:**

1. QQS nisbati aynan 1.12 bo'ladi deb tasdiq yozgan edim — noto'g'ri
   edi, chunki `ichida` rejimida boshqacha. **Testni tuzatdim,
   tizimni emas.**
2. Test faqat `ogohlantirish` kalitini o'qirdi, karton esa
   `narx_ogoh` qaytarardi — natijada 487 so'm/quti degan xato narx
   **to'g'ri ko'rinib turdi**. Endi uchala kalit ham yig'iladi.

Ikkinchisi muhim saboq: **test o'zi ko'r bo'lsa, u yashil rang
beradi va ishonch soxta bo'ladi.**

---

## `jonli_agent_test.py` — haqiqiy LLM

Boshqalardan farqi: haqiqiy provayderga so'rov yuboradi. Kalit
bo'lmasa **o'zi o'tkazib yuboradi** — `sinov.sh` yiqilmasin.

---

## `tools/kochir.py` — mijoz ma'lumotini ko'chirish

Eski TIZIM ERP (SQLite) → platforma bazasi.

**Xavfsizlik qarori:**

```python
sqlite3.connect(f"file:{fayl}?mode=ro", uri=True)
```

Manbaga yozish **SQLite darajasida imkonsiz** — kodda xato bo'lsa ham.
Mijozning yillar davomida yig'ilgan ma'lumoti bilan ishlaganda
«ehtiyot bo'laman» yetarli emas, texnik kafolat kerak.

`--tekshir` rejimi avval sanaydi, keyin ko'chiradi.

---

## `tools/demo_data.py` — 22 sohaga demo

**Nega kerak:** bo'sh tizimda hamma narsa chiroyli ko'rinadi.
Muammolar ma'lumot to'planganda chiqadi — qarz yoshi, FIFO,
kechikkan buyurtma.

Materiallar `p.retsept` dan olinadi — ya'ni **AI yaratgan soha uchun
ham ishlaydi**, ro'yxatga bog'lanmagan.

O'lchamlar uchburchak taqsimot (kichikroq tomonga og'gan) — haqiqiy
buyurtmalar shunday.

---

## `tools/butunlik.py` — 14 o'zgarmas

Hech narsa yozmaydi, **prodda ham ishlaydi**.

Tekshiradi: qarz ikki yo'lda bir xilmi · qarz yoshi bo'laklari
jamiga tengmi · kutilayotgan kirim umumiy qarzdan oshmaydimi ·
partiyalar yig'indisi qoldiqqa tengmi · kassa jurnali pul
harakatlariga mosmi...

**Bu — oltita xatoning qaytmasligining kafolati** (003-yozuv).
Tuzatish yetarli emas, qo'riqchi kerak.

---

## `sinov.sh` — 9 bosqich

Har to'plam **toza bazada**. Sabab: `e2e_test.py` holatga bog'liq
(foydalanuvchi yaratadi, parol almashtiradi). Har safar to'liq
yurgizish kerak.

Sinov paroli: `Sinov2026Parol`.
