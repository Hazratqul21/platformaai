# 027 — TO'LIQ MA'LUMOT KO'CHIRISH + ADMIN PANEL

**Sana:** 2026-08-20
**Holat:** ✅ karton to'liq ma'lumot; admin.innasoft.uz ishlaydi

---

## Muammo (foydalanuvchi topdi)

karton.innasoft.uz da hisobotlar to'liq emas, AI tushunmayapti.
Sabab: `kochir.py` faqat **8 jadval** ko'chirardi, **9 tasi** qolib
ketgan edi.

| Yetishmagan | Manba | Ta'siri |
|---|---|---|
| purchases | 109 | yetkazib beruvchi qarzi, xarid tarixi yo'q |
| purchase_payments | 137 | xarid to'lovlari yo'q |
| cash_entries | 319 | sex xarajat + xodim avansi yo'q |
| work_entries | 5 | sdelshina/oklad yo'q |
| stock_moves / material_moves | 91/109 | ombor harakati yo'q |
| payment_schedules | 2 | to'lov grafigi yo'q |
| **settings** | 9 | **rekvizit + brak % yo'q** → hujjat/tannarx noto'g'ri |

---

## Yechim: kochir.py to'liq ko'chiradi

`tools/kochir.py` kengaytirildi:
- **Xarita qo'shildi:** xodim (emp), partiya (lot) — FK bog'lash uchun
- **9 yangi jadval:** xaridlar, xarid_tolovlari, cash_entries,
  work_entries, stock_moves, material_moves, payment_schedules,
  settings
- **order_photos O'TKAZILDI** — rasm fayllari Rustam serverida qoladi,
  faqat yozuv ko'chirsa havolalar buziladi

**settings — UPSERT** (`db.merge`): rekvizit va brak foizi hisob-kitobga
ta'sir qiladi, ular ko'chmasa akt bo'sh rekvizit bilan chiqadi va
tannarx brak foizisiz noto'g'ri bo'ladi.

Qayta ko'chirish: inna_karton DROP → qayta tayyorlash (karton profil,
admin/1234) → to'liq kochir. Endi hamma jadval manba bilan bir xil.

---

## butunlik YANA REAL HOLATNI O'RGATDI

To'liq ko'chgach `butunlik.py` nomuvofiqlik topdi:
`ish haqi = miqdor × stavka — 5 ta`.

Tekshirdim: manbada `qty=0, rate=4000000, amount=4000000` — bular
**OKLAD** (belgilangan maosh), sdelshina EMAS. Butunlik tekshiruvi
faqat sdelshina uchun mo'ljallangan edi.

**Tuzatildi:** tekshiruv endi faqat `qty > 0` (sdelshina) uchun.
qty=0 = oklad, amount to'g'ridan-to'g'ri yoziladi.

> Bu migratsiya xatosi EMAS — Rustam ishchilari okladga ishlaydi.
> Loyihaning naqshi: real ma'lumot tekshiruvni o'rgatadi.

Natija: **14 tekshiruv toza** (GL provodka yo'qligi uchun skip).

---

## Isbot — hisobotlar endi ishlaydi

| Hisobot | Oldin | Endi |
|---|---|---|
| Xaridlar | 0 | 109 |
| Kassa harakatlari | 0 | 319 |
| Pul oqimi (30 kun) | to'liqsiz | −167 mln (xarid chiqimi bilan, realistik) |
| Rekvizit/sozlamalar | seed | brak_percent, margin, labor... (Rustam niki) |

---

## ADMIN PANEL — admin.innasoft.uz

Foydalanuvchi so'radi: admin.innasoft.uz da `admin` / `Xazrat_ali571`.

- `app/main.py`: `index()` — host `admin.*` bo'lsa `admin.html` beradi
- `static/admin.html`: o'z-o'zicha panel (glass uslub) — login
  (`/api/platforma/kir`), akkauntlar ro'yxati (holat, tarif, AI sarfi),
  muzlatish/ochish, platforma AI sarfi, audit jurnali
- Platforma admin login `admin@innasoft.uz` → **`admin`**, parol
  `Xazrat_ali571` (boshqaruv bazasida yangilandi)

Brauzerda sinaldi: 3 akkaunt (non/mebel/karton), audit, muzlatish
tugmalari — ishlaydi.

---

## ⚠️ Aniqlangan bo'shliq: AI sarfi 0 ko'rsatilyapti

Admin panelda hamma akkauntda AI sarfi **0** — garchi karton'da AI
sinalgan bo'lsa ham. Sabab: agent halqasi `ai_sarf` jadvaliga
YOZMAYAPTI (`llm.javob_ol` dan keyin sarf yozilishi kerak edi).

Bu «AI xarajati alohida» xususiyatining yozuv qismi — alohida
tuzatiladi. Hozir AI ISHLAYDI, lekin sarfi qayd etilmaydi.

---

## Regressiya

kochirish_test ✅ (manba tegilmadi, checksum), himoya_audit ✅,
royxat_test ✅.

---

## Qoldi

1. **AI sarfini `ai_sarf` ga yozish** — agent halqasida (muhim)
2. Wildcard cert avto-yangilanish (Cloudflare API)
3. 1C integratsiyasi
