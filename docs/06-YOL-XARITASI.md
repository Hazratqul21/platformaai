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

## BOSQICH A — Ijarachilik (3–4 hafta)

**Nima:** har mijozga alohida baza, ustida boshqaruv paneli.

**Qadamlar:**
1. `platforma_boshqaruv` bazasi: mijozlar, tariflar, ulanish
2. So'rovda mijozni aniqlash (subdomen: `mijoz.innasoft.uz`)
3. Ulanishlar hovuzi (mijoz bo'yicha)
4. Migratsiya hamma bazada yurishi
5. **`domain.py` keshi mijoz bo'yicha kalitlanishi** ← unutilmasin
6. Mijoz yaratish/o'chirish, zaxira, tiklash

**Tayyor deb hisoblanadi:** ikki mijoz parallel ishlaydi, biri
ikkinchisining ma'lumotini KO'RA OLMAYDI (test bilan isbotlangan).

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
| A — Ijarachilik | 3–4 hafta |
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

## QAROR NUQTALARI — bularni siz hal qilasiz

| # | Savol | Nima uchun muhim |
|---|---|---|
| 1 | **A yoki B birinchi?** | Ko'p mijoz muhimmi yoki buxgalteriya chuqurligi? Men A ni tavsiya qilaman — keyinroq qo'shish qimmatroq |
| 2 | **POS qachon?** | Eng katta bozor, lekin sertifikat kerak. Ariza bugun boshlanadimi? |
| 3 | **Bulut yoki mijoz serverida?** | Bulut = tez o'sish; mijoz serveri = ma'lumot ularniki. Ikkalasi ham mumkin, lekin tanlash arxitekturaga ta'sir qiladi |
| 4 | **AI xarajatini kim to'laydi?** | Biz (tarifga kiritamiz) yoki mijoz o'z kalitini qo'yadimi? Hozir ikkinchisi |
| 5 | **Qaysi vertikal keyingi?** | Sizda qaysi biriga mijoz tayyor? U birinchi bo'lsin |

---

## Keyingi qadam

Har bosqich boshlanishidan oldin alohida hujjat yoziladi (masalan
`docs/A-IJARACHILIK.md`) — u yerda aniq jadvallar, endpointlar,
migratsiya tartibi va sinov mezonlari bo'ladi.

**Hozir kerak:** yuqoridagi 5 ta qaror. Ularsiz keyingi hujjat
taxminга asoslanadi.
