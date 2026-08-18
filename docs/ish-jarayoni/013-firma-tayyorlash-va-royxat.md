# 013 — FIRMA TAYYORLASH VA RO'YXATDAN O'TISH (A bosqichi, 3-qadam)

**Sana:** 2026-08-18
**Holat:** ✅ ishlaydi — ro'yxatdan o'tishdan ERP gacha to'liq oqim sinaldi
**TZ:** [../A-IJARACHILIK.md](../A-IJARACHILIK.md) §A.6

---

## Nima qilindi

Endi yangi firma **ro'yxatdan o'ta oladi** va tizim uning bazasini
o'zi tayyorlaydi: `CREATE DATABASE` → jadvallar → migratsiya →
22 profil → admin. Foydalanuvchi subdomeniga kirib ishlaydi.

Bu — A bosqichining «tirik» qismi: oldingi ikki qadam (boshqaruv
bazasi, ijarachilik yadrosi) endi bir-biriga ulandi.

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `app/platforma/tayyorlash.py` | **yangi**, 130 qator — baza tayyorlash zanjiri |
| `app/routers/royxat.py` | **yangi**, 140 qator — ro'yxat/holat/kir |
| `app/main.py` | lifespan ijarachilikda boshqaruv bazasini tayyorlaydi; middleware `/api/platforma/*` ni firmasiz o'tkazadi; router ulandi |
| `app/domain.py` | `profil()` kesh topilmasa firma bazasidan o'qiydi (xato tuzatildi) |
| `tools/migratsiya.py` | **yangi**, 120 qator — hamma bazada migratsiya |
| `tests/royxat_test.py` | **yangi**, 130 qator — to'liq oqim |
| `tests/himoya_audit.py` | 3 yangi ochiq endpoint sababi bilan |
| `sinov.sh` | 3 yangi serversiz sinov |

---

## Tayyorlash zanjiri — nega ajratilgan

`tayyorlash.py` uch bosqichga bo'lingan:

```
baza_yarat()      CREATE DATABASE (PostgreSQL) — SQLite da hech nima
sxema_tayyorla()  jadvallar + migratsiya
bazani_toldir()   22 profil + admin + kataloglar
```

**`sxema_tayyorla` ni `main.py` lifespan ham chaqiradi** — tayyorlash
mantiqi ikki joyda takrorlanmasin. Ilgari lifespan o'zi
`create_all` + `run_migrations` qilardi; endi bitta funksiya, biri
eskirmaydi.

### `seed()` dan farqi — MUHIM

Yangi mijozning bazasi **bo'sh** bo'ladi: admin + kataloglar + profil,
lekin **namuna ma'lumot yo'q**. `app/seed.py` esa dev bazasiga Rustam
akaning Excel ma'lumotini yuklaydi. Bu ikkisi aralashmasligi kerak edi
— shuning uchun `bazani_toldir` alohida, `seed()` ni chaqirmaydi.

Mijoz o'z ma'lumotini AI bilan yig'adi yoki qo'lda kiritadi.

---

## `CREATE DATABASE` nozikligi

Ikki narsa e'tibor talab qildi:

1. **`AUTOCOMMIT`** — `CREATE DATABASE` tranzaksiya ichida ishlamaydi.
   `isolation_level="AUTOCOMMIT"` bilan alohida ulanish.
2. **Qaysi bazaga ulanish** — yangi bazani yaratish uchun unga ulanib
   bo'lmaydi (u hali yo'q). Shuning uchun `MIJOZ_ADMIN_DB` (odatda
   `postgres`) ga ulanamiz.

Baza bor bo'lsa `False` qaytaradi — **idempotent**, qayta chaqirilsa
buzmaydi.

---

## Ro'yxatdan o'tish — baza yaratish FON vazifasi

```
POST /api/platforma/royxat
  → PlatformaUser + Firma yoziladi (darhol)
  → fon.add_task(baza tayyorlash)          ← bir necha soniya
  → javob qaytadi: {holat: "tayyorlanmoqda"}

GET /api/platforma/holat/{kod}
  → tayyorlanmoqda / tayyor / xato
```

**Nega fon:** `CREATE DATABASE` + migratsiya + profil yuklash bir necha
soniya. So'rov ichida qilinsa foydalanuvchi «osilib qolgan» ekranni
ko'radi — birinchi taassuroti buziladi.

**Xato bo'lsa `tayyorlik = "xato"`** va izoh yoziladi. Yarim tayyor
holat jimgina qolib ketmaydi — foydalanuvchi ko'radi, biz loglardan
bilamiz.

---

## Middleware istisnosi

`/api/platforma/*` firmasiz o'tadi. Sabab: ro'yxatdan o'tayotgan odam
hali subdomenga ega **emas** — u `app.innasoft.uz` da. Firma talab
qilinsa ro'yxatdan o'tishning o'zi imkonsiz bo'lardi (tovuq-tuxum).

---

## Topilgan va tuzatilgan XATO — `profil()` zaxiraga tushardi

Bu sinovsiz **jimgina** ketardi.

Ro'yxatda mebel tanlandi, lekin ERP `Karton` ko'rsatdi. Sabab:

```
profil() kesh topmasa → qayta_yukla(None) → db=None →
    bazadan o'qiy olmaydi → ZAXIRA_KALIT (karton) ga tushadi
```

Kesh mebel profilini boshqa kalit ostida saqlagan edi (fon vazifasi
firmani `ornat` qilmagani uchun `_yagona` ostida). ERP so'rovi
`inna_mebelsex` kalitini qidirdi, topmadi, **karton**ga tushdi.

**Tuzatildi:** `profil()` kesh topmasa **joriy firmaning bazasidan**
o'qiydi (`db.sessiya()`). Endi har firma o'z sohasini ko'radi.

> Bu ijarachilikning yashirin nuqsoni edi — 011-qadamda `_KESH` ni
> lug'atga o'tkazganimda kesh **miss** yo'lini to'liq o'ylamaganman.
> To'liq oqim sinovi buni ochdi. Kesh-hit yo'li to'g'ri edi,
> kesh-miss yo'li karton'ga tushardi.

---

## `tools/migratsiya.py --hammasi`

Boshqaruv bazasidan firmalar ro'yxatini olib, har biriga sxema
yangilash (+ ixtiyoriy butunlik). **Bittasi xato bersa qolganlari
davom etadi** — bitta firma tufayli hammasi to'xtamasin.

Ikki firma bazasida sinaldi: `2/2 muvaffaqiyatli`, butunlik toza.

---

## Sinov natijasi

`tests/royxat_test.py` — TestClient, ikki firma, bir jarayon:

```
1. ro'yxatdan o'tish 200, subdomen manzili to'g'ri
2. fon vazifasi bazani tayyorladi (tayyorlik=tayyor)
3. firma subdomenida ERP ga login 200, token olindi
   (parol ro'yxatda o'rnatilgani uchun majburiy almashtirish YO'Q)
4. tanlangan soha (mebel) faol bo'ldi
5. mebel tokeni non firmasida 401; non o'z sohasini ko'rdi
6. band subdomen rad etildi
7. yo'q firma so'rovi rad etildi
```

### Regressiya

| Sinov | Natija |
|---|---|
| `himoya_audit.py` | ✅ 128/128 |
| `genui_test.py` | ✅ |
| `platforma_test.py` | ✅ |
| `ijarachilik_test.py` | ✅ ikki mijoz aralashmadi |
| Yagona rejim (ijarachiliksiz) | ✅ health karton, login himoyasi ishlaydi |

Yagona rejimda `SEED_EMPTY` bilan standart parol majburiy almashtirish
hali ishlaydi — `profil()` o'zgarishi eski yo'lni buzmadi.

---

## Xavf va qo'riqlash

| Xavf | Qo'riqlash |
|---|---|
| `CREATE DATABASE` in'ektsiya | `kod_tekshir` + identifikator qo'shtirnoqda |
| Yarim tayyor firma | `tayyorlik="xato"` + izoh + log |
| Tayyorlash mantiqi ikki joyda eskiradi | `sxema_tayyorla` bitta funksiya |
| `profil()` karton'ga tushishi | firma bazasidan o'qiydi + oqim sinovi |
| Ro'yxatdan o'tish himoyasiz deb topilishi | audit ochiq ro'yxatiga sababi bilan |

---

## Qoldi

1. **`bot.py`** — hali bitta bazaga (ijarachilikda firma bo'yicha)
2. **Frontend** — ro'yxatdan o'tish ekrani (hozir faqat backend)
3. **Tasdiqlash kodi** — telefon/email tasdiqlash (hozir to'g'ridan-to'g'ri)
4. **Zaxira** — `zaxira.sh` har firma bazasini alohida olishi kerak
5. Admin paneli endpointlari (`/api/admin/*`)
