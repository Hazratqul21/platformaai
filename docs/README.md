# INNASOFT PLATFORMA — HUJJATLAR

> Hamma reja shu yerda. Kod yozishdan oldin **shu sahifadan**
> boshlanadi. Oxirgi yangilanish: **2026-08-18**.

---

## Bir sahifada: biz nima qilyapmiz

Oddiy odam AI bilan gaplashib o'ziga tizim yasab olsin — ERP, POS,
CRM, WMS, LMS, buxgalteriya. Har sohada, dasturchisiz.

**Hammasi bitta web platformada (SaaS):** firma ro'yxatdan o'tadi →
o'z kabinetiga kiradi → AI bilan gaplashadi → tizimi yig'iladi.
Nechta mijoz bo'lsa ham — bitta kod, har biriga alohida baza.

---

## Qabul qilingan qarorlar — o'zgartirilmaydi

| # | Qaror | Sana |
|---|---|---|
| 1 | Hammasi qonuniy bo'ladi, sertifikatlashdan o'tamiz | 2026-08-15 |
| 2 | AI xarajati mijozdan **alohida** olinadi | 2026-08-15 |
| 3 | **Bitta web platforma (SaaS).** On-premise 3–5 mijozdan keyin | 2026-08-18 ⚠️ o'zgargan |
| 4 | Loyiha umumiy — Odoo/1C kabi, bitta sohaga xos emas | 2026-08-15 |
| 5 | A birinchi (ijarachilik), keyin B (Bosh kitob) | 2026-08-18 |
| 6 | POS arizasi bugundan, kodi A+B dan keyin | 2026-08-18 |
| 7 | Frontend hozir qayta yozilmaydi | 2026-08-18 |

3-qaror bilan eski «litsenziya kaliti + AI shlyuzi» rejasi bekor
qilindi — sababi [07-TARQATISH.md](07-TARQATISH.md) §7.2 da.

---

## Hujjatlar — o'qish tartibi

### Avval bularni (strategiya)

| # | Hujjat | Bir jumlada |
|---|---|---|
| 00 | [STRATEGIYA](00-STRATEGIYA.md) | nima uchun bizni tanlashadi, kim bilan raqobat, qayerdan boshlash, nima va'da qilmaymiz |
| 01 | [HOZIRGI HOLAT](01-HOZIRGI-HOLAT.md) | nima bor, nima yo'q — raqamlar bilan |
| 02 | [QONUNCHILIK](02-QONUNCHILIK.md) | EHF (522-qaror), fiskal kassa (943-qaror, Davlat reyestri), BHMS №21 |

### Keyin bularni (arxitektura)

| # | Hujjat | Bir jumlada |
|---|---|---|
| 03 | [ARXITEKTURA](03-ARXITEKTURA.md) | uchinchi o'q — QOBILIYAT, Bosh kitob rejasi, ijarachilik |
| 04 | [AI VA RAG](04-AI-VA-RAG.md) | **raqam — asbobdan, bilim — RAG dan**; reja, xotira, sinash |
| 05 | [INTEGRATSIYALAR](05-INTEGRATSIYALAR.md) | Payme/Click/Uzum → EHF → fiskal → telefoniya → marketpleys |
| 07 | [TARQATISH](07-TARQATISH.md) | SaaS qarori, ma'lumot ajratish, AI sarfi, tarif, on-premise arxivi |
| 08 | [FRONTEND](08-FRONTEND.md) | hozirgi holat, F1–F6 modernizatsiya, SaaS ekranlari |

### Ish hujjatlari (kod yozishda ochiladi)

| Hujjat | Bir jumlada |
|---|---|
| [06 — YO'L XARITASI](06-YOL-XARITASI.md) | A→G bosqichlar, vaqtlar, **yopilgan qarorlar** |
| [KOD XARITASI](KOD-XARITASI.md) | **har faylda nima bor, u nimaga bog'liq, tegilganda nima buziladi** |
| [A — IJARACHILIK](A-IJARACHILIK.md) | A bosqichining aniq jadvallari, endpointlari, sinov mezonlari |

---

## Yo'l xaritasi — qisqacha

```
A. IJARACHILIK / SaaS ──┬──> B. BOSH KITOB ──┬──> D. POS
   4–6 hafta            │      5–7 hafta     ├──> E. CRM
                        │                    └──> F. WMS · G. LMS
                        └──> C. AI + RAG
                                4–5 hafta (parallel)
```

**A+B+C ≈ 3 oy** — shundan keyin platforma ko'p mijozli,
buxgalteriyasi to'g'ri va AI konstruktori haqiqiy.
**Hammasi ≈ 8–10 oy** bir kishi ishlaganda.

---

## Hozirgi holat — 2026-08-18

**Ishlaydi va sinalgan:**
22 soha profili · buyurtma to'liq sikli · FIFO xomashyo · tannarx
(retsept va formula) · QQS (stavka qotirilgan) · mijoz qarzi va
qarz yoshi · pul oqimi prognozi · kassa (ko'p firma/valyuta) ·
kadrlar (sdelshina, ish haqi) · AI (4 agent, 12 asbob, GenUI) ·
Telegram bot · PDF/Excel/DOCX eksport · konstruktor · himoya

**Yo'q:** ijarachilik · Bosh kitob · RAG · agent xotirasi · online
to'lov · EHF · POS · CRM voronkasi · WMS · LMS · telefoniya

**O'lchamlar:** 17 151 qator · 33 jadval · 125 endpoint ·
8 sinov to'plami

---

## Kod yozish qayerdan boshlanadi

[KOD-XARITASI.md](KOD-XARITASI.md) §9 va §12 bo'yicha, aynan shu
tartibda:

```
1. app/db.py        get_db firma bo'yicha, Engine hovuzi + LRU
2. app/auth.py      token boshqaruv bazasida, get_user firmani qaytaradi
3. app/domain.py    _KESH → contextvars (26 ta profil() chaqiruvi)
   + tests/ijarachilik.py — shusiz «tayyor» deyilmaydi
```

**17 151 qatordan jiddiy o'zgaradigani ~1 000 qator.** 125 endpoint,
`services.py` va `genui.py` **tegilmaydi** — `Depends(get_db)` naqshi
tufayli.

---

## O'zgarmaydigan qoidalar

1. **Raqam — asbobdan, bilim — RAG dan.** ERP bazasi hech qachon
   vektorlashtirilmaydi.
2. **AI bazaga o'zi yozmaydi.** Taklif qiladi → odam tugma bosadi →
   auditga **odam** yoziladi.
3. **Ma'lumot garovga olinmaydi.** Obuna tugasa yozish to'xtaydi,
   o'qish va eksport ochiq qoladi.
4. **AI limiti tugasa AI to'xtaydi, ERP ishlayveradi.**
5. **Migratsiya faqat qo'shadi.** Ustun o'chirish alohida buyruq.
6. **Sinalmagan zaxira — zaxira emas.** Oyda bir marta tiklab
   `butunlik.py`.
7. **Tayyor bo'lmagan narsa va'da qilinmaydi**
   ([00-STRATEGIYA.md](00-STRATEGIYA.md) §0.6).

---

## ⚠️ Tegilmaydigan joylar

> Rustam akaning **jonli** tizimi: server `/var/www/tizim` va lokal
> `~/Desktop/rustam_aka/`. Ular boshqa chatda boshqariladi.
> Bu loyihada faqat **read-only nusxa** ishlatiladi.

Nusxa oltita jiddiy xatoni ochgan edi (QQS qarzdan tushib qolgan,
qarz yoshi status nomiga bog'langan, avans hisobga olinmagan, pul
oqimida noto'g'ri sana, yetkazib beruvchi qarzi chiqimda yo'q,
`Decimal × float`). Hammasi tuzatilgan, `tools/butunlik.py`
qaytishidan qo'riqlaydi.
