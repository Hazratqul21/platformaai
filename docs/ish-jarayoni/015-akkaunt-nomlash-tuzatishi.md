# 015 — NOM TO'QNASHUVI TUZATILDI: firma → AKKAUNT

**Sana:** 2026-08-18
**Sabab:** foydalanuvchi to'g'ri e'tiroz bildirdi

---

## Muammo

Ijarachilik tenant'ini «Firma» deb atadim (009–014 qadamlar).
Lekin loyihada **`firm` allaqachon boshqa narsa**:

```
ERP ICHIDA (eski, tegilmaydi):
  Employee.firm, Client.firm, CashEntry.firm — bitta ERP ichida bir
  nechta kichik firma (yuridik shaxs/sex). setFirm(), firmBanner(),
  loadFirms() — ular orasida almashish.

MENING YANGI KODIM (xato nom):
  Firma = tenant = ro'yxatdan o'tgan korxona = alohida baza
```

Bitta so'z ikki xil narsani anglatardi. Bu abadiy chalkashlik
beradigan **nom to'qnashuvi** edi.

Foydalanuvchi aniq aytdi: *«men akkaunt dedim, qanday firma? bu bitta
firma bitta akkaunt bo'ldi degani»*.

---

## To'g'ri model

```
AKKAUNT (tenant)
  = bitta ro'yxatdan o'tish
  = bitta subdomen (mebelsex.innasoft.uz)
  = bitta baza
  = bitta korxona
  = bitta egasi (+ xodimlar)
    │
    └── ICHIDA: eski ko'p-firma xususiyati O'Z HOLICHA qoladi
        (bir korxona bir nechta yuridik shaxsni yuritishi mumkin)
```

Ya'ni ierarxiya: **Akkaunt > (ERP ichidagi) firm > ma'lumot**.

---

## O'zgartirilgan fayllar

Tenant «Firma» → «Akkaunt», faqat **mening yangi kodimda**:

| Fayl | Nima |
|---|---|
| `app/platforma/models.py` | `Firma`→`Akkaunt`, `firmalar`→`akkauntlar`, `firma_id`→`akkaunt_id` (5 jadvalda) |
| `app/platforma/xizmat.py` | `firma_yarat`→`akkaunt_yarat` va h.k. |
| `app/platforma/tayyorlash.py` | `firma_tayyorla`→`akkaunt_tayyorla` |
| `app/tenancy.py` | `Firma`→`Akkaunt`, `sorovdan_firma`→`sorovdan_akkaunt`, `_FIRMA_KESH`→`_AKKAUNT_KESH`, contextvar `joriy_firma`→`joriy_akkaunt` |
| `app/routers/royxat.py` | API: `firma_kod`→`akkaunt_kod`, `firma_nom`→`akkaunt_nom` |
| `app/main.py` | middleware, `X-Firma`→`X-Akkaunt` |
| `app/db.py`, `app/domain.py` | `tenancy.joriy`, `tenancy.kalit` chaqiruvlari |
| `static/js/core/lending.js` | API body, UI: «Firma nomi»→«Korxona nomi» |
| testlar, `docs/A-IJARACHILIK.md`, `docs/KOD-XARITASI.md` | |

**ERP ichidagi `firm` (hr.py da 9 ta, finance.py, models.py) —
TEGILMADI.** U boshqa tushuncha va to'g'ri ishlaydi.

---

## Nega blind replace xavfsiz edi

Mening yangi fayllarim ERP ichidagi `firm` (inglizcha, kichik,
'a' siz) ga **umuman murojaat qilmaydi** — ular tenant uchun faqat
«firma»/«Firma» ishlatardi. Shuning uchun shu 8 faylda to'liq
almashtirish boshqa narsani buzmadi.

Tekshirildi: `grep pm.Firma|tenancy.Firma|firma_id|...` — **nol
natija**. ERP `firm`: hr.py da 9 ta — **saqlanган**.

---

## Sinov — rename dan keyin

| Sinov | Natija |
|---|---|
| `platforma_test.py` | ✅ |
| `ijarachilik_test.py` | ✅ ikki mijoz aralashmadi |
| `royxat_test.py` | ✅ ro'yxat → ERP to'liq |
| `himoya_audit.py` | ✅ 128/128 |
| `genui_test.py` | ✅ |
| Jonli curl (ijarachilik) | ✅ ro'yxat → baza → login → «Tikuvchilik sexi» faol |

---

## Saboq

Yangi tushuncha kiritishdan oldin **loyihada shu so'z bormi**
tekshirish kerak edi. «Firma» — biznes uchun tabiiy so'z, shuning
uchun uni tenant uchun ishlatish oson tuyuldi, lekin ERP allaqachon
uni band qilgan edi.

Foydalanuvchi loyihani biladi va to'g'ri ushladi. Nom to'qnashuvi
kech tuzatilsa qimmatroq — hozir 8 faylda, keyin 50 faylда bo'lardi.
