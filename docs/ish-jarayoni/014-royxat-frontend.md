# 014 — RO'YXATDAN O'TISH FRONTEND

**Sana:** 2026-08-18
**Holat:** ✅ brauzerda to'liq oqim ishladi (baza yaratildi)

---

## Nima qilindi

Lending'dagi «Ro'yxatdan o'tish» tugmasi endi **haqiqiy forma**
ochadi: firma nomi, subdomen, soha, login, parol. Yuborilganda
013-qadamdagi backend chaqiriladi va baza tayyorlanishi kuzatiladi.

Bu — A bosqichining vizual yakuni: 009–013 backend endi ekrandan
foydalanib bo'ladigan bo'ldi.

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `static/js/core/lending.js` | `lendingRoyxat()` haqiqiy forma; `royxatYubor`, `royxatHolatKuzat`, `royxatKodTozala` (+150 qator) |
| `static/css/style.css` | overlay `z-index` 100 → 200 (modal lending ustida) |

Backend `royxat.py` ga tegilmadi — u 013-qadamda tayyor edi.

---

## Uch qaror

### 1. Subdomen nomdan avtomatik taklif qilinadi

Foydalanuvchi «Mebel Sex MCHJ» yozganda subdomen `mebel-sex-mchj`
bo'lib to'ldiriladi. Lekin u subdomen maydonini **qo'lda tegsa**,
avtomatik to'ldirish to'xtaydi (`dataset.qol`). Aks holda odam
subdomen yozayotganda nomga har tegilganda ustidan yozib ketilardi.

`royxatKodTozala` — kichik harf, faqat harf/raqam/tire. Backenddagi
`kod_tekshir` bilan bir xil qoida, lekin bu yerda **darhol** —
foydalanuvchi noto'g'ri belgi kiritsa ko'rmaydi ham.

### 2. Baza tayyorlanishi kuzatiladi (polling)

`/royxat` javobi darhol qaytadi (baza fon vazifasida), shuning uchun
frontend `/holat/{kod}` ni **15 marta, 0,7 soniyada** so'raydi:
`tayyorlanmoqda → tayyor` yoki `xato`.

Xato bo'lsa izoh ko'rsatiladi va «Qayta urinish». Yolg'on «tayyor»
ko'rsatilmaydi — holat backenddan keladi.

### 3. Overlay z-index — topilgan nuqson

Forma ochildi, lekin **ko'rinmadi**: overlay `z-index:100`, lending
`z-index:140` — modal lending ortida qoldi. Brauzerda `getComputedStyle`
bilan aniqlandi (`show=true` lekin ko'rinmaydi).

Overlay `z-index:200` ga ko'tarildi — u har doim eng ustda bo'lishi
kerak (login-screen 150, lending 140 dan yuqori).

> Bu faqat brauzerda ko'rinadigan nuqson edi — kod «to'g'ri»
> ko'rinardi, lekin foydalanuvchi hech narsa ko'rmasdi. Shuning
> uchun frontendni brauzerda haqiqiy sinash shart.

---

## Sinov — brauzerda, haqiqiy provisioning bilan

Server ijarachilik rejimida (`IJARACHILIK=1`, SQLite baza shabloni):

| Qadam | Natija |
|---|---|
| Forma ochiladi, to'liq ko'rinadi | ✅ overlay 200 dan keyin |
| Nomdan subdomen taklif qilindi | ✅ `mebel-sex-demo` |
| «Yaratish» → fon vazifasi | ✅ 3 soniyada tayyor |
| «✓ Tayyor! mebel-sex-demo.innasoft.uz» | ✅ ko'rsatildi |
| Firma bazasi diskda | ✅ `inna_mebel_sex_demo.db` |
| Faol soha | ✅ **Mebel sexi** (22 profil yuklandi) |
| Admin | ✅ `parol_almashtirilsin=0` (ro'yxatda o'rnatildi) |
| Konsol xatolari | ✅ yo'q |

---

## Nimaga tegdi

Overlay z-index butun ilovada modal uchun ishlatiladi. 100 → 200
o'zgarishi modalni har doim eng ustga chiqaradi — bu to'g'ri
xatti-harakat, boshqa modallar ham lending/login ustida bo'lishi
kerak. Regressiya xavfi yo'q (hech narsa overlay dan yuqori bo'lishi
kerak emas edi).

---

## Qoldi

1. Tasdiqlash kodi (telefon/email) — hozir to'g'ridan-to'g'ri
2. Platforma kabineti ekrani (`/kir` bor, ekran yo'q) — tarif, AI sarfi
3. Til: forma faqat lotin o'zbekcha (kirill/rus keyin)
4. Baza tayyorlanayotganda «bir necha soniya» animatsiyasi yaxshilanishi
