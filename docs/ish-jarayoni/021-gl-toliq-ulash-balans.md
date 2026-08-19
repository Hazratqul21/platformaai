# 021 — GL TO'LIQ ULANDI VA BALANS HISOBOTI

**Sana:** 2026-08-18
**Holat:** ✅ 6 hodisa ulandi, balans yig'ilyapti
**TZ:** [../06-YOL-XARITASI.md](../06-YOL-XARITASI.md) BOSQICH B, 5-qadam

---

## Nima qilindi

Qolgan amallar ham GL ga ulandi (xarid, yetkazuvchiga to'lov, sex
xarajati, xodim avansi) va **balans hisoboti** yozildi — buxgalteriyaning
asosiy hujjati.

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `app/routers/purchase.py` | xarid → `material_kirim` + `yetkazuvchiga_tolov` |
| `app/routers/hr.py` | xarajat → `sex_xarajati`, avans → `ish_haqi_tolandi` |
| `app/hisob/xizmat.py` | `balans()` — aktiv/passiv (+40 qator) |
| `app/routers/hisob.py` | `GET /api/hisob/balans` |
| `tests/hisob_test.py` | 11-bo'lim: to'liq sikl → balans yig'ildimi |

---

## Endi qaysi amallar GL ga tushadi

| Amal | Provodka |
|---|---|
| Buyurtma topshirildi | Дт4010 Кт9010 (daromad) · Дт4010 Кт6410 (QQS) · Дт9110 Кт2810 (tannarx) |
| Mijoz to'lovi | Дт5010 Кт4010 |
| Material xaridi | Дт1010 Кт6010 |
| Yetkazuvchiga to'lov | Дт6010 Кт5010 |
| Sex xarajati | Дт2010 Кт5010 |
| Xodim avansi | Дт6710 Кт5010 |

Hammasi **parallel** — eski hisob-kitob tegilmagan, xato bo'lsa amal
to'xtamaydi.

---

## Balans — foyda alohida hisoblanadi

Bu nozik joy. 9-sinf schetlari (daromad/xarajat) yil davomida
**yopilmaydi** — ular oborot to'playveradi. Agar ular balansga
qo'shilsa, aktiv va passiv **teng chiqmaydi**.

To'g'ri yo'l: 9-sinf balansdan chiqariladi, ularning natijasi
(daromad − xarajat) passivga **«joriy davr foydasi»** bo'lib tushadi.

```
AKTIV                        PASSIV
1010 material   5 000 000    6010 yetkazuvchi qarzi  3 000 000
5010 kassa      8 000 000    8710 ustav kapitali    10 000 000
                             8330 joriy davr foydasi        0
─────────────────────────    ────────────────────────────────
       13 000 000                    13 000 000    ✅ teng
```

Sinovda to'liq sikl tekshirildi (kapital → xarid → ishlab chiqarish →
sotuv → to'lov): **aktiv 13 600 000 == passiv 13 600 000**, foyda
3 000 000 (5 000 000 daromad − 2 000 000 tannarx).

---

## Jonli serverda tasdiqlandi

Haqiqiy endpointlar orqali:

```
ustav kapitali (qo'lda provodka)   Дт5010 Кт8710  10 000 000
xarid, qarzga, 2 mln to'landi      Дт1010 Кт6010   5 000 000
                                   Дт6010 Кт5010   2 000 000
sex xarajati                       Дт2010 Кт5010     300 000

BALANS: aktiv 13 000 000 == passiv 13 000 000  ✅
```

---

## Regressiya

| Sinov | Natija |
|---|---|
| himoya auditi | ✅ 156/156 |
| 9 serversiz to'plam | ✅ |
| 22 profil to'liq sikl | ✅ |
| 22 soha hisob-kitobi | ✅ |
| modul auditi (38 endpoint) | ✅ |
| `butunlik.py` | ✅ 19 tekshiruv |

---

## Yo'l-yo'lakay ko'rilgan holat

Xarajat yozilgach kassa **manfiy** bo'ldi (kapital kiritilmagan bazada).
`butunlik.py` ning «kassa saldosi manfiy emas» tekshiruvi buni
ko'rsatadi — bu **to'g'ri xatti-harakat**, nuqson emas: haqiqiy
korxonada kassada pul bo'lmasa xarajat qilib bo'lmaydi.

Boshlang'ich qoldiqlarni kiritish sehrgari kerakligi shundan
ko'rinadi (quyida, qoldi ro'yxatida).

---

## Qoldi (bosqich B ning oxiri)

1. **Frontend** — buxgalteriya bo'limi (13 endpoint tayyor, ekran yo'q)
2. **Boshlang'ich qoldiqlar sehrgari** — mavjud korxona tizimga
   o'tganda kassa/qarz/ombor qoldig'ini kiritish
3. **Parallel davr yakuni** — raqamlar mos kelgani isbotlangach
   hisobotlarni GL ga o'tkazish
4. Ish haqi **hisoblash** provodkasi (hozir faqat to'lov yoziladi)
5. Amortizatsiya, valyuta farqi — keyingi bosqichda
