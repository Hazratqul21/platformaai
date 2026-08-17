# 6. YO'L XARITASI

> Tartib tasodifiy emas — har bosqich keyingisining poydevori.
> Vaqtlar taxminiy va bir kishi ishlashiga mo'ljallangan.

---

## Bosqichlarning bog'liqligi

```
A. IJARACHILIK ──┬──> B. BOSH KITOB ──┬──> D. CHAKANA/POS
                 │                    ├──> E. CRM
                 └──> C. AI KUCHAYTIRISH   └──> F. WMS · G. LMS
                          │
                          └──> RAG
```

**Nega shunday:**
- **A birinchi** — ikkinchi mijozni qabul qila olmasak, qolgani
  behuda. Va keyinroq qo'shish qimmatroq.
- **B ikkinchi** — hamma vertikal pulga borib taqaladi.
- **C parallel** — AI ishi boshqa qismlarni to'sib qo'ymaydi.

---

## BOSQICH A — Ijarachilik / SaaS (4–6 hafta)

**Nima:** har mijozga alohida baza, ustida boshqaruv paneli va
ro'yxatdan o'tish. Bu — [07-TARQATISH.md](07-TARQATISH.md) dagi
SaaS qarorining amaliy qismi.

**Qadamlar:**
1. `platforma_boshqaruv` bazasi: mijozlar, tariflar, ulanish
2. So'rovda mijozni aniqlash (subdomen: `mijoz.innasoft.uz`)
3. Ulanishlar hovuzi (mijoz bo'yicha, chegarali)
4. Migratsiya hamma bazada yurishi
5. **`domain.py` keshi mijoz bo'yicha kalitlanishi** ← unutilmasin
6. Mijoz yaratish/o'chirish, zaxira, tiklash
7. **Ro'yxatdan o'tish oqimi** — telefon/email → firma → AI sehrgari
8. **Tarif va obuna** — obuna tugasa yozish to'xtaydi, o'qish qoladi
9. **AI sarfi hisobi** — token, narx qotirilgan holda, limit va ogoh
10. **Platforma admin paneli** — mijozlar holati, xatolar, sarf

**Tayyor deb hisoblanadi:** ikki mijoz parallel ishlaydi, biri
ikkinchisining ma'lumotini KO'RA OLMAYDI —
`tests/ijarachilik.py` har endpointni chalkash token bilan sinaydi
va bittasi ham o'tmaydi.

**Xavf:** kesh va global holat. Hozir profil keshi global — bu
ijarachilikda sirni oshkor qiladi. Kodda ogohlantirish yozib qo'yilgan.

---

## BOSQICH B — Bosh kitob (5–7 hafta)

**Nima:** ikki yoqlama yozuv, schetlar rejasi, moliyaviy hisobotlar.

**Qadamlar:**
1. `schetlar` — BHMS №21 asosidagi reja, mijoz tahrirlashi mumkin
2. `provodka` + `provodka_qatori`
3. Har amal GL ga **ham** yozadi (eski mantiq qoladi)
4. `butunlik.py`: **GL qarzi == eski usul qarzi** tekshiruvi
5. Hisobotlar: balans, foyda-zarar, aylanma qaydnoma
6. Davrni yopish
7. Parallel ishlagach — hisobotlar GL ga o'tkaziladi
8. Eski hisoblash olib tashlanadi

**Tayyor deb hisoblanadi:** balans yig'iladi (aktiv == passiv), oltita
oldingi xato turidagi nomuvofiqlik `butunlik.py` da chiqmaydi.

**Xavf:** eng katta ish. Shoshilmaslik kerak — noto'g'ri buxgalteriya
noto'g'ri soliq degani.

---

## BOSQICH C — AI kuchaytirish (4–5 hafta, parallel)

**C1. RAG quvuri (2 hafta)**
1. `pgvector`, `hujjat` + `hujjat_bolagi` jadvallari
2. Bo'laklash va indekslash vositasi
3. Gibrid qidiruv (vektor + to'liq matn)
4. `bilim_qidir` asbobi, manba ko'rsatish majburiy
5. Boshlang'ich baza: BHMS, soliq qoidalari, tizim yo'riqnomasi

**C2. Agent rejalashtiruvi (2 hafta)**
1. Ko'p qadamli reja, ekranda ko'rinadigan
2. `mijoz_xotira` — doimiy xotira
3. Ko'proq tasdiqlanadigan amal (mijoz, buyurtma, kirim, narx)
4. Guruhli tasdiq

**C3. AI sinovi (1 hafta)**
1. `tests/ai_oltin_toplam.py` — 50+ savol
2. Asbob chaqiruvi va RAQAM tekshiruvi
3. `sinov.sh` ga qo'shish

**Tayyor deb hisoblanadi:** AI «mebel sexim bor» dan to ishlaydigan
tizimgacha olib boradi va oltin to'plamda ≥90% to'g'ri.

---

## BOSQICH D — Chakana / POS (4 hafta kod + sertifikat)

> **Ariza BUGUN boshlanadi** — sertifikat kodni kutmaydi.

**Parallel yo'l 1 — hujjat (bugundan):**
1. Virtual kassa reyestri talablarini olish
2. Texnik shartlarni o'rganish
3. Ariza topshirish

**Parallel yo'l 2 — kod (A va B dan keyin):**
1. `chakana` qobiliyati: smena ochish/yopish
2. POS ekrani: shtrix-kod, tez tugmalar, aralash to'lov
3. Chek (fiskal shakl)
4. OFD ga ulanish
5. Qaytarish, chegirma, sotuvchi smenasi

**Tayyor deb hisoblanadi:** reyestrda ro'yxatdan o'tgan va chek
Soliq ilovasida tekshiriladi.

---

## BOSQICH E — CRM (3 hafta)

1. Lid → aloqa → taklif → bitim voronkasi
2. Vazifa va eslatmalar
3. Aloqa tarixi (qo'ng'iroq, xat, uchrashuv)
4. Telefoniya (Asterisk/FreePBX): screen pop, yozuv
5. `sotuvchi` agenti

---

## BOSQICH F — WMS (2–3 hafta)

1. Ko'p ombor, yacheykalar (adreslar)
2. Terish (picking), joylashtirish
3. Partiya va yaroqlilik muddati
4. Terminal/skaner uchun ekran

---

## BOSQICH G — LMS (3–4 hafta)

1. Kurs, dars, guruh, jadval
2. Talaba, davomat, baho
3. To'lov (mavjud moliya bilan)
4. Sertifikat

---

## Integratsiyalar (bosqichlarga parallel)

| Nima | Qachon | Vaqt |
|---|---|---|
| Payme / Click / Uzum | A dan keyin | 2–3 hafta |
| EHF | B bilan birga | 3–4 hafta |
| Fiskal / OFD | D bilan | 3–4 hafta |
| Telefoniya | E bilan | 3–4 hafta |
| Marketpleys | F dan keyin | 2–3 hafta |

---

## Taxminiy umumiy vaqt

| Bosqich | Vaqt |
|---|---|
| A — Ijarachilik / SaaS | 4–6 hafta |
| B — Bosh kitob | 5–7 hafta |
| C — AI (parallel) | 4–5 hafta |
| D — POS | 4 hafta + sertifikat |
| E — CRM | 3 hafta |
| F — WMS | 2–3 hafta |
| G — LMS | 3–4 hafta |
| Integratsiyalar | ~12 hafta (parallel) |

**A+B+C = ~3 oy** — shundan keyin platforma ko'p mijozli, buxgalteriyasi
to'g'ri va AI konstruktori haqiqiy.
**Hammasi = ~8–10 oy** bir kishi ishlaganda.

---

## QAROR NUQTALARI — HAMMASI YOPILDI (2026-08-18)

| # | Savol | QAROR |
|---|---|---|
| 1 | A yoki B birinchi? | ✅ **A birinchi.** Ijarachiliksiz ikkinchi mijoz yo'q |
| 2 | POS qachon? | ✅ **Ariza bugun, kod A+B dan keyin.** Sertifikat kodni kutmaydi |
| 3 | Bulut yoki mijoz serverida? | ✅ **BULUT (SaaS).** On-premise 3–5 mijozdan keyin — [07](07-TARQATISH.md) |
| 4 | AI xarajatini kim to'laydi? | ✅ **Mijoz, alohida qator.** Kalit bizda, sarf serverda loglanadi |
| 5 | Qaysi vertikal keyingi? | ✅ **Mijoz tayyor bo'lgani.** Bugun — ishlab chiqarish + savdo |

Qonuniylik yo'ldan chiqmaydi: sertifikatlashdan o'tamiz, chetlab
o'tish yo'q ([02-QONUNCHILIK.md](02-QONUNCHILIK.md)).

---

## Frontend — parallel yo'l

[08-FRONTEND.md](08-FRONTEND.md) da to'liq. Qisqasi:

| Qachon | Nima |
|---|---|
| A bilan birga | build tizimi (Vite), CSS ajratish, SaaS ekranlari |
| B/C bilan parallel | ES modullar, Playwright testlari |
| Keyinroq | PWA / oflayn |
| Baholanadi | React/Vue — muammoni yechsagina |

Frontend **hozir qayta yozilmaydi.** Avval backend arxitekturasi.

---

## Sinov — haqiqiy ma'lumot bilan davom etadi

Rustam akaning ma'lumotidan olingan **read-only** nusxa oltita
jiddiy xatoni ochdi (QQS, qarz yoshi, pul oqimi) — hammasi
tuzatilgan va `butunlik.py` ularni qaytib chiqishdan qo'riqlaydi.

> ⚠️ **Jonli tizimga TEGILMAYDI.** Server `/var/www/tizim` va lokal
> `~/Desktop/rustam_aka/` — boshqa chatda boshqariladi. Bu yerda
> faqat nusxa ishlatiladi.

**Keyingi:** har bosqich yakunida yana shu nusxada sinaladi, so'ng
boshqa sohalardagi mijozlar ma'lumotida ham. Bitta soha ishlagani —
yigirma ikkitasi ishlaganini bildirmaydi.

---

## Keyingi qadam

Har bosqich boshlanishidan oldin alohida hujjat yoziladi (masalan
`docs/A-IJARACHILIK.md`) — u yerda aniq jadvallar, endpointlar,
migratsiya tartibi va sinov mezonlari bo'ladi.

Qarorlar yopildi, demak keyingi hujjat taxminga asoslanmaydi.

**Boshlanadigan ish:** `docs/A-IJARACHILIK.md` — aniq jadvallar,
endpointlar, migratsiya tartibi, `tests/ijarachilik.py` mezonlari.
