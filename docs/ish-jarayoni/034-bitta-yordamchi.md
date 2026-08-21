# 034 — TO'RT AGENT → BITTA YORDAMCHI

**Sana:** 2026-08-20
**Holat:** ✅ ishlaydi — rol cheklovi kuchi o'zgarmadi
**So'rov:** «moliya yordamchisi, ombor yordamchisi… deb qilib tashlama —
bittasi bo'lishi kerak»

---

## Muammo

Ilgari 4 agent bor edi (sozlash / ombor / moliya / buyurtma) va
foydalanuvchi **qaysi biriga savol berishni o'zi tanlardi**.

Amalda noqulay:
- odam «qarzim qancha» deb so'ramoqchi, avval «Moliya yordamchisi» ni
  tanlashi kerak
- savol chegarani kesib o'tsa («omborda nima tugayapti va eng katta
  qarzdor kim?») — **ikkita agentga bo'lib so'rash** kerak edi

---

## Yechim: bitta yordamchi, ASBOBLAR rol bo'yicha filtrlanadi

**Eng muhim qaror — himoya qayerga ko'chdi:**

```
ILGARI:  cheklov AGENT darajasida
         «moliya agenti faqat Rahbar/Buxgalterga ochiq»

ENDI:    cheklov ASBOB darajasida
         sklad mudiri `qarzdorlar` asbobini UMUMAN KO'RMAYDI
```

Kuchi **o'zgarmadi** — aksincha aniqroq: model chaqira olmaydigan
asbob unga umuman berilmaydi.

`ASBOB_ROLLARI` — eski `AGENTLAR[*]["rollar"]` ning birlashmasi:

| Rol | Asbob | Qarzdorlar |
|---|---|---|
| Rahbar | 12 | ✅ |
| Buxgalter | 3 | ✅ |
| Sklad mudiri | 3 | ❌ |
| Menejer | 4 | ❌ |
| Sex boshlig'i | 4 | ❌ |

---

## Nega endi xavfsiz (ilgari nega bo'linган edi)

005-yozuvda sabab yozilgan: «40 asbob berilsa model qaysi birini
chaqirishni chalkashtiradi va aniqlik tushadi».

Bugun asboblar **jami 12 ta**. 12 — zamonaviy model uchun muammo
emas. Kodda yozib qo'yildi: **asbob soni 20 dan oshsa bu qaror
qayta ko'riladi**.

---

## Isbot

### 1. Chegarani kesib o'tuvchi savol (asosiy foyda)

```
«Omborda nima tugayapti va eng katta qarzdor kim?»  (Rahbar)
→ chaqirilgan asboblar: ombor_qoldigi, qarzdorlar, korsat
```

Bitta savol, ikki soha. Ilgari bu **imkonsiz** edi.

### 2. Rol izolyatsiyasi

```
Sklad mudiri: asbob_soni = 3
«Eng katta qarzdor kim?»
→ chaqirilgan asboblar: (yo'q)
→ javob: «menda mijozlar qarzdorligini ko'rish uchun tegishli asbob
   (ruxsat) mavjud emas»
```

Model uydirma qilmadi, ochiq aytdi.

---

## Orqaga moslik

- Eski agent kalitlari (`moliya`, `ombor`…) **qabul qilinadi** va
  hammasi bitta yordamchiga olib boradi — eski havolalar buzilmaydi
- `AGENTLAR` da eski 4 yozuv **saqlanadi**: ularning ko'rsatmasi
  bazada tahrirlangan bo'lishi mumkin (018-yozuv), yo'qotilmaydi
- `agent_royxati()` ro'yxat shaklini saqlaydi (frontend o'zgarmasin),
  ichida bitta yozuv

---

## Frontend

- AI sahifasidagi **agent tanlash `<select>` olib tashlandi** — o'rniga
  yordamchi nomi
- O'ng paneldagi tanlash: ro'yxat bitta bo'lsa **yashiriladi**
- Namuna savollar aralash: qarz, ombor, buyurtma, pul — bir to'plamda

---

## Regressiya

himoya 164/164, genui, korsatma (5 agent — 4 eski + yordamchi),
platforma, ijarachilik — toza.

`korsatma_test` yangilandi: 4 → 5 agent (kutilgan o'zgarish, chunki
eski ko'rsatmalar tahrir uchun saqlanadi).
