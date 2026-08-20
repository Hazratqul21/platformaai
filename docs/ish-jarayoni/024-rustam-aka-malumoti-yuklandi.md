# 024 — RUSTAM AKANING MA'LUMOTI test.innasoft.uz GA YUKLANDI

**Sana:** 2026-08-19
**Holat:** ✅ ma'lumot ko'chirildi, butunlik toza, tashqaridan tasdiqlandi

---

## Nima qilindi

Rustam akaning JONLI tizimining **oxirgi** ma'lumoti sinov muhitiga
(test.innasoft.uz) read-only nusxa orqali ko'chirildi.

---

## Xavfsizlik — manba TEGILMADI

```
1. Jonli baza:  /var/www/tizim/gofra_erp.db  (Rustam akaning PRODI)
2. Nusxa:       Python `sqlite3.connect("...?mode=ro")` + `.backup()`
                — izchil nusxa, manbaga yozish IMKONSIZ
3. Isbot:       md5 nusxadan OLDIN va KEYIN bir xil:
                07dd4ea7921da01cc3e80adc6dc4241d
```

Ikki qatlamli himoya: `mode=ro` (SQLite yozishni rad etadi) +
`.backup()` (faqat o'qiydi). Nusxa `/tmp` ga olindi, manba diskda
tegilmadi.

---

## Ko'chirish

`tools/kochir.py` orqali (konteyner ichida, PostgreSQL ga):

| Jadval | Soni |
|---|---|
| mijozlar | 57 |
| yetkazib beruvchilar | 3 |
| materiallar | 21 |
| qog'oz partiyalari | 22 |
| buyurtmalar | 94 |
| to'lovlar | 97 |
| kassa yozuvlari | 447 |
| xodimlar | 25 |

**Tartib:** avval `--tekshir` (hech narsa yozmaydi, sanaydi), keyin
haqiqiy ko'chirish.

---

## Butunlik — toza

`tools/butunlik.py`: **14 tekshiruv, baza butun.**

> GL tekshiruvlari (5 ta) ATAYLAB o'tkazib yuborildi — Rustam akaning
> eski ma'lumotida provodka yo'q (`Provodka.count() == 0`), shuning
> uchun 19 emas, 14 chiqdi. Bu to'g'ri xatti-harakat: eski ma'lumotga
> GL keyinroq, boshlang'ich qoldiq sehrgari orqali qo'shiladi.

Bitta ogohlantirish: «zarariga sotilgan buyurtma yo'q» — bu ma'lumot
buzilgani emas, aksincha yaxshi (hamma buyurtma tannarxdan yuqori
sotilgan).

---

## Tashqaridan tasdiqlandi (https://test.innasoft.uz)

| Tekshiruv | Natija |
|---|---|
| Login (`admin`) | ✅ 200, Rahbar roli |
| Buxgalteriya (eng oxirgi kod) | ✅ 28 schet, BHMS №21 |
| Qarzdorlar | ✅ 31 mijoz, **983 mln so'm** jami qarz |
| Faol buyurtmalar | ✅ 55 ta |
| HTTP → HTTPS | ✅ 301 |
| health | ✅ 200 |

---

## Konteynerga qo'shimcha

`tools/` prod obrazida yo'q edi (ish vaqtida kerak emas). Ko'chirish
uchun `docker cp` bilan vaqtincha nusxalandi. Kelgusi deploy uchun
Dockerfile ga `COPY tools ./tools` qo'shildi — migratsiya har safar
qo'lda nusxalanmasin.

---

## Qoldi

1. **Wildcard DNS** `*.test.innasoft.uz` — hali tarqalmagan
   (Cloudflare). Tarqalgach ijarachilikni yoqib, alohida akkauntlarni
   sinash mumkin.
2. **Boshqa ma'lumotlar bilan sinash** — demo generatordan boshqa
   sohalar
3. **1C integratsiyasi** — ma'lumotni avtomatik tortib olish (keyingi
   katta ish)
