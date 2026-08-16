# 2. QONUNCHILIK VA MAJBURIY TALABLAR

> **Bu bo'lim rejaning tartibini belgilaydi.** Texnik qiyinchilik emas,
> qonuniy to'siqlar qaysi ishni qachon qilishni aytadi. Sertifikatlash
> oylar oladi, kod esa haftalar.

---

## 2.1 Elektron hisob-faktura (EHF)

**Holat:** 2020-yil 1-yanvardan **majburiy**.
**Asos:** Vazirlar Mahkamasining 25.06.2019 yildagi **522-son** qarori.

Ishlash zanjiri: korxona → EHF operatori → rouming → Soliq qo'mitasi
axborot tizimi. Operatorlar orasida rouming bor, ya'ni har xil
operatordagi ikki korxona bir-biriga hujjat yubora oladi.

**Biz uchun ma'nosi:**

- Hozirgi akt/nakladnoy PDF lari **yuridik kuchga ega emas** — ular
  faqat ichki hujjat. Mijoz ularni buxgalteriyasiga qo'ya olmaydi.
- To'liq qiymatli bo'lish uchun EHF operatoriga ulanish shart.
- Bu **integratsiya**, sertifikatlash emas — nisbatan tez.

**Manba:** [lex.uz 522-son](https://lex.uz/uz/docs/-4386769) ·
[buxgalter.uz](https://buxgalter.uz/oz/publish/doc/text156943_agar_siz_elektron_hisobvaraq-fakturalarga_utishni_hohlasangiz_nima_qilish_lozim)

---

## 2.2 Onlayn kassa va virtual kassa (POS uchun ENG MUHIM)

**Asos:** Vazirlar Mahkamasining 23.11.2019 yildagi **943-son** qarori.

Zanjir: kassa amali → fiskal chek → **OFD** (fiskal ma'lumot
operatori) → Soliq qo'mitasi. Real vaqtda. Mijoz chekni «Soliq»
ilovasida tekshira oladi.

### ENG MUHIM QOIDA

> Dastur **virtual kassalar Davlat reyestrida ro'yxatdan o'tgan**
> bo'lishi shart. Reyestrda yo'q dasturni O'zbekistonda ishlatib
> bo'lmaydi.

R-Keeper, JOWi, iiko kabi dasturlar aynan shu yo'ldan o'tgan.

### 2026-yil 1-apreldan qo'shimcha talablar

- davlat katalogi bo'yicha sotuvni cheklash
- dori-darmonni retsept QR kodi skanerlangandan keyingina berish
- muddati o'tgan tovarga chek bermaslik
- ijtimoiy karta to'lovlarini to'g'ri qayta ishlash

**Biz uchun ma'nosi:**

| | |
|---|---|
| POS qilish | texnik jihatdan mumkin |
| POS ni QONUNIY sotish | **reyestrdan o'tmasdan mumkin emas** |
| Muddat | sertifikatlash oylar oladi, oldindan boshlash kerak |

> **Strategik xulosa:** POS ni birinchi bo'lib qilmaymiz. Avval
> reyestr talablarini o'rganib, ariza jarayonini **parallel**
> boshlaymiz, kod esa keyinroq. Aks holda tayyor kod oylab kutib
> yotadi.

**Manba:** [lex.uz 943-son](https://lex.uz/acts/-4603329) ·
[norma.uz](https://www.norma.uz/oz/qonunchilikda_yangi/onlayn-nkm_va_virtual_kassa_qanday_urnatiladi_va_ruyhatdan_utkaziladi) ·
[paloma365 — 2026 talablari](https://paloma365.uz/blog/guides/onlajn-kassa-uzbekistan)

---

## 2.3 Buxgalteriya standartlari (BHMS)

- **BHMS** — Buxgalteriya Hisobi Milliy Standartlari
- **Schetlar rejasi** — BHMS №21, 2002-yildan amalda
- **Ikki yoqlama yozuv MAJBURIY**: har amal bir schet debetiga va
  boshqasining kreditiga bir vaqtda yoziladi

**Biz uchun ma'nosi:** hozirgi sodda pul modeli bilan buxgalteriya
hisoboti chiqmaydi. «1C uchetka» darajasi uchun **Bosh kitob (General
Ledger)** kerak. Bu eng katta arxitektura ishi —
[03-ARXITEKTURA.md](03-ARXITEKTURA.md) da batafsil.

---

## 2.4 To'lov tizimlari

| Tizim | Integratsiya turi |
|---|---|
| **Payme** | Merchant API — hujjatlashtirilgan, tayyor kutubxonalar ko'p |
| **Click** | ikki model: SHOP API (mijoz ilovadan to'laydi) va Merchant API (sayt ichida) |
| **Uzum** | zamonaviy API |

Uchalasini qamraydigan Python kutubxonasi bor: **`paytechuz`** (PyPI).
Bu ishni sezilarli tezlashtiradi — noldan yozish shart emas.

**Kerak bo'ladi:** har provayder bilan shartnoma, test muhiti kalitlari
(merchant ID + secret key).

**Manba:** [paytechuz (PyPI)](https://pypi.org/project/paytechuz/) ·
[GitHub PayTechUz](https://github.com/paytechuz/paytechuz) ·
[integratsiya misoli](https://github.com/bek-shoyatbek/payme-uzum-click-integration-example)

---

## 2.5 Xulosa: qonuniy to'siqlar tartibi

```
TEZ (haftalar)              SEKIN (oylar)
──────────────────          ─────────────────────────
to'lov tizimlari            virtual kassa reyestri
EHF operatori               (POS uchun majburiy)
```

**Reja shu asosda tuziladi:** sertifikatlash talab qiladigan ish
birinchi bo'lib BOSHLANADI (ariza, hujjat), lekin kod tartibida
KEYINROQ turadi. Tez integratsiyalar esa mahsulotga darhol qiymat
qo'shadi.
