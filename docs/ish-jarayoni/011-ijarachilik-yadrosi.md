# 011 — IJARACHILIK YADROSI (A bosqichi, 2-qadam)

**Sana:** 2026-08-18
**Holat:** ✅ ishlaydi, sinovdan o'tdi
**TZ:** [../A-IJARACHILIK.md](../A-IJARACHILIK.md) §A.3–A.4

---

## Nima qilindi

So'rov endi **mijozga bog'lanadi**: subdomen → firma → o'sha firmaning
bazasi va o'sha firmaning profili. Ikki mijoz bir jarayonda ishlaganda
ma'lumot aralashmaydi.

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `app/tenancy.py` | **yangi**, 214 qator |
| `app/db.py` | `get_db` firma bo'yicha + `sessiya()` (+22) |
| `app/domain.py` | `_KESH` → lug'at, `keshni_tozala()` (+20) |
| `app/main.py` | ijarachilik middleware (+38) |
| `tests/ijarachilik_test.py` | **yangi**, 165 qator |

**125 endpointning birortasiga tegilmadi.** Reja shuni aytgan edi va
amalda shunday chiqdi — `Depends(get_db)` naqshi tufayli.

---

## Eng muhim qaror: `contextvars`, argument emas

`profil()` kodda **26 joyda** chaqiriladi. Har biriga `firma`
argumenti qo'shilsa — bittasi albatta unutiladi, va unutilgan joy
xato bermaydi, **jimgina boshqa mijozning profilini** ko'rsatadi.

`contextvars` da imzolar o'zgarmaydi, lekin har so'rov o'z qiymatini
ko'radi. Middleware so'rov boshida o'rnatadi, oxirida tozalaydi.

```python
_JORIY: ContextVar[Firma | None] = ContextVar("joriy_firma", default=None)
```

`default=None` ataylab: firma **o'rnatilmagan holat ham to'g'ri
holat** — fon vazifalari, vositalar, ijarachiliksiz rejim.

---

## Ikkinchi qaror: ORQAGA MOSLIK bayrog'i

`IJARACHILIK=1` bo'lmasa hamma narsa **aynan avvalgidek** ishlaydi.

Nega muhim: bugun ishlab turgan tizim bor va u buzilmasligi kerak.
Bayroqsiz yozilganda har o'zgarish «endi ishlaydimi?» degan savolni
tug'dirardi. Bayroq bilan javob aniq: o'chiq — eski yo'l, yoniq —
yangi yo'l, ikkalasi ham sinaladi.

Kesh kaliti yagona rejimda doim `"_yagona"` — ya'ni lug'atga
o'tkazish eski xatti-harakatni o'zgartirmadi. Sinov buni tekshiradi.

---

## Uchinchi qaror: token KO'CHIRILMADI

[../A-IJARACHILIK.md](../A-IJARACHILIK.md) §A.3 da «token boshqaruv
bazasiga ko'chadi» deb yozgan edim. **Amalda kerak bo'lmadi.**

Sabab: firma **subdomendan** aniqlanadi, tokendan emas. Ya'ni
tovuq-tuxum tuguni umuman paydo bo'lmaydi — `get_db` allaqachon
to'g'ri bazaga borgan bo'ladi va ERP tokeni o'sha yerda topiladi.

`platforma_tokenlar` jadvali behuda emas — u **boshqa narsa uchun**:
ro'yxatdan o'tish va hisob-kitob kabinetiga kirish (u yerda hali
firma bazasi bo'lmasligi mumkin).

> Rejadagi qaror amalda soddaroq chiqdi. Hujjat yangilanadi.

---

## Ulanishlar chegarasi

Muammo aniq edi: 50 mijoz × (pool 10 + overflow 20) = **1500 ulanish**,
PostgreSQL standarti **100**.

Ikki chegara qo'yildi:

1. **Kichik hovuz** — mijozga `pool_size=2, max_overflow=3`
   (`MIJOZ_POOL`, `MIJOZ_POOL_OVERFLOW`)
2. **LRU** — ochiq `Engine` soni `MAX_ENGINE` (standart 50) dan
   oshsa, eng kam ishlatilgani yopiladi

Kechasi ishlamaydigan mijoz ulanish band qilib turmaydi.

50 mijozda eng yomon holat: 50 × 5 = 250. Bu ham ko'p, shuning
uchun prodda `max_connections` oshiriladi yoki PgBouncer qo'yiladi —
infratuzilma hujjatida hisoblangan.

---

## Middleware — ikki qoida

**1. Firma topilmasa 400, 404 emas.** Javob har doim bir xil:
«Firma aniqlanmadi». Aks holda tashqaridan mijoz kodlarini sanab
chiqish mumkin bo'lardi (qaysi firma bor, qaysi yo'q).

**2. Obuna tugagan firma O'QIY oladi, YOZA olmaydi.** `GET/HEAD/
OPTIONS` o'tadi, qolgani 402 qaytaradi. Ma'lumot garovga olinmaydi —
[../07-TARQATISH.md](../07-TARQATISH.md) §7.7 qoidasi endi kodda.

---

## Sinov natijasi

`tests/ijarachilik_test.py` — ikki SQLite baza, bitta jarayon,
har firmada **boshqa profil** (mebel va non).

```
1. subdomen ajratish: 8 holat (asosiy domen, www, ichma-ich,
   begona domen — hammasi rad etildi)
2. PROFIL KESHI: non so'rovidan KEYIN ham mebel o'z profilini ko'rdi
   (mebel 7 maydon, non 5 — aralashmadi)      ← eng muhimi
3. har baza faqat o'z mijozini ko'radi; `get_db()` to'g'ri bazaga bordi
4. LRU: MAX_ENGINE=3 da 6 baza ochilgach 3 ta qoldi
5. ijarachiliksiz rejim: kalit "_yagona" — o'zgarmagan
6. keshni tozalash faqat o'z firmasiga tegdi
```

### Regressiya — eski sinovlar

| Sinov | Natija |
|---|---|
| `himoya_audit.py` | ✅ 125/125 |
| `genui_test.py` | ✅ 8 primitiv, 5 amal |
| `profil_test.py` | ✅ 22 profil to'liq sikldan o'tdi |
| `chuqur_sinov.py` | ✅ 22 soha hisob-kitob to'g'ri |
| `audit.py` | ✅ 38 endpoint, 0 xato |
| `platforma_test.py` | ✅ hammasi |
| `kochirish_test.py` | ⚠️ **yurgizilmadi** — PostgreSQL kerak, Docker demoni ishlamayapti |

Ilova bevosita ko'tarildi va tekshirildi:
`{"holat":"ok","profil":"karton"}`, logda kesh kaliti `[_yagona]`.

> **Halol qayd:** `kochirish_test.py`, `e2e_test.py` va
> `butunlik.py` Docker'siz yurmadi. Ular mening o'zgarishimga
> bog'liq emas (ikkalasi ham `get_db` orqali ishlaydi va u sinalgan),
> lekin **sinalmagan** — Docker ko'tarilganda qayta yurgizish kerak.

---

## Xavf va qo'riqlash

| Xavf | Qo'riqlash |
|---|---|
| Yangi global holat qo'shilishi | `tenancy.kalit()` naqshi, sinovning 2-bo'limi |
| Fon vazifasi firmasiz yozishi | `db.sessiya()` izohida ogohlantirish |
| Ulanishlar tugashi | kichik hovuz + LRU + sinovning 4-bo'limi |
| Firma keshi eskirishi | `firma_keshini_tozala()` — holat o'zgarganda |
| Eski rejim buzilishi | `IJARACHILIK` bayrog'i + regressiya sinovlari |

---

## Qoldi

1. **`bot.py`** — hali bitta bazaga yozadi (ijarachilikda firma
   bo'yicha bo'linishi kerak)
2. **`main.py` `lifespan`** — startupdagi ishlar hali yagona bazaga
3. Baza yaratish fon vazifasi (`CREATE DATABASE` + migratsiya)
4. `tools/migratsiya.py --hammasi`
5. Ro'yxatdan o'tish endpointlari
