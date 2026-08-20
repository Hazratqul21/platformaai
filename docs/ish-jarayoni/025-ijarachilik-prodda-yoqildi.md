# 025 — IJARACHILIK PRODDA YOQILDI (ko'p akkaunt)

**Sana:** 2026-08-20
**Holat:** ✅ prodda ishlaydi — 2 akkaunt, izolyatsiya isbotlangan

---

## Nima qilindi

test.innasoft.uz yagona rejimdan **ko'p-akkaunt (SaaS)** rejimiga
o'tkazildi. Rustam akaning ma'lumoti alohida akkauntga ko'chirildi,
yangi sinov akkaunti ochildi — ikkalasi to'liq ajratilgan.

---

## Yakuniy manzil xaritasi

| Manzil | Nima | Kirish |
|---|---|---|
| **tizim.innasoft.uz** | Rustam akaning JONLI eski tizimi (port 8090) | TEGILMADI |
| **test.innasoft.uz** | ro'yxatdan o'tish / lending entry | akkaunt kerak emas |
| **karton.innasoft.uz** | Rustam ma'lumoti (platformada) | admin / **1234** |
| **mebel.innasoft.uz** | yangi sinov akkaunti (mebel sexi) | admin / MebelTest2026 |

Platforma admini (biz): **admin@innasoft.uz / InnaAdmin2026** →
`/api/admin/*` (hamma akkaunt, AI sarfi, muzlatish).

---

## Bosqichlar

1. **Kod:** band subdomenlar (test/tizim/archive/base/diydor —
   boshqa loyihalar, akkaunt emas)
2. **boshqaruv bazasi** yaratildi (PostgreSQL `CREATE DATABASE`)
3. **.env + compose:** `IJARACHILIK=1`, `ASOSIY_DOMEN=innasoft.uz`,
   `MIJOZ_DB_SHABLON`, `MIJOZ_ADMIN_DB=postgres`, `BOSHQARUV_DATABASE_URL`,
   `PLATFORMA_ADMIN_*`
4. **karton akkaunti** yaratildi → `inna_karton` bazasi (karton profil,
   admin/1234)
5. Rustam ma'lumoti `inna_karton` ga ko'chirildi (57 mijoz, 94 buyurtma,
   100 to'lov, 464 kassa)
6. **nginx:** `karton/mebel.innasoft.uz` bloki → 8100, Host uzatiladi
7. **SSL:** Let's Encrypt HTTP-01 (karton + mebel), 2026-11-18 gacha
8. **mebel akkaunti** ro'yxatdan o'tish orqali ochildi (fon vazifasi
   bazasini tayyorladi)

---

## Isbotlangan

| Tekshiruv | Natija |
|---|---|
| karton.innasoft.uz login + ma'lumot | ✅ 57 mijoz, 1.02 mlrd qarz |
| mebel.innasoft.uz — mebel sohasi, bo'sh | ✅ izolyatsiya |
| mebel tokeni karton'da | ✅ 401 (rad) |
| ikki akkaunt ikki soha | ✅ Karton / Mebel |
| AI (Gemini) karton'da | ✅ pul_holati + qarzdorlar o'qidi |
| **tizim.innasoft.uz (Rustam)** | ✅ **200, buzilmadi** |
| platforma admin paneli | ✅ 2 akkaunt ko'rindi |

---

## Nozik joylar

- **ERP admin paroli akkauntga xos.** karton = 1234 (qo'lda
  tayyorladim), mebel = ro'yxatdan o'tish paroli. Ro'yxatdan o'tishda
  parol egasi tanlaydi.
- **test.innasoft.uz da ERP endpoint 400** — bu to'g'ri: u ro'yxatdan
  o'tish entry, akkaunt emas. Kirish o'z subdomeningizda.
- **SSL faqat karton+mebel uchun** (SAN sertifikat). Yangi akkaunt
  qo'shilsa uning subdomeni uchun ham sertifikat kerak — hozircha
  qo'lda. To'liq SaaS uchun wildcard DNS-01 (`*.innasoft.uz`,
  Cloudflare) — keyingi qadam.

---

## Parallel ishlash (muhim)

Rustam akaga XABAR BERILMAGAN — u `tizim.innasoft.uz` da davom etadi.
`karton.innasoft.uz` — parallel nusxa (bugungi 16:14 holati). Yakuniy
o'tishda (xabar berilganda) yangi nusxa olib qayta ko'chiriladi.

Jonli manba HAR SAFAR read-only nusxa orqali olindi — md5 tekshirildi,
tegilmadi.

---

## Qoldi

1. **Wildcard SSL** (`*.innasoft.uz`) — cheksiz akkaunt HTTPS uchun
2. **Ro'yxatdan o'tish frontendida** subdomen redirect (login o'z
   subdomeniga yo'naltirsin)
3. Boshqa sohalar bilan sinash (non, tikuvchilik...)
4. 1C integratsiyasi — ma'lumotni avtomatik tortish
