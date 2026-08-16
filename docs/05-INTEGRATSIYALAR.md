# 5. INTEGRATSIYALAR

> To'lov, soliq, telefoniya, marketpleys. Har biri uchun: nima kerak,
> qancha vaqt oladi, qanday tartibda.

---

## 5.1 Umumiy qoida: integratsiya ham MA'LUMOT bo'lsin

Xato yo'l: har integratsiyaga alohida kod yozish. 10 ta integratsiya
= 10 ta alohida mantiq, har biri o'zicha xato beradi.

To'g'ri yo'l — **bitta integratsiya qatlami**:

```
app/integratsiya/
  asos.py          umumiy shartnoma: ulash, tekshirish, log, qayta urinish
  tolov/           payme.py · click.py · uzum.py
  soliq/           ehf.py · ofd.py
  aloqa/           telegram.py · sms.py · ats.py
  marketpleys/     uzum_market.py
```

Har biri bitta shartnomaga bo'ysunadi: `ulash()`, `tekshir()`,
`yubor()`, `holat()`. Shunda:

- xato bir joyda ushlanadi
- qayta urinish bir marta yoziladi
- **har chaqiruv logga tushadi** — pul tizimida bu majburiy
- yangi provayder qo'shish = bitta fayl

---

## 5.2 To'lov tizimlari (BIRINCHI NAVBATDA)

**Nega birinchi:** eng tez qiymat beradi, sertifikatlash kerak emas,
va mijoz uchun ko'rinadigan foyda («mijozim linkka bosib to'ladi»).

| Tizim | Model | Izoh |
|---|---|---|
| Payme | Merchant API | yaxshi hujjatlashtirilgan |
| Click | SHOP API + Merchant API | ikki xil ssenariy |
| Uzum | Merchant API | zamonaviy |

**Tezlashtiruvchi:** `paytechuz` kutubxonasi uchalasini qamraydi.
Noldan yozmaymiz.

### Ish oqimi

```
Buyurtma → «To'lov linki» tugmasi → link/QR
   ↓
Mijoz to'laydi → provayder webhook yuboradi
   ↓
Tizim to'lovni yozadi → qarz kamayadi → GL ga provodka
```

### Nozik joylar (bularni oldindan hisobga olish shart)

1. **Idempotentlik** — bitta webhook ikki marta kelishi mumkin.
   Har to'lovga provayder tranzaksiya id si bilan unikal indeks.
   Busiz mijozning to'lovi ikki marta yoziladi.
2. **Summani tekshirish** — webhook dagi summa buyurtmadagiga mos
   kelishi shart, aks holda soxta to'lov o'tadi.
3. **Imzo tekshiruvi** — har provayderning o'z usuli. Tekshirilmasa
   istalgan odam «to'ladim» deb yubora oladi.
4. **Test muhiti** — shartnoma bo'yicha test kalitlari olinadi,
   prodga chiqishdan oldin hamma ssenariy sinaladi.

**Vaqt:** 2–3 hafta (uchala provayder + sinov).

---

## 5.3 EHF — elektron hisob-faktura

**Nega ikkinchi:** hujjat yuridik kuchga ega bo'ladi, mijozning
buxgalteri qabul qiladi. Sertifikatlash emas — integratsiya.

**Kerak:** EHF operatori bilan shartnoma, API kalitlari, ERI (elektron
raqamli imzo).

```
Buyurtma topshirildi → EHF yaratiladi → operator → mijozning operatori
                                              ↓
                                        Soliq qo'mitasi
```

**Nozik joy:** EHF bekor qilish va tuzatish tartibi qat'iy. Yuborilgan
hisob-fakturani oddiy «tahrirlash» mumkin emas — bekor qilish yoki
tuzatuvchi hujjat kerak. Bu tizimda ham shunday bo'lishi shart, aks
holda soliq bilan muammo chiqadi.

**Vaqt:** 3–4 hafta.

---

## 5.4 Fiskal / OFD (POS uchun)

**Eng uzun yo'l.** [02-QONUNCHILIK.md](02-QONUNCHILIK.md) ga qarang:
dastur **virtual kassalar Davlat reyestridan** o'tishi shart.

```
BUGUN BOSHLANADI              KEYIN QILINADI
─────────────────             ──────────────────────
talablarni o'rganish          POS ekrani
ariza va hujjatlar            smena, chek, qaytarish
texnik shartlar               OFD ga ulanish
```

**Muhim:** ariza jarayoni kod yozishdan OLDIN boshlanadi. Aks holda
tayyor kod oylab kutib yotadi.

**Vaqt:** sertifikatlash 2–4 oy (baholash kerak), kod 3–4 hafta.

---

## 5.5 Telefoniya / call-center

**Nima kerak:**
- kirish qo'ng'irog'ida mijoz kartochkasi ochilishi (screen pop)
- suhbat yozuvi mijozga biriktirilishi
- qo'ng'iroqlar tarixi va statistika
- chiquvchi qo'ng'iroq (click-to-call)

**Qanday:** Asterisk/FreePBX — AMI/ARI orqali. Bu yo'l tanish
(`inna` loyihasida tajriba bor).

**AI qiymati:** suhbat yozuvini matnga o'girib, xulosani mijoz
kartochkasiga yozish. Bu — RAG uchun ham manba.

**Vaqt:** 3–4 hafta (asosiy qism), AI xulosasi keyinroq.

---

## 5.6 Marketpleys (Uzum Market)

Chakana va ulgurji savdo mijozlari uchun: tovar, qoldiq, buyurtma
sinxronizatsiyasi. `stlot` loyihasida Uzum bilan ishlash tajribasi
bor — undan foydalanish mumkin.

**Vaqt:** 2–3 hafta.

---

## 5.7 Tartib va sabab

```
1. TO'LOV        tez, sertifikatsiz, darhol ko'rinadigan foyda
2. EHF           hujjat yuridik kuchga ega bo'ladi
3. FISKAL        ariza BUGUN boshlanadi, kod keyinroq
4. TELEFONIYA    CRM vertikali uchun
5. MARKETPLEYS   savdo vertikali uchun
```

Har integratsiya `sinov.sh` ga o'z testi bilan qo'shiladi — pul
tizimida «ishlayapti shekilli» yaramaydi.
