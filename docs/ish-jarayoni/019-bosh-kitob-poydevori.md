# 019 — BOSH KITOB POYDEVORI (bosqich B, 1-qadam)

**Sana:** 2026-08-18
**Holat:** ✅ dvigatel ishlaydi · ⏳ mavjud amallarga hali ULANMAGAN
**TZ:** [../06-YOL-XARITASI.md](../06-YOL-XARITASI.md) BOSQICH B

---

## Nima qilindi

Ikki yoqlama yozuv dvigateli: hisoblar rejasi (BHMS №21), provodka
qoidalari, provodka yozish, storno, davr yopish, aylanma qaydnoma,
foyda-zarar.

**Hali ulanmagan:** buyurtma topshirilganda GL avtomatik yozmaydi.
Bu keyingi qadam va u ehtiyot bilan qilinadi (quyida).

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `app/hisob/reja.json` | **yangi** — 28 schet, BHMS №21 |
| `app/hisob/qoidalar.json` | **yangi** — 10 hodisa → provodka shabloni |
| `app/hisob/xizmat.py` | **yangi**, 250 qator — dvigatel |
| `app/models.py` | 5 jadval: `Schet`, `Provodka`, `ProvodkaQatori`, `ProvodkaQoida`, `YopilganDavr` |
| `app/routers/hisob.py` | **yangi**, 220 qator — 13 endpoint |
| `app/main.py`, `app/platforma/tayyorlash.py` | GL yuklanishi |
| `tests/hisob_test.py` | **yangi**, 10 bo'lim |

---

## Qaror 1: reja va qoidalar — MA'LUMOT, kod emas

Foydalanuvchi so'ragan edi: «buxgalteriyaga doir narsalarni admin
panelda o'zgaradigan qilib qo'y». Bajarildi va bu loyihaning o'z
naqshiga to'liq mos:

```
app/profiles/*.json  → soha_profillar (baza)     ← allaqachon bor edi
app/hisob/reja.json  → schetlar (baza)           ← yangi
app/hisob/qoidalar.json → provodka_qoidalar      ← yangi
```

**Amaliy foyda (sinovda isbotlangan):** savdo korxonasi
«tayyor mahsulot» (2810) o'rniga «tovarlar» (2910) ishlatadi — buning
uchun **kod yozilmaydi**, qoidadagi schet almashtiriladi.

---

## Qaror 2: Дт—Кт shakli (jurnal uslubi emas)

Har provodka qatori: **debet schet + kredit schet + summa**.

Muqobil (G'arb jurnal uslubi): har qator alohida debet YOKI kredit,
keyin ularning yig'indisi tekshiriladi.

**Nega Дт—Кт tanlandi:**

1. **Balans STRUKTURA bilan kafolatlanadi.** Har qator o'zi
   tenglashadi, ya'ni «debet kreditga teng emas» holati umuman
   **paydo bo'lolmaydi**. Jurnal uslubida bu tekshiruvni kod
   qilishi kerak va u unutilishi mumkin.
2. **Mahalliy amaliyot.** Buxgalter «Дт 4010 Кт 9010» ni tanidi —
   1C ham shunday ko'rsatadi.

---

## Qaror 3: buxgalteriyaning qat'iy qoidalari — KODDA

Bular «yaxshi bo'lardi» emas, buxgalteriyaning o'zi talab qiladi:

| Qoida | Nega | Buzilsa nima bo'ladi |
|---|---|---|
| Provodka **o'chirilmaydi** — storno | audit izi | soliq tekshiruvida javob yo'q |
| **Yopilgan davrga** yozib bo'lmaydi | hisobot topshirilgan | baza topshirilgan hisobotga mos kelmaydi |
| Summa **manfiy emas** | oborot to'g'ri chiqsin | debet/kredit oboroti soxta bo'ladi |
| **Nol qator** yozilmaydi | hisobot tozaligi | qaydnoma bo'sh qatorlar bilan to'ladi |
| Debet ≠ kredit schet | ma'nosiz yozuv | saldo o'zgarmaydi, lekin oborot shishadi |

Hammasi `tests/hisob_test.py` da tekshiriladi.

### Storno JORIY sanaga yoziladi

Asl provodka sanasiga emas. Sabab: asl davr **yopilgan** bo'lishi
mumkin va o'tmishni o'zgartirish mumkin emas. Bu buxgalteriyaning
umumiy qoidasi.

---

## Sinov natijasi

`tests/hisob_test.py` — 10 bo'lim, serversiz:

```
1. 28 schet + 10 qoida yuklandi; qayta yuklashda takrorlanmadi
2. sotuv provodkasi: qarz 1 120 000 (QQS bilan), daromad 1 000 000
   (QQSSIZ), QQS majburiyati 120 000
3. QQS to'lovchi emas -> QQS qatori umuman tushmadi
4. to'lov qarzni kamaytirdi, kassa to'ldi
5. BALANS: jami debet == jami kredit
6. manfiy summa / bir xil schet / bo'sh provodka — rad etildi
7. STORNO: asl provodka joyida, yangisi qo'shildi, saldo tiklandi,
   ikki marta storno rad etildi
8. yopilgan davrga yozuv rad etildi, boshqa oyga ishladi
9. aylanma qaydnoma va foyda-zarar yig'ildi
10. mijoz qoidani o'zgartirdi (2810 → 2910) va u ISHLADI
```

**Jonli serverda:** 28 schet, qo'lda provodka (ustav kapitali
5 000 000), qaydnoma — aktiv 5 010 = passiv 8 710, balans teng.

**Regressiya:** himoya 155/155, 8 serversiz sinov, 22 profil to'liq
sikl, 22 soha hisob-kitobi — hammasi toza.

---

## ⚠️ Halol qayd: hisoblar rejasi tekshirilishi kerak

`reja.json` — **ishchi to'plam** (28 schet), tizim qo'llab-quvvatlaydigan
amallar uchun kerak bo'lganlari. To'liq BHMS rejasi ancha kengroq.

Kodlar (1010, 2010, 4010, 5010, 6010, 6410, 6710, 9010, 9110...)
keng tarqalgan va standart, lekin **men buxgalter emasman**. Fayl
ichida ham, API javobida ham ogohlantirish yozilgan:

> «Prodga chiqishdan oldin buxgalter tasdiqlashi SHART.»

Bu — [00-STRATEGIYA.md](../00-STRATEGIYA.md) §0.6 dagi qoidaning
davomi: tayyor bo'lmagan narsa va'da qilinmaydi.

---

## Keyingi qadam — EHTIYOT bilan

Endi GL ni mavjud amallarga ulash kerak (buyurtma topshirildi, to'lov,
xarid). Bu **eng xavfli qism**, shuning uchun tartib:

```
1. GL PARALLEL yoziladi — eski `services.py` tegilmaydi
2. `butunlik.py` ga tekshiruv: GL qarzi == eski usul qarzi
3. Bir muddat ikkalasi ishlaydi va taqqoslanadi
4. Faqat mos kelgach — hisobotlar GL ga o'tkaziladi
5. Eski hisoblash olib tashlanadi
```

**Nega shunday:** oltita xato aynan «har bo'lim o'z hisobini yozadi»
dan chiqqan edi. Agar GL ni birdan asosiy manba qilsak va unda xato
bo'lsa, mijozning moliyaviy manzarasi buziladi va buni **darhol
sezmaydi**.

---

## Qoldi (bosqich B ning qolgani)

1. **Ulash:** buyurtma/to'lov/xarid → avtomatik provodka
2. **`butunlik.py`:** GL == eski usul tekshiruvi
3. **Balans hisoboti** (aktiv/passiv) — hozir qaydnoma va foyda-zarar bor
4. **Frontend:** buxgalteriya bo'limi (hozir faqat API)
5. Boshlang'ich qoldiqlarni kiritish sehrgari
