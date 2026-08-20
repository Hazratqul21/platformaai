# 032 — OBUNA VA AI SARFI EKRANI (ERP ichida)

**Sana:** 2026-08-20
**Holat:** ✅ ishlaydi — Sozlamalar → «Обуна ва AI сарфи»

---

## Muammo: ikki xil token

`/api/kabinet/*` **platforma tokenini** talab qiladi (ro'yxatdan
o'tish oqimi uchun, subdomensiz). Lekin akkaunt egasi ERP ga o'z
subdomenida **ERP paroli** bilan kirgan — undan yana ikkinchi login
so'rash noto'g'ri UX bo'lardi.

---

## Yechim: `/api/obuna/*` — ERP tokeni bilan

Yangi router (`kabinet.py` ichida, alohida `obuna_router`):

```
/api/kabinet/*   platforma tokeni   (registratsiya oqimi, subdomensiz)
/api/obuna/*     ERP tokeni         (ERP ichida, subdomendan akkaunt)
```

`_joriy_akkaunt()` — `tenancy.joriy()` dan (subdomendan aniqlangan)
akkauntni boshqaruv bazasidan oladi. Ya'ni **karton.innasoft.uz da
Rahbar bo'lib kirgan odam — o'sha akkauntning egasi**. Xavfsiz:
middleware subdomenni allaqachon tekshirgan, `require_roles("Rahbar")`
rolni tekshiradi.

Uch endpoint: `/mening`, `/ai-sarf`, `/ai-limit`.

---

## Ekran (Sozlamalar → Обуна ва AI сарфи)

- **KPI:** tarif · bu oy AI sarfi · ishlatilgan token
- **Akkaunt:** nomi, holati, manzili, obuna muddati
- **AI limiti:** progress chizig'i (yashil/sariq/qizil), limit qo'yish
- **Taqsimot:** yordamchilar bo'yicha, xodimlar bo'yicha

**Shaffoflik qoidasi bajarildi:** raqam yalang'och kelmaydi — «906
so'm» qayerdan kelgani (qaysi agent, qaysi xodim) ko'rsatiladi
([../07-TARQATISH.md](../07-TARQATISH.md) §7.6).

---

## Isbot (karton)

```
tarif: boshlangich · holat: sinov
AI: 9 so'rov · 27 543 token · 905.71 so'm
limit 1000 qo'yildi -> 90% · ogoh: True · to'xtatilgan: False
tokensiz -> 401
```

Limit mantiqi to'g'ri: 90% da ogohlantirish, to'xtatish faqat 100% da.
Obuna tugasa ham ERP ishlayveradi — ekranda ham shu yozilgan.

himoya_audit 162/162.

---

## Qoldi

- Tarifni o'zgartirish (to'lov tizimi bilan — integratsiya bosqichi)
- Obuna muddati tugashiga eslatma (email/telegram)
