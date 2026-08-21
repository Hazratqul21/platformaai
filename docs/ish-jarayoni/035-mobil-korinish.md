# 035 — Mobil ko'rinish: o'lchab topilgan 5 ta nuqson

Sana: 2026-08-21 · Bosqich: frontend sayqal · Holat: bajarildi

## Nima qilindi

`karton.innasoft.uz` (Rustam akaning haqiqiy ma'lumoti) 375×812 va
1280×800 o'lchamlarda **brauzerda o'lchab** ko'rildi — taxmin qilinmadi.
13 ta sahifaning har birida "ekrandan chiqib ketgan element bormi"
degan tekshiruv yurgizildi. Topilgan 5 ta nuqson tuzatildi.

Desktop dastlab ham toza edi (0 muammo). Mobilda esa quyidagilar
chiqdi:

| # | Nuqson | O'lchov |
|---|--------|---------|
| 1 | Jadval ustunlari kesilib, ko'rishning iloji yo'q | jadval 450px, ekran 375px, ota `overflow:visible` |
| 2 | Kartochka grid katakchasidan kengroq | karta 617px, katak 344px |
| 3 | Topbar ekrandan chiqib ketgan | userchip +72px, chiqish tugmasi +119px |
| 4 | Tab tugmalari 4 qatorga o'ralgan | balandligi ~200px |
| 5 | AI tugmasi pastki menyuni yopib turgan | tugma 309..361, menyu 10..365, ikkalasi ham z-index 60 |

## Fayllar

- `static/css/style.css` — asosiy o'zgarishlar shu yerda
- `static/js/pages/hisob.js` — inline grid o'rniga loyihaning klassi
- `static/js/pages/settings.js` — inline uslub o'rniga `.tabs` klassi

## Nega aynan shunday

**1 va 2 — bir muammoning ikki uchi.** Jadvalga `overflow-x:auto`
berish yetmadi: kartochka o'zi kengayib ketardi. Sabab — grid
elementining standart `min-width:auto` qiymati, u elementni
min-content dan kichrayishga qo'ymaydi. Shuning uchun jadvalni
suriladigan qilish bilan birga `.split > *, .grid > * {min-width:0}`
qo'shildi. Bittasini qo'shib ikkinchisini qo'shmaslik ishlamaydi —
buni o'lchov ko'rsatdi (birinchi urinishda `wh` sahifasi tuzalmadi).

**3 — topbar.** Xuddi shu `min-width:auto` tuzog'i, faqat flex da.
Uzun matn uch nuqta bilan kesiladi, firma tanlash maydoniga shift
qo'yildi, ≤520px da userchip dagi ism yashiriladi (avatar harfi
qoladi — kim kirgani baribir Sozlamalarda ko'rinadi).

**4 — tab qatori.** `flex-wrap:wrap` o'rniga bir qator + gorizontal
surish. Bu telefonda tanish naqsh va vertikal joyni tejaydi
(200px → 39px). `settings.js` da bu allaqachon inline uslub bilan
qilingan edi — umumiy `.tabs` klassiga chiqarildi, endi ikkala
sahifa bir xil.

**5 — AI tugmasi.** Mobilda menyudan yuqoriga ko'tarildi
(`bottom:84px`, `z-index:61`). Ilgari «Мижозлар» va «Яна» bandlari
bosilmasdi.

**Qo'shimcha — balans jadvali.** Umumiy mobil qoida jadvalga
`white-space:nowrap` beradi. Ko'p ustunli ro'yxatlar uchun to'g'ri,
lekin balansda 3 ta ustun bor va eng muhimi — SUMMA — o'ngga surilib
ko'rinmay qolardi. `table.oralsin` klassi qo'shildi: hisob nomi
o'raladi, summa joyida qoladi.

## Nimaga tegdi

Faqat CSS va ikkita sahifaning markup'i. Backend, ma'lumot, API
tegilmadi. `docker cp` bilan joylandi — statik fayl, qayta yig'ish
kerak emas.

`.split.teng` yangi klass: balansda Актив/Пассив teng bo'lishi kerak
(loyihaning standart `.split` i 1.3fr/1fr).

## Xavf

Past. Lekin `.split > *, .grid > * {min-width:0}` — keng qamrovli
qoida. U faqat ≤860px media so'rovi ichida, ya'ni desktopga
tegmaydi. Desktop 1280px da qayta o'lchandi — 13 sahifada 0 muammo,
regressiya yo'q.

## Tekshiruv

Brauzerda o'lchandi, ko'z bilan ham ko'rildi:

- Mobil 375px: 13 sahifa, ekrandan chiqqan element **0**,
  `body.scrollWidth = 375 = viewport`
- Desktop 1280px: 13 sahifa, **0**, `body.scrollWidth = 1280`
- Topbar o'ng cheti 365 < 375
- Tab qatori 39px, suriladi
- AI tugmasi pasti 728 < menyu tepasi 739 — ustma-ust emas
- Balansda summa ustuni o'ng cheti 337 < 375 — hammasi ko'rinadi
- Desktopda Актив/Пассив ustunlari 486 = 486

Hisobga olinmagan (muammo emas): `.paper-bg` bezak SVG ichidagi
`<rect>` — SVG ning o'zi 375px va `overflow:hidden`; AI panelining
elementlari — u ataylab ekrandan tashqarida (right=750) turadi.

## Qoldi

- AI tugmasi surilganda kontent ustiga tushadi (odatiy FAB xatti-harakati)
- Boshqa akkauntlarda (mebel, non) qayta o'lchash — profil boshqa,
  jadval ustunlari boshqacha bo'lishi mumkin
