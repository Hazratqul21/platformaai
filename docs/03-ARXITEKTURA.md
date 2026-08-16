# 3. ARXITEKTURA — bir sohadan ko'p vertikalga

> Maqsad: ERP, POS, CRM, WMS, LMS va buxgalteriya — hammasi bitta
> platformada, AI yig'ib beradigan qilib. Bu hujjat qanday qilib
> shunga yetishni ko'rsatadi.

---

## 3.1 Bugungi ikki o'lchov, kerakli uchinchisi

Hozir tizimda ikki o'lchov bor:

```
1) YADRO    — kod. Pul, ombor, mijoz, xodim. Sohani bilmaydi.
2) SOHA     — ma'lumot. Qaysi maydonlar, qanday retsept, bosqichlar.
```

Bu «non zavodimi yoki beton zavodi» savoliga javob beradi. Lekin
«ERP mi yoki CRM mi» degan savolga javob bermaydi.

**Kerak bo'lgan uchinchi o'lchov — QOBILIYAT (modul to'plami):**

```
3) QOBILIYAT — qaysi biznes imkoniyatlari yoqilgan
   ┌─────────────┬────────────────────────────────────┐
   │ savdo       │ mijoz, buyurtma, hisob-faktura     │
   │ ombor       │ qoldiq, partiya, inventarizatsiya  │
   │ ishlab_chiq │ retsept, sex, brak                 │
   │ chakana     │ POS, smena, chek, fiskal           │
   │ moliya      │ bosh kitob, schetlar, hisobotlar   │
   │ crm         │ voronka, vazifa, aloqa tarixi      │
   │ hr          │ xodim, davomat, oylik              │
   │ talim       │ kurs, dars, sertifikat (LMS)       │
   │ xizmat      │ ariza, ish buyrug'i, kafolat       │
   └─────────────┴────────────────────────────────────┘
```

Uch o'lchov birga:

| Mahsulot | Qobiliyatlar | Soha profili |
|---|---|---|
| «Odoo kabi ERP» | savdo + ombor + ishlab_chiq + moliya | non zavodi |
| «amoCRM kabi» | crm + savdo | ko'chmas mulk |
| «MoySklad kabi» | ombor + savdo + chakana | ulgurji savdo |
| «1C uchetka» | moliya + savdo + ombor | umumiy |
| «LMS» | talim + savdo | o'quv markazi |
| «POS» | chakana + ombor | do'kon |

**Muhimi:** bular alohida mahsulotlar EMAS — bitta platformaning har
xil yoqilgan holati. AI mijoz bilan gaplashib qaysi qobiliyat kerakligini
aniqlaydi va yoqadi.

### Amalga oshirish

`app/qobiliyatlar/*.json` — har qobiliyat ta'rifi: qaysi menyu
bo'limlari, qaysi endpointlar, qaysi rollar, qanday sozlamalar.
`SohaProfil` ga `qobiliyatlar: ["savdo","ombor"]` maydoni qo'shiladi.
Menyu va API shundan chiziladi — bugun forma profildan chizilgani kabi.

---

## 3.2 ENG KATTA ISH: Bosh kitob (General Ledger)

Bu hamma narsaning ostidagi poydevor. Busiz «1C uchetka», SAP yoki
Odoo darajasidagi moliya bo'lmaydi.

### Muammo

Hozir pul shunday oqadi:

```
buyurtma → to'lov → kassa yozuvi
   ↓
qarz = topshirilgan − to'langan   (qo'lda hisoblanadi)
```

Har hisobot alohida formula bilan yoziladi. Aynan shu sababdan
oldin **oltita xato** chiqdi (QQS qarzdan tushib qolishi, qarz yoshi
jadvalining jamiga to'g'ri kelmasligi va h.k.) — chunki bitta haqiqat
manbai yo'q edi.

### Yechim: ikki yoqlama yozuv

```
HAR AMAL → PROVODKA (bir necha qator, debet = kredit)

Mahsulot sotildi 1 120 000 (QQS 12%):
   D 4010 Xaridorlar qarzi      1 120 000
   K 9010 Sotuvdan tushum       1 000 000
   K 6410 QQS bo'yicha qarz       120 000

Mijoz to'ladi 500 000:
   D 5110 Hisob-raqam             500 000
   K 4010 Xaridorlar qarzi        500 000
```

Shundan keyin **hamma hisobot bitta manbadan** chiqadi: qarz, balans,
foyda-zarar, QQS deklaratsiyasi. Alohida formula yozilmaydi.

### Yangi jadvallar

| Jadval | Nima |
|---|---|
| `schetlar` | schetlar rejasi (BHMS №21 asosida, mijoz tahrirlashi mumkin) |
| `provodka` | operatsiya sarlavhasi: sana, hujjat, izoh |
| `provodka_qatori` | schet, debet, kredit, summa, analitika |
| `hisobot_davri` | yopilgan davrlar — yopilganidan keyin yozib bo'lmaydi |

### Qanday qo'shiladi (mavjud tizimni buzmasdan)

**Muhim:** bugungi mantiq ishlab turibdi va sinalgan. Uni bir kunda
almashtirmaymiz.

1. **GL qo'shiladi**, mavjud kod tegilmaydi
2. Har amal (buyurtma, to'lov, kirim) GL ga **ham** yozadi — hozirgi
   jadvallar ham qoladi
3. `butunlik.py` ga tekshiruv qo'shiladi: **GL dan hisoblangan qarz
   == hozirgi usul bilan hisoblangan qarz**
4. Bir necha oy ikkalasi parallel ishlaydi, farq chiqmasa —
   hisobotlar GL ga o'tkaziladi
5. Eski hisoblash olib tashlanadi

Bu — karton ustunlarini `attributes` ga ko'chirishda ishlatilgan
usulning aynan o'zi. U safar ishladi.

---

## 3.3 Ijarachilik (multi-tenancy)

Qabul qilingan qaror: **har mijozga alohida baza**.

```
platforma_boshqaruv   ← mijozlar ro'yxati, tariflar, ulanish ma'lumoti
  mijoz_001           ← alohida baza
  mijoz_002           ← alohida baza
```

**Nega alohida baza:**
- ma'lumot aралashib ketmaydi (ERP da bu halokat)
- bitta mijozni zaxiradan tiklash — boshqalariga ta'sir qilmaydi
- mijoz «ma'lumotimni bering» desa — bitta dump
- `tenant_id` unutilgan bitta so'rov butun sirni oshkor qiladi;
  alohida bazada bunday xato IMKONSIZ

**Narxi:** migratsiya har bazada yurishi kerak, ulanishlar hovuzi
kattaroq bo'ladi. Bu boshqariladigan narx.

**Qo'shimcha e'tibor:** `domain.py` dagi profil keshi hozir global.
Ijarachilikda u **mijoz bo'yicha** kalitlanishi shart — aks holda bir
mijozning profili boshqasiga ko'rinadi. (Kodda izoh sifatida allaqachon
yozib qo'yilgan.)

---

## 3.4 Hujjat dvigateli

Hozir akt/nakladnoy kodda qattiq yozilgan. Ko'p vertikal uchun
hujjat ham **shablon** bo'lishi kerak:

```
app/hujjatlar/*.json
  hisob_faktura.json    (EHF ga ham shu ta'rif bilan yuboriladi)
  yuk_xati.json
  akt.json
  chek.json             (POS)
  shartnoma.json
  sertifikat.json       (LMS)
```

Shablon: qaysi maydonlar, qanday joylashuv, qaysi rekvizitlar. Yangi
hujjat turi = yangi JSON.

---

## 3.5 Umumiy manzara

```
┌──────────────────────────────────────────────────────────┐
│  AI QATLAMI                                              │
│  agentlar · asboblar · GenUI · RAG · tasdiq              │
├──────────────────────────────────────────────────────────┤
│  QOBILIYATLAR (ma'lumot)                                 │
│  savdo · ombor · ishlab_chiq · chakana · moliya · crm    │
│  hr · talim · xizmat                                     │
├──────────────────────────────────────────────────────────┤
│  SOHA PROFILLARI (ma'lumot)                              │
│  22 ta tayyor + AI yaratganlari                          │
├──────────────────────────────────────────────────────────┤
│  YADRO (kod) — sohani ham, vertikalni ham bilmaydi       │
│  BOSH KITOB · ombor · mijoz · xodim · hujjat · rol       │
├──────────────────────────────────────────────────────────┤
│  INTEGRATSIYALAR                                         │
│  EHF · OFD/fiskal · Payme/Click/Uzum · ATS · Telegram    │
├──────────────────────────────────────────────────────────┤
│  IJARACHILIK — har mijozga alohida baza                  │
└──────────────────────────────────────────────────────────┘
```

**Qoida o'zgarmaydi:** yangi soha ham, yangi vertikal ham — **ma'lumot
qo'shish**, kod yozish emas. AI aynan shu ma'lumotni to'ldiradi.
