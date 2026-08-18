# 009 — BOSHQARUV BAZASI (A bosqichi, 1-qadam)

**Sana:** 2026-08-18
**Holat:** ✅ tugallandi, sinovdan o'tdi
**TZ:** [../A-IJARACHILIK.md](../A-IJARACHILIK.md) §A.2

---

## Nima qilindi

Ijarachilikning birinchi g'ishti: **mijozlardan mustaqil boshqaruv
bazasi**. Kim ro'yxatdan o'tgan, qaysi bazada, qaysi tarifda, AI ga
qancha sarfladi — hammasi shu yerda.

Mijoz ma'lumoti bu yerda **yo'q**.

---

## Fayllar

| Fayl | Qator | Holat |
|---|---|---|
| `app/platforma/__init__.py` | 11 | yangi |
| `app/platforma/db.py` | 62 | yangi |
| `app/platforma/models.py` | 148 | yangi — 6 jadval |
| `app/platforma/xizmat.py` | 175 | yangi |
| `tests/platforma_test.py` | 196 | yangi — 7 bo'lim |

**Mavjud kodga bitta ham o'zgarish kiritilmadi.** Bu ataylab: yangi
paket qo'shish eski tizimni buza olmaydi, ya'ni qaytarish arzon.

---

## Nega ALOHIDA `BoshqaruvBase`

Eng muhim qaror shu, va u qulaylik uchun emas.

`app/db.py` dagi `Base` mijoz bazasiga tegishli va `main.py`
startupda `Base.metadata.create_all(engine)` chaqiradi. Agar
boshqaruv jadvallari o'sha `Base` da bo'lsa:

```
har mijozning bazasida `firmalar` jadvali paydo bo'lardi
        → ya'ni HAR MIJOZ boshqa mijozlarning ro'yxatini ko'rardi
```

Shuning uchun `app/platforma/db.py` da mustaqil `BoshqaruvBase`,
mustaqil `engine`, mustaqil `Session`.

**Sinovda birinchi tekshiriladigan narsa ham shu** — jadval
to'plamlari kesishmaydi (mijoz 33, boshqaruv 6).

---

## Jadvallar va ular ortidagi qarorlar

### `firmalar`

`baza_nomi` saqlanadi, **ulanish satri emas**. Ulanish satri
serverning `.env` idagi shablondan yasaladi — **parol bazada yotmasin**.

`tayyorlik` maydoni: `CREATE DATABASE` + migratsiya + profil yuklash
bir necha soniya oladi. So'rov ichida qilinmaydi — frontend shu
maydonni kuzatadi. Aks holda ro'yxatdan o'tishning birinchi
taassuroti «osilib qoldi» bo'lardi.

`yozish_mumkinmi` — obuna tugasa **yozish to'xtaydi, o'qish qoladi**.
Ma'lumot garovga olinmaydi ([../07-TARQATISH.md](../07-TARQATISH.md) §7.7).

### `platforma_tokenlar` — tovuq-tuxum tugunining yechimi

Bugun token mijoz bazasidagi `auth_tokens` da. Ijarachilikda muammo:

```
tokenni tekshirish uchun → qaysi bazaga borishni bilish kerak
qaysi baza ekanini bilish uchun → tokenni o'qish kerak
```

Token markaziy bazada bo'lsa tugun yechiladi: `token → firma →
firma bazasi`. Shuning uchun yangi jadval `firma_id` ni ham olib
yuradi.

### `ai_sarf` — narx QOTIRILADI

Provayder narxni o'zgartirsa eski hisob buzilmasligi kerak. Shuning
uchun yozuvga **o'sha paytdagi narx ko'chiriladi** (kirish va chiqish
alohida) va hisoblangan summa ham saqlanadi.

Bu — QQS stavkasini buyurtmada qotirish bilan **aynan bir xil naqsh**.
U yerda ishlagan: davlat stavkani o'zgartirganda eski hujjatlar
buzilmadi.

**Savol matni saqlanmaydi** — faqat metama'lumot. Mijozning biznes
savoli bizning markaziy bazamizda qolmasin.

**Xato bergan so'rov ham yoziladi** (`muvaffaqiyat=False`) — u ham
token sarflaydi va pul turadi. Yozilmasa hisob kam chiqadi va farqni
tushuntirib bo'lmaydi.

### `ai_limitlar`

`limit_som = 0` → cheklovsiz. `UniqueConstraint(firma_id, oy)` —
bitta oyga ikkita limit bo'lmasin.

Qoida: **80% da ogoh, 100% da AI to'xtaydi, ERP ishlayveradi.**

---

## Narx hisobi

```
1 mln token narxi = USD narx × USD kurs × ustama
summa = (kirish/1mln × kirish_narx) + (chiqish/1mln × chiqish_narx)
```

Kurs `USD_KURS`, ustama `AI_USTAMA` (standart 1.30 — valyuta
tebranishi, qayta urinishlar, shlyuz xarajati).

**Noma'lum model bepul emas.** Ro'yxatda yo'q model uchun eng
qimmat stavka olinadi (`NOMALUM_NARX`). Nol qo'yilsa yangi model
qo'shilganda mijozga bepul chiqib ketardi va buni **hech kim
sezmasdi** — sarf hisobidagi eng jimgina xato turi shu.

Hammasi `Decimal` da, `ROUND_HALF_UP`. Float aralashtirilmaydi —
`services.py` dagi qoida bu yerda ham amal qiladi.

---

## Subdomen kodi

`^[a-z][a-z0-9-]{2,39}$` + band nomlar ro'yxati (`www`, `api`,
`admin`, `mail`...).

Baza nomi: `mebel-sex` → `inna_mebel_sex`. Tire pastki chiziqqa
aylanadi, chunki tireli baza nomiga `CREATE DATABASE` da qo'shtirnoq
kerak bo'lardi va bu keyinroq chalkashlik beradi.

---

## Sinov natijasi

`tests/platforma_test.py` — server kerak emas, toza SQLite da.

```
✅ mijoz (33) va boshqaruv (6) jadvallari kesishmaydi
✅ `firmalar` MIJOZ bazasida YO'Q
✅ noto'g'ri kodlar rad etildi (8 xil holat)
✅ takroriy kod rad etildi, auditga yozildi
✅ 1 mln kirish + 100k chiqish = 73 710 so'm
✅ noma'lum model bepul emas
✅ narx 10× oshgach ESKI yozuv o'zgarmadi
✅ limit: 50% jim · 90% ogoh · 100% to'xtatish · 0 cheklovsiz
✅ ikkinchi firmaning sarfi nol — aralashmadi
```

**Eski sinovlar tekshirildi:** `himoya_audit.py` 125/125,
`genui_test.py` toza — yangi paket ularga tegmadi.

---

## Sinov o'zim xato qilganimni ko'rsatdi

Testda `Mebel` rad etilishi kerak deb yozgan edim. Rad etilmadi —
kod uni `mebel` ga keltirdi.

O'ylab ko'rilganda **kod to'g'ri**: subdomen katta-kichik harfni
ajratmaydi, `Mebel.innasoft.uz` va `mebel.innasoft.uz` — bitta
manzil. Foydalanuvchi katta harf bilan yozgani xato emas.

**Testni tuzatdim, kodni emas.** Endi test aniq yozadi: katta harf
va bo'sh joy **normallashtiriladi**, rad etilmaydi.

> Bu naqsh avval ham bo'lgan (007-yozuv): QQS nisbati testida ham
> tizim emas, mening kutganim noto'g'ri edi.

---

## Xavf va qo'riqlash

| Xavf | Qo'riqlash |
|---|---|
| Boshqaruv jadvali mijoz bazasiga tushishi | alohida `Base`, sinovning 1-bo'limi |
| Yangi model bepul sanalishi | `NOMALUM_NARX` + sinov |
| Narx o'zgarib eski hisob buzilishi | narx yozuvga qotiriladi + sinov |
| Baza paroli bazada yotishi | faqat `baza_nomi` saqlanadi |
| Band subdomen (`api`, `admin`) olinishi | `BAND_KODLAR` |

---

## Qoldi (keyingi qadamlar)

1. **`app/db.py`** — `get_db` firmani aniqlab, o'sha bazaning
   `Engine` ini qaytarsin. Hovuz + LRU.
2. **`app/auth.py`** — token boshqaruv bazasidan o'qilsin.
3. **`app/domain.py`** — `_KESH` → `contextvars`.
4. Baza yaratish fon vazifasi (`CREATE DATABASE` + migratsiya).
5. `tests/ijarachilik.py` — 8 mezon.

Hozircha boshqaruv bazasi **hech kim tomonidan ishlatilmaydi** —
jadvallar va mantiq tayyor, ulash keyingi qadamda. Bu ataylab:
ulash bilan birga qilinsa, xato chiqqanda qaysi qism aybdor ekanini
ajratib bo'lmasdi.
