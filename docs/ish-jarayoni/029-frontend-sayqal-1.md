# 029 — FRONTEND SAYQALI (1-tur)

**Sana:** 2026-08-20
**Holat:** ✅ ikki rough edge tuzatildi, hamma bo'lim ko'rildi
**So'rov:** «frontendni mukammallashtirish — hamma bo'lim»

---

## Usul

karton.innasoft.uz (Rustam akaning haqiqiy ma'lumoti) da har bo'lim
ko'rildi — desktop va mobil. Muammolar yig'ildi, tuzatildi.

---

## Ko'rilgan bo'limlar

| Bo'lim | Holat |
|---|---|
| Dashboard | ✅ mukammal (KPI, savdo grafigi, ogohlantirishlar) |
| Buyurtmalar | ✅ kartochka, status, eksport — rasm tuzatildi |
| Mijozlar | ✅ mukammal (qarz, qidiruv, kategoriya) |
| Ombor | ✅ FIFO, past qoldiq ogohi |
| Xodimlar | ✅ ro'yxat, oklad/sdelshina, oylik |
| Buxgalteriya | ✅ bo'sh holat tuzatildi |
| Mobil (dashboard) | ✅ responsive, pastki navigatsiya |

Umumiy xulosa: frontend allaqachon puxta qurilgan. Ikki aniq rough
edge topildi va tuzatildi.

---

## Tuzatilgan 1: buyurtma rasmlari 404

**Muammo:** buyurtma kartochkalarida rasm `/uploads/order_*.jpg`
so'ralardi, lekin fayllar Rustam serverida qolган — 404, brauzerda
buzuq rasm ikonkasi va konsolda 404 to'lqini.

**Yechim ikki qism:**
1. **Rasmlar ko'chirildi** — 79 fayl (5.6 MB) Rustam serveridan
   platforma `uploads` voluميga (manba read-only, tegilmadi). Endi
   mavjud rasmlar ko'rinadi.
2. **Graceful fallback** (`orders.js`): kartochka rasmi `onerror` da
   YASHIRINADI, tafsilot rasmi «Расм мавжуд эмас» placeholder ga
   almashadi. Manbada yo'q rasm ham endi buzuq ikonka ko'rsatmaydi.

> Qolgan 404 (manbada umuman yo'q rasmlar) — `onerror` yashiradi,
> foydalanuvchi ko'rmaydi. Konsoldagi 404 faqat texnik shovqin.

---

## Tuzatilgan 2: buxgalteriya bo'sh balansi

**Muammo:** karton'da balans AKTIV/PASSIV 0 ko'rsatardi — chalkash.
Sabab: ko'chirilgan tarixiy ma'lumotda provodka yo'q, GL faqat YANGI
amallardan boshlanadi.

**Yechim** (`hisob.js`): balans bo'sh bo'lsa 0 lar o'rniga
tushuntirish — «Бош китоб ҳали бўш», qanday to'lishi va boshlang'ich
qoldiqni qanday kiritish. Endi foydalanuvchi nima bo'layotganini
tushunadi.

---

## Nozik joy — uploads izolyatsiyasi

`uploads` volume hozircha AKKAUNTLAR ORASIDA UMUMIY. karton rasmlari
`/uploads/` da, texnik jihatdan mebel.innasoft.uz/uploads/ dan ham
ochsa bo'ladi (fayl nomi tasodifiy, xavf past). To'liq izolyatsiya
uchun uploads akkaunt-papkasiga bo'linishi kerak — alohida ish,
belgilab qo'yildi.

---

## Regressiya

Frontend o'zgarishlar statik — himoya/backend tegilmadi. JS sintaksis
tekshirildi.

---

## Qoldi (keyingi sayqal turlari)

1. uploads akkaunt bo'yicha ajratish
2. Boshlang'ich qoldiq sehrgari (balansni haqiqiy qilish)
3. Kabinet/tarif ekranlari
4. Qolgan bo'limlarni chuqurroq (moliya, kassa, xarid detali)
