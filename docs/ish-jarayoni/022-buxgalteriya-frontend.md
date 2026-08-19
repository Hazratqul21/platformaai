# 022 — BUXGALTERIYA EKRANI VA ISHLAB CHIQARISH ZANJIRI

**Sana:** 2026-08-19
**Holat:** ✅ 7 tab ishlaydi, brauzerda sinaldi

---

## Nima qilindi

Buxgalteriya bo'limi: **balans, aylanma qaydnoma, foyda-zarar,
provodkalar, hisoblar rejasi, provodka qoidalari, davrlar**.

Va yo'l-yo'lakay **ishlab chiqarish zanjiri** GL ga ulandi — ekranda
manfiy aktiv ko'rinib qolgani uchun (quyida).

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `static/js/pages/hisob.js` | **yangi**, 310 qator — 7 tab |
| `static/js/core/router.js` | NAV + META + `enterApp` tuzatishi |
| `static/index.html` | skript tegi |
| `app/routers/orders.py` | ishlab chiqarish zanjiri GL ga |
| `app/hisob/ulash.py` | `material_ishlab_chiqarishga`, `mahsulot_tayyor` |
| `tests/gl_ulash_test.py` | sotuv provodkasini aniq tanlash |

---

## Ekranda HALOL ogohlantirish

Sahifaning eng boshida sariq karta:

> **Sinov bosqichi.** Bosh kitob mavjud hisob-kitob bilan **parallel**
> ishlaydi — raqamlar solishtirilmoqda. Rasmiy hisobot topshirish uchun
> buxgalter tasdig'i kerak.

Sabab: mijoz «to'liq buxgalteriya tayyor» deb o'ylab qolmasin
([../00-STRATEGIYA.md](../00-STRATEGIYA.md) §0.6). Bu lending
sahifasidagi «Ochiq gapiramiz» bo'limi bilan bir qoida.

Hisoblar rejasi tabida ham API dan kelgan ogohlantirish ko'rsatiladi:
«buxgalter tasdiqlashi shart».

---

## Ikkita nuqson brauzerda topildi

### 1. `META[p]` yo'q edi → lending ilova ustida qolib ketdi

Ekran ochilmadi, o'rniga **lending sahifasi** ilova ustida turdi.

Diagnostika zanjiri: `enterApp()` ichida xato → u `app.js` dagi
promise `.catch()` ga tushdi → `.catch()` esa `lendingBoshla()`
chaqiradi. Ya'ni **xato lending sifatida ko'rindi** va sababi
yashirindi.

Asl xato: `NAV` ga `hisob` qo'shilgan, lekin **`META` ga qo'shilmagan**
— `_renderPage` da `const [t,s] = META[p]` undefined ni destrukturizatsiya
qilishga urindi.

**Ikkita tuzatish:**
- `META.hisob` qo'shildi
- `enterApp()` endi lending'ni ham yashiradi (ilgari faqat login
  oynasini yashirardi)

> Saboq: yangi sahifa qo'shganda **NAV va META ikkalasiga** yozish
> kerak. Bu juftlik kodda ajratilgan va bittasini unutish oson.

### 2. Balansda MANFIY aktiv: `2810 = −75 000`

Ekranda ko'rinib qoldi. Sabab jiddiy: tayyor mahsulot **omborga
kirmasdan** sotilyapti.

To'g'ri zanjir uchta bo'g'indan iborat, ikkitasi yo'q edi:

| Bo'g'in | Provodka | Holat |
|---|---|---|
| Material ishlab chiqarishga | Дт2010 Кт1010 | ❌ yo'q edi |
| Tayyor mahsulot omborga | Дт2810 Кт2010 | ❌ yo'q edi |
| Sotilgan tannarx | Дт9110 Кт2810 | ✅ bor edi |

Ya'ni 2810 dan **chiqim** bor, **kirim** yo'q → manfiy.

**Ulandi:** `ishlab_chiqarish` ga o'tganda material qiymati (haqiqiy
FIFO summasi `retsept_yechish` dan), `tayyor` ga o'tganda
`unit_cost × qty`.

**Natija:** `2810 = 0` (kirdi va chiqdi), manfiy aktiv yo'q.

---

## `2010` da qoldiq qolishi — bu NORMAL

Sinovdan keyin `2010 = 425 000`. Bu xato emas:

```
Дт2010 Кт1010    75 000   material
Дт2010 Кт5010   500 000   sex xarajati
Дт2810 Кт2010   150 000   tayyor mahsulotga o'tdi
─────────────────────────
qoldiq          425 000   TUGALLANMAGAN ISHLAB CHIQARISH
```

Buxgalteriyada 2010 — «tugallanmagan ishlab chiqarish». Ustama
xarajatlar mahsulotga taqsimlanmagunicha shu yerda turadi. Haqiqiy
korxonada ham shunday.

> ⚠️ Ustama xarajatni mahsulotga **taqsimlash** (raspredeleniye) hali
> yo'q — u keyingi qadam. Hozircha xarajat 2010 da to'planadi.

---

## Sinov natijasi

### Brauzerda (haqiqiy ma'lumot: kapital → xarid → sotuv → xarajat)

```
✅ 7 tab ochiladi, birortasida xato yo'q
✅ Balans: aktiv 31 925 000 == passiv 31 925 000 «Баланс йиғилди»
✅ 2810 = 0 (manfiy emas)
✅ Provodkalar hujjat bilan: sex_xarajati, mijoz_tolovi,
   buyurtma_topshirildi — har birida Дт/Кт va summa
✅ Konsol toza
```

### Regressiya

| Sinov | Natija |
|---|---|
| himoya auditi | ✅ 156/156 |
| 9 serversiz to'plam | ✅ |
| 22 profil to'liq sikl | ✅ |
| 22 soha hisob-kitobi | ✅ |
| GL ulash (toza baza) | ✅ |
| `butunlik.py` | ✅ 19 tekshiruv |

---

## Qoldi

1. **Ustama xarajatni taqsimlash** — 2010 dan mahsulot tannarxiga
2. **Boshlang'ich qoldiqlar sehrgari** — mavjud korxona o'tganda
3. Schet qo'shish/tahrirlash ekrani (API bor, forma yo'q)
4. Provodka qoidasini ekrandan tahrirlash (API bor, forma yo'q)
5. Parallel davr yakuni
