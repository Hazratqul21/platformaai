# 010 — LENDING SAHIFASI (kirishda)

**Sana:** 2026-08-18
**Holat:** ✅ ishlaydi, brauzerda tekshirildi

---

## Nima qilindi

Kirishda birinchi ko'rinadigan **tanishtiruv sahifasi**. Login oynasi
endi undan keyin ochiladi.

**Nega:** ilgari sahifaga birinchi kelgan odam login oynasini
ko'rardi. Login oynasi «bu nima?» degan savolga javob bermaydi — u
faqat **allaqachon biladigan** odam uchun. Platforma ko'p mijozli
bo'layotgani uchun birinchi ekran nima taklif qilinayotganini
ko'rsatishi kerak.

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `static/js/core/lending.js` | **yangi**, 62 qator |
| `static/index.html` | lending bloki (+112 qator), login `display:none`, «← Orqaga» tugmasi |
| `static/css/style.css` | `/* LENDING */` bo'limi, +51 qator (402 → 460) |
| `static/js/app.js` | tokensiz holatda `lendingBoshla()` |

Backendga **tegilmadi** — bu to'liq frontend ishi.

---

## Sahifaning tuzilishi

```
1. Yuqori panel      logo · Ro'yxatdan o'tish · Kirish
2. Hero              «Biznesingizni ayting — tizim o'zi yig'ilsin»
3. Uch karta         AI konstruktor · Bitta tizim · Mahalliy
4. Tayyor sohalar    22 chip + «+ sizniki — AI yasab beradi»
5. Ochiq gapiramiz   nima ishlaydi / nima hali yo'q
6. Tariflar          Boshlang'ich · Biznes · Korxona
7. Footer            obuna tugasa ma'lumot o'chirilmaydi
```

---

## Uch qaror

### 1. «Ochiq gapiramiz» bo'limi — bu sotuv sahifasida g'alati, lekin ataylab

Ko'p lending faqat yaxshi tomonni ko'rsatadi. Bu yerda **hali
yo'q** narsalar ham yozilgan: Bosh kitob, online to'lov, EHF, fiskal
kassa, CRM/WMS/LMS.

Sabab — [../00-STRATEGIYA.md](../00-STRATEGIYA.md) §0.6 dagi qoida:
tayyor bo'lmagan narsa va'da qilinmaydi. Mijoz «to'liq buxgalteriya»
deb kelib, keyin yo'qligini bilsa — ishonch bir marotaba yo'qoladi.

Bu bo'lim o'sha qoidaning **ekrandagi ko'rinishi**. Reja o'zgarsa
bu ro'yxat ham yangilanadi.

### 2. Soha ro'yxati JS da qo'lda yozilgan, API dan olinmaydi

Lending **login bo'lmagan** holatda ochiladi, ya'ni API yopiq
(hamma endpoint `Depends(get_user)` talab qiladi).

Ro'yxatni ochiq endpointdan berish mumkin edi, lekin bu himoya
yuzasini kengaytiradi. 22 ta nom kamdan-kam o'zgaradi — qo'lda
ro'yxat arzonroq va xavfsizroq.

> Yangi soha qo'shilsa `LND_SOHALAR` ni yangilash kerak. Bu qarz
> — kodda izoh bilan belgilangan.

### 3. «Ro'yxatdan o'tish» tugmasi yolg'on gapirmaydi

Ro'yxatdan o'tish hali yozilmagan (A bosqichida bo'ladi). Tugmani
umuman qo'ymaslik ham mumkin edi, lekin u sahifaning kelajakdagi
shaklini ko'rsatadi.

Bosilganda **halol javob**: «Ro'yxatdan o'tish tayyorlanmoqda.
Hozir tizimga mavjud login bilan kiriladi.» Ishlamaydigan forma
ochib, keyin xato bermaydi.

---

## Xavfsizlik

Soha nomlari `textContent` bilan qo'yiladi, `innerHTML` bilan emas —
`genui.js` dagi qoida bilan bir xil. Hozir ro'yxat kodda, lekin
keyinroq API dan kelsa qoida allaqachon o'rnida bo'ladi.

---

## Tekshiruv (brauzerda, haqiqiy serverda)

Server: `uvicorn app.main:app --port 8071`.

| Tekshiruv | Natija |
|---|---|
| Lending ochiladi, login yashirin | ✅ `lendingOn=true, login=none` |
| 22 soha + AI chipi | ✅ 23 element |
| «Kirish» → login, fokus login maydonida | ✅ `login=flex, fokus=lg` |
| «← Orqaga» → lending | ✅ qaytdi |
| «Ro'yxatdan o'tish» → halol xabar | ✅ toast chiqdi |
| Konsol xatolari | ✅ yo'q |
| Mobil (375×812) | ✅ chiplar qatorlarga bo'linadi |

### Mobilda topilgan va tuzatilgan nuqson

Yuqori panel 375px ekranda **386px** kenglik talab qildi — tugmalar
kesilardi. `@media(max-width:520px)` qo'shildi: panel ikki qatorga
tushadi, tugmalar teng bo'linadi. Qayta tekshirildi — toza.

---

## Nimaga tegdi

Hech nimaga. Tokeni bor foydalanuvchi lendingni **umuman ko'rmaydi** —
`app.js` uni to'g'ri `enterApp()` ga o'tkazadi. `logout()` sahifani
qayta yuklaydi va lending ochiladi.

---

## Qoldi

- Ro'yxatdan o'tish oqimi (A bosqichi)
- Tarif narxlari — hozir faqat nomlar, raqam yo'q
- Rus va kirill tarjimasi (lending hozir faqat lotin o'zbekchada)
