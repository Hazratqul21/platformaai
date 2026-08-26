# 039 — RUSTAM AKA: YAKUNIY O'TISH (tayyorgarlik)

**Sana:** 2026-08-26
**Holat:** ⏸ TO'XTATILGAN — vositalar tayyor, o'tish qilinmadi
**Davom ettirish uchun:** shu hujjatning «Qolgan qadamlar» bo'limi

---

## Maqsad

`tizim.innasoft.uz` dagi eski TIZIM ERP (Rustam aka, JONLI) platformaga
ko'chiriladi. Ikkita qattiq shart:

1. **Bitta nuqta ham yo'qolmasin** — bu prod, mijozning ishlab turgan
   biznesi.
2. **Odam uchun bu «yangilanish» bo'lsin** — qayta login qilmasin,
   parol so'ralmasin, manzil o'zgarmasin.

---

## Serverdagi holat (2026-08-26 da aniqlangan)

| Nima | Qayerda |
|---|---|
| Server | `138.249.248.172` (hostname `diydor`), foydalanuvchi `xazratabduraufov` |
| Eski tizim | `/var/www/tizim` · `tizim.service` (systemd, Docker EMAS) · port **8090** · SQLite `/var/www/tizim/gofra_erp.db` |
| Platforma | `/var/www/innasoft-platforma` · `innasoft-app` (port **8100**), `innasoft-db` (5441) |
| nginx | `tizim.innasoft.uz` → 8090 · `*.innasoft.uz` → 8100 (wildcard SSL bilan) |

> ⚠️ **Prodda git yo'q** — `/var/www/innasoft-platforma` oddiy papka.
> `git pull` ishlamaydi, deploy fayl ko'chirish bilan.

> ⚠️ **Compose farqi:** proddagi `docker-compose.yml` da ijarachilik
> o'zgaruvchilari BOR (50–57-qatorlar), repodagida **YO'Q**. Repodan
> fayl ko'chirilsa ijarachilik jimgina o'chadi va hamma akkaunt
> qulaydi. **Deploydan oldin repo compose'iga o'sha 7 qator qo'shilsin.**

---

## Manba ma'lumoti (jonli, 2026-08-26 00:32)

```
clients 61 · orders 109 · payments 108 · kassa_entries 512
purchases 109 · purchase_payments 137 · cash_entries 359
employees 30 · materials 21 · raw_lots 27 · stock_moves 96
material_moves 109 · work_entries 5 · payment_schedules 2 · settings 9
audit_logs 1216 · order_photos 77 (+97 fayl, 7 MB) · users 1 · auth_tokens 25
categories 9 · formulas 6 · services 8 · positions 8 · units 7
```

`inna_karton` (20-avgust nusxasi) **eskirgan**: 57/94/100. Unga
tegilmaydi — orqaga qaytish nuqtasi bo'lib tursin.

---

## Qilingan ish

### 1. `tools/kochir.py` to'ldirildi — 15 bo'lim → 20

Ilgari **9 jadval umuman ko'chmasdi**. Qo'shildi:

| Bo'lim | Jadval | Nega muhim |
|---|---|---|
| 16 | units, positions, categories | kataloglar (nomi bo'yicha upsert) |
| 17 | services, formulas | **tannarx hisobi** shu formulalarga bog'liq |
| 18 | order_photos | buyurtma rasmlari (fayllar alohida ko'chadi) |
| 19 | audit_logs | «kim nima qildi» — 1216 yozuv |
| 20 | users + auth_tokens | `--kirish` bayrog'i bilan |

**`--kirish` bayrog'i.** Parol xeshi (bcrypt) o'zgarmasdan ko'chadi,
muddati o'tmagan sessiyalar saqlanadi, `parol_almashtirilsin` o'chiriladi.
Parallel nusxaga BERILMAYDI — bitta sessiya ikki bazada yashab qolsa,
odam qaysi nusxaga yozayotganini bilmaydi.

**Mashqda ushlangan nuqson:** `db.merge()` birlamchi kalit (`id`)
bo'yicha ishlaydi, `formulas.name` esa unique — seed yozgan formula
ustiga kelganda `UNIQUE constraint failed` bilan BUTUN ko'chirish
yiqilardi. Nomi bo'yicha upsert ga o'zgartirildi.

### 2. Yangi `tools/solishtir.py` — yo'qolmaganini ISBOTLAYDI

`butunlik.py` bazaning ichki ziddiyatini qaraydi va **yarim ko'chgan
bazani ham «butun» deb ko'rsatadi** (61 mijozdan 40 tasi ko'chsa, o'sha
40 tasi o'zaro mos bo'ladi). `solishtir.py` boshqa savolga javob
beradi: manbada nima bor edi, platformaga nima yetib bordi.

- har jadval: manba ⟷ platforma soni
- pul jamlari: buyurtma, to'lov, xarid, kassa — tiyinigacha
- yo'qotish bo'lsa `exit 1` — o'tish skripti shu yerda to'xtaydi

Lokal mashqda ikkalasi ham ishladi, pul jamlari aynan teng chiqdi.

### 3. Zaxira nusxa olindi (server)

`/tmp/tizim_nusxa.db` — `mode=ro` + `.backup()`. Manba md5 nusxadan
oldin ham, keyin ham bir xil: `0a09958647e41fdc620cbc369f3ae987`.

> Nusxaning md5 i manbanikidan farq qiladi — bu normal, `.backup()`
> izchil nusxa yasaydi, bayt-baytga aynan emas. Tenglik **qatorlar
> soni bilan** isbotlanadi.

---

## O'tish rejasi (qolgan qadamlar)

### Qaror: akkaunt kodi `tizim` bo'lsin

Manzil o'zgarmasa brauzerdagi token joyida qoladi (`localStorage`
domenga bog'langan) — odam qayta kirmaydi. Shuning uchun `karton`
emas, **yangi `tizim` akkaunti**.

Kodda: `tizim` band subdomen ro'yxatidan chiqariladi
(`app/tenancy.py` `BAND_SUBDOMEN`, `app/platforma/xizmat.py`
`BAND_KODLAR`) va akkaunt DARROV yaratiladi — kod band bo'lib qoladi.

### Tartib

1. **Mashq:** vaqtinchalik `inna_mashq` bazasiga to'liq ko'chirish +
   `solishtir.py`. **109 buyurtmaning `attributes` ga o'girilishi shu
   yerda tekshiriladi** (lokal nusxada buyurtma yo'q edi)
2. Repo compose'iga ijarachilik qatorlari qo'shiladi, yangi kod prodga
3. `tizim` akkaunti yaratiladi (baza `inna_tizim`, karton profili)
4. **To'xtash oynasi (5–10 daq):**
   `systemctl stop tizim` → yangi `mode=ro` nusxa → `kochir.py --kirish`
   → rasm fayllari `uploads/inna_tizim/` ga → `solishtir.py` **yashil**
5. `rm /etc/nginx/sites-enabled/tizim && nginx -s reload`
   (wildcard bloki o'z-o'zidan 8100 ga olib boradi)
6. Tekshirish: eski token bilan ochiladimi, qarzdorlar jami mos keladimi

### Orqaga qaytish

Har qadamda ~1 soniya: nginx bloki qaytariladi (`ln -s`), `systemctl
start tizim`. Eski baza **umuman tegilmaydi**.

---

## Ochiq savollar

1. **Rustam akaning kodi alohida yozilgan** — foydalanuvchi aytdi:
   uning `app/` kodi platformanikidan farq qilishi mumkin. Ko'chirishdan
   oldin **manba sxemasi ustunma-ustun tekshirilsin**: `kochir.py`
   `_q()` bilan yo'q ustunni jimgina o'tkazib yuboradi, ya'ni
   nomlanishi boshqacha ustun **jimgina yo'qoladi**. Mashq bosqichida
   har jadvalning ustunlari ro'yxati manba bilan solishtirilsin.
2. `firms` jadvali manbada yo'q — rekvizit `settings` da. Tekshirilsin.
3. Rasm fayllari: `/var/www/tizim/uploads` (97 fayl, 7 MB) →
   platformaning `innasoft_uploads` volumeidagi `inna_tizim/` papkasi.

---

## Nega to'xtatildi

Foydalanuvchi ustuvorlikni o'zgartirdi: avval **bilyard mijozi**
(alohida subdomen, Excel ma'lumoti, Mini App). Rustam akaning o'tishi
shu hujjat bo'yicha keyinroq davom ettiriladi.
