# 031 — BOSHLANG'ICH QOLDIQ SEHRGARI

**Sana:** 2026-08-20
**Holat:** ✅ karton balansi to'ldi — aktiv 1.56 mlrd = passiv

---

## Muammo

Mavjud korxona (yoki ko'chirilgan ma'lumot) uchun balans BO'SH edi:
GL faqat YANGI amallardan boshlanadi, tarixiy holat provodkasiz.
Buxgalteriya bo'limi 0 ko'rsatardi.

---

## Yechim: ochilish provodkasi ERP holatidan

`gl.boshlangich_qoldiq_hisobla()` — hozirgi holatni sanaydi:

| Manba | Schet |
|---|---|
| Mijozlar qarzi (`client_balances_batch`) | Дт 4010 |
| Kassa (kirim − chiqim, so'm) | Дт 5010 |
| Ombor (material + qog'oz partiyalari qoldig'i) | Дт 1010 |
| Yetkazuvchi qarzi (olindi − berildi) | Кт 6010 |
| Mijoz avansi (manfiy balans) | Кт 6310 |

Har qator **8330** (taqsimlanmagan foyda) ga tenglashtiriladi —
Дт—Кт shakli tufayli aktiv == passiv **avtomat** chiqadi.

**Bir marta:** `boshlangich_qoldiq_bormi()` takror kiritishni rad
etadi (aks holda balans ikki barobar shishardi).

---

## Frontend sehrgari

Bo'sh balans holatidagi «Бошланғич қолдиқ киритиш» tugmasi →
modal: hozirgi raqamlar + qaysi schetga tushishi (Дт/Кт) ko'rsatiladi
→ tasdiq → provodka yoziladi va balans to'ladi.

---

## Natija (karton — Rustam ma'lumoti)

```
АКТИВ                                    ПАССИВ
1010 Ombor          532 897 067          6010 Yetkazuvchi     147 496 000
4010 Mijoz qarzi  1 024 803 234          6310 Mijoz avansi     22 592 604
                                         8330 Taqsimlanmagan 1 387 611 697
ЖАМИ              1 557 700 301          ЖАМИ               1 557 700 301
                          ✅ БАЛАНС ЙИҒИЛДИ (фарқ 0)
```

Raqamlar dashboard bilan mos (mijoz qarzi 1.02 mlrd, yetkazuvchi
147.5 mln).

---

## butunlik: ogohlantirish TO'G'RI chiqdi

```
⚠️ GL mijoz qarzi (4010) eski usulga mos — GL 1 024 803 234
   != eski usul 1 002 210 630 (farq 22 592 604)
```

Farq **aynan mijoz avansi**. Eski usul avansni qarzdan AYIRADI,
GL esa uni alohida **passivda** (6310) ko'rsatadi.

**Buxgalteriyada GL yo'li to'g'ri:** mijozning avansi bizning
majburiyatimiz (pul oldik, mol bermadik) — u qarzni kamaytirmaydi,
alohida turadi. Ogohlantirish ma'lumot buzilgani emas, ikki usul
farqini ko'rsatadi.

**19 tekshiruv toza.**

---

## Qoldi

- Kassa 0 chiqdi (KassaEntry so'm kirim/chiqim tengligi) — Rustam
  bazasidagi holat, tekshirish kerak bo'lsa alohida
