# A — IJARACHILIK (multi-tenancy) va SaaS

> Bosqich A ning ish hujjati. [06-YOL-XARITASI.md](06-YOL-XARITASI.md)
> da bosqich e'lon qilingan, [07-TARQATISH.md](07-TARQATISH.md) da
> SaaS qarori. Bu yerda — **aniq jadvallar, endpointlar, tartib va
> sinov mezonlari**.
>
> **Vaqt:** 4–6 hafta. **Holat:** boshlanmagan.

---

## A.0 Bir jumlada

Bugun: bitta jarayon → bitta baza → bitta korxona.
Kerak: bitta jarayon → **so'rovdan mijoz aniqlanadi** → o'sha
mijozning bazasi.

Va ustiga: ro'yxatdan o'tish, tarif, AI sarfi, admin paneli.

---

## A.1 Nima uchun alohida BAZA

Uch yo'l bor, ikkitasi qabul qilinmadi:

| Yo'l | Qanday | Nega yo'q / ha |
|---|---|---|
| `mijoz_id` ustuni | har jadvalga ustun, har so'rovga `WHERE` | ❌ bitta unutilgan `WHERE` = boshqa mijozning ma'lumoti. 117 endpoint, yuzlab so'rov — bir kun albatta unutiladi |
| Alohida schema | `search_path` almashtiriladi | ❌ ulanish adashsa — o'sha xavf, faqat kamroq ehtimol bilan |
| **Alohida baza** | mijoz bo'yicha `Engine` | ✅ noto'g'ri ulansa jadval **umuman topilmaydi** — xato darhol chiqadi, jimgina sir oshkor bo'lmaydi |

Narxi (ochiq aytiladi): migratsiya har bazada yurishi kerak, zaxira
ko'p, ulanishlar ko'p, «hamma mijoz bo'yicha hisobot» qiyin. Bu narx
qabul qilinadi — muqobili ma'lumot sizishi.

`app/db.py` da bu allaqachon oldindan aytilgan (PostgreSQL tanlash
sababi). Ya'ni yo'l poydevorga mos.

---

## A.2 Boshqaruv bazasi — `platforma_boshqaruv`

Bu **alohida baza**, mijoz bazalaridan tashqarida. Faqat platforma
kodi ko'radi, mijoz hech qachon ko'rmaydi.

### Jadvallar

**`firmalar`** — kim ro'yxatdan o'tgan

| Ustun | Tur | Izoh |
|---|---|---|
| `id` | int | |
| `kod` | str, unik | subdomen: `mebelsex` → `mebelsex.innasoft.uz` |
| `nom` | str | «Mebel Sex MCHJ» |
| `inn` | str | |
| `qqs_tolovchi` | bool | |
| `baza_nomi` | str | `inna_mijoz_7` |
| `holat` | str | `sinov` · `faol` · `muzlatilgan` · `ochirilgan` |
| `tarif` | str | `boshlangich` · `biznes` · `korxona` |
| `yaratilgan`, `obuna_tugaydi` | datetime | |

**`platforma_userlar`** — ro'yxatdan o'tgan odam (mijoz bazasidagi
`users` bilan ARALASHTIRILMAYDI)

| Ustun | Izoh |
|---|---|
| `telefon` / `email`, unik | kirish |
| `parol_hash` | `auth.hash_pw` — bir xil funksiya |
| `firma_id` | qaysi firmaga tegishli |
| `platforma_roli` | `egasi` · `xodim` |

**`ai_sarf`** — har AI so'rovi ([07](07-TARQATISH.md) §7.6)

| Ustun | Izoh |
|---|---|
| `firma_id`, `vaqt` | kimga hisob |
| `provayder`, `model` | narx shundan |
| `kirish_token`, `chiqish_token` | asosiy o'lchov |
| `narx_som` | **o'sha paytdagi narx bo'yicha, QOTIRILADI** |
| `agent`, `user_login` | ichkarida kim sarflaydi |
| `muvaffaqiyat` | xato bo'lgan so'rov ham yoziladi (u ham pul) |

> Narxni qotirish — QQS stavkasini buyurtmada qotirish bilan **bir xil
> naqsh**. U yerda ishlagan: davlat stavkani o'zgartirganda eski
> hujjatlar buzilmadi.

**`ai_limit`** — firma bo'yicha oylik limit, ogohlantirish holati

**`platforma_audit`** — firma yaratildi/muzlatildi/o'chirildi, tarif
o'zgardi, limit oshirildi. Kim qildi, qachon.

---

## A.3 So'rovdan mijozni aniqlash

```
So'rov  →  subdomen  →  firma  →  o'sha firmaning Engine i  →  Session
           mebelsex.innasoft.uz
```

### Tartib (ustuvorlik bo'yicha)

1. **Subdomen** — asosiy yo'l
2. **`X-Firma` sarlavhasi** — Telegram Mini App va mobil uchun
   (subdomen qulay emas)
3. **Token ichidan** — `auth_tokens` mijoz bazasida bo'lgani uchun
   bu yo'l ishlamaydi; token **boshqaruv bazasida** saqlanadi va
   firma id ni o'zi olib yuradi

**Qaror:** token boshqaruv bazasiga ko'chadi. Sabab — tokenni
tekshirish uchun avval qaysi bazaga borishni bilish kerak, ya'ni
tovuq-tuxum. Boshqaruv bazasidagi token bu tugunni yechadi.

### Kod o'zgarishi

`app/db.py` da `get_db` bugun global `SessionLocal` ni qaytaradi.
Yangi shakl:

```python
_ENGINELAR: dict[str, Engine] = {}          # baza_nomi -> Engine

def firma_engine(baza_nomi: str) -> Engine
def get_db(request) -> Session               # firmani aniqlab, o'sha Session
```

**117 endpoint o'zgarmaydi** — hammasi `Depends(get_db)` ishlatadi,
almashtirish bitta joyda bo'ladi. Bu — hozirgi kodning yaxshi tomoni.

### Ulanishlar hovuzi — chegara MAJBURIY

Har `Engine` `pool_size=10, max_overflow=20` bo'lsa, 50 mijozda
1500 ulanish. PostgreSQL standarti — 100.

**Qaror:** mijoz bo'yicha `pool_size=2, max_overflow=3`, ustiga
**LRU**: eng kam ishlatilgan `Engine` yopiladi (masalan 50 tadan
ortiq bo'lsa). Kechasi ishlamaydigan mijoz ulanish band qilmaydi.

---

## A.4 Uchta unutilmaydigan joy

Bular jimgina buzadigan joylar — testda ko'rinmaydi, prodda ko'rinadi.

### 1. `domain.py` profil keshi — GLOBAL

```python
_KESH: Profil | None = None      # app/domain.py
```

Bugun bitta modul o'zgaruvchisi. Ikki mijoz bo'lsa: mebel sexi
so'rov yubordi → kesh mebel bo'ldi → non zavodi so'rov yubordi →
**non zavodiga mebel maydonlari ko'rinadi**.

Kod ichida ogohlantirish allaqachon yozilgan (`domain.py` bosh
izohi) — endi bajariladi:

```python
_KESH: dict[str, Profil] = {}    # baza_nomi -> Profil
def profil(firma) -> Profil
```

`profil()` ni chaqiradigan joylar: `agent.py`, `routers/soha.py`,
`routers/warehouse.py`, `routers/orders.py`, `main.py` — **26 ta
chaqiruv**. Hammasiga firma kontekstini uzatish kerak.

**Eng xavfsiz yo'l:** `contextvars` — so'rov boshida joriy firma
o'rnatiladi, `profil()` imzosi o'zgarmaydi. Aks holda 26 joyni
qo'lda tuzatishda bittasi unutiladi.

### 2. Fon vazifalari

`app/bot.py:183` — `threading.Thread(..., name="gofra-bot")`.
Bitta bot bitta bazaga yozadi. Ko'p mijozda bot **qaysi firma
uchun** ishlayotganini bilishi shart.

**Qaror:** bot boshqaruv bazasidan Telegram tokeni bor firmalarni
o'qiydi va har biriga alohida ishlaydi. `contextvars` shu yerda ham.

### 3. `lifespan` — startupdagi ishlar

Bugun `main.py` startupda: `create_all` → `run_migrations` →
`profillarni_yukla` → `qayta_yukla` → `seed` → `backfill_soha`.
Hammasi **bitta bazaga**.

Ko'p mijozda bular startupda emas, **firma yaratilganda** va
**migratsiya buyrug'ida** bajariladi. Startupda faqat boshqaruv
bazasi tayyorlanadi.

---

## A.5 Migratsiya — 50 bazada qanday yuriladi

```
tools/migratsiya.py --hammasi
```

Tartib:

1. Boshqaruv bazasidan faol firmalar ro'yxati
2. Har biriga: **zaxira** → `create_all` → `run_migrations` →
   `butunlik.py`
3. Bittasi xato bersa: **o'sha firma qaytariladi**, qolganlari
   davom etadi, oxirida hisobot
4. Natija `platforma_audit` ga yoziladi

**Qoida (`migrate.py` da allaqachon bor):** migratsiya faqat
**qo'shadi**. Ustun o'chirish alohida buyruq, ogohlantirish bilan.

**Versiya:** har baza o'z sxema versiyasini saqlaydi. Kod versiyasi
bazanikidan yangi bo'lsa — migratsiya, eski bo'lsa — **ishga
tushmaydi** (orqaga qaytarilgan kod yangi bazani buzmasin).

---

## A.6 Ro'yxatdan o'tish oqimi

```
1. telefon/email → tasdiqlash kodi
2. firma: nom, INN, QQS to'lovchimi
3. baza yaratiladi (CREATE DATABASE) + migratsiya + profillar
4. AI SEHRGARI: «biznesingizni ayting»
5. AI profil yig'adi → sinov buyurtmasi bilan O'ZI tekshiradi
6. egasi xodimlarni chaqiradi (rol bilan)
7. ishlaydi
```

### Endpointlar

| Metod | Yo'l | Nima |
|---|---|---|
| POST | `/api/platforma/royxat` | telefon/email yuborish |
| POST | `/api/platforma/tasdiq` | kodni tekshirish |
| POST | `/api/platforma/firma` | firma yaratish → baza |
| GET | `/api/platforma/holat` | tayyorlanish jarayoni |
| POST | `/api/platforma/taklif` | xodim chaqirish |
| GET/POST | `/api/platforma/tarif` | joriy tarif, o'zgartirish |
| GET | `/api/platforma/ai-sarf` | token, pul, limit |
| POST | `/api/platforma/ai-limit` | limit qo'yish |

**Admin (faqat biz):**

| Metod | Yo'l | Nima |
|---|---|---|
| GET | `/api/admin/firmalar` | ro'yxat, holat, oxirgi faollik |
| POST | `/api/admin/firma/{id}/holat` | muzlatish, ochish |
| GET | `/api/admin/sarf` | hamma bo'yicha AI sarfi |
| GET | `/api/admin/xatolar` | oxirgi xatolar, firma bo'yicha |

### Baza yaratish — sekin ish

`CREATE DATABASE` + migratsiya + profil yuklash bir necha soniya.
So'rov ichida qilinmaydi — **fon vazifasi**, foydalanuvchi
`/holat` ni kuzatadi. Aks holda birinchi taassurot «osilib qoldi»
bo'ladi.

---

## A.7 Obuna tugaganda

```
Obuna tugadi  →  YOZISH to'xtaydi
              →  O'QISH va EKSPORT ochiq qoladi
              →  ma'lumot O'CHIRILMAYDI
```

Muhlat: 90 kun muzlatilgan holat, keyin ogohlantirish bilan
arxivga. **Ma'lumot garovga olinmaydi** — bu qoida
[07-TARQATISH.md](07-TARQATISH.md) §7.7 dan o'zgarishsiz keladi.

AI limiti tugaganda esa: AI to'xtaydi, **ERP to'liq ishlayveradi**.

---

## A.8 Sinov mezonlari — «tayyor» qachon deyiladi

`tests/ijarachilik.py`. Bosqich shu test toza o'tmaguncha
tugallanmagan hisoblanadi.

| # | Tekshiruv |
|---|---|
| 1 | Ikki firma yaratiladi, ikkalasiga ma'lumot yoziladi |
| 2 | **Har endpoint** A firma tokeni bilan B ning ID lariga urinadi — bittasi ham o'tmaydi (404/403, 200 EMAS) |
| 3 | A ning profili mebel, B niki non — ikkalasi **parallel** so'rov yuboradi, har biri o'z maydonlarini oladi (kesh sinovi) |
| 4 | Migratsiya ikkala bazada yuradi, `butunlik.py` ikkalasida toza |
| 5 | Bir firma o'chirilsa, ikkinchisi shikastlanmaydi |
| 6 | 20 firma bir vaqtda so'rov yuborganda ulanishlar tugamaydi |
| 7 | AI so'rovi `ai_sarf` ga yoziladi, narx qotirilgan |
| 8 | Limit tugaganda AI to'xtaydi, buyurtma yaratish ISHLAYDI |

**2-tekshiruv eng muhimi.** U `tests/himoya_audit.py` dagi
«124/124 endpoint himoyalangan» naqshining davomi — o'sha yerda
har endpoint tokensiz sinalgan edi, bu yerda **boshqa firmaning
tokeni bilan** sinaladi.

---

## A.9 Ish tartibi (haftalar bo'yicha)

| Hafta | Ish |
|---|---|
| 1 | Boshqaruv bazasi, modellari, firma yaratish/o'chirish |
| 1–2 | `get_db` mijoz bo'yicha, `Engine` hovuzi + LRU |
| 2 | `contextvars`, `domain._KESH` mijoz bo'yicha, bot |
| 2–3 | `tools/migratsiya.py --hammasi`, sxema versiyasi |
| 3 | `tests/ijarachilik.py` — 1–6 tekshiruv |
| 3–4 | Ro'yxatdan o'tish, tasdiqlash, tarif |
| 4 | AI sarfi hisobi, limit — 7–8 tekshiruv |
| 5 | Admin paneli, frontend ekranlari (F1/F3 bilan birga) |
| 6 | Zaxira/tiklash, monitoring, sinovdan o'tkazish |

Frontend tomoni: [08-FRONTEND.md](08-FRONTEND.md) §8.4.

---

## A.10 Xavflar

| Xavf | Oqibati | Oldini olish |
|---|---|---|
| Global holat unutilgan joyda qoladi | bir mijozning ma'lumoti boshqasiga | `contextvars`, 3-tekshiruv, kodda global o'zgaruvchi qidiruvi |
| Ulanishlar tugaydi | butun platforma to'xtaydi | mijoz bo'yicha kichik hovuz + LRU, 6-tekshiruv |
| Migratsiya bir bazada buziladi | o'sha mijoz ishlamaydi | har bazadan oldin zaxira, xatoda qaytarish |
| Zaxira sinalmagan | tiklash kerak bo'lganda ishlamaydi | **oyda bir marta** bo'sh bazaga tiklab `butunlik.py` |
| Baza yaratish sekin | «osilib qoldi» taassuroti | fon vazifasi + `/holat` ekrani |
| AI sarfi noto'g'ri hisoblanadi | mijozga noto'g'ri hisob | narx qotiriladi, xato so'rov ham yoziladi, 7-tekshiruv |

---

## A.11 Bu bosqichda QILINMAYDI

Chegara aniq bo'lsin, aks holda bosqich cho'ziladi:

- ❌ Bosh kitob (B bosqichi)
- ❌ RAG (C bosqichi)
- ❌ To'lov tizimlari — tarif hozircha qo'lda faollashtiriladi
- ❌ On-premise, litsenziya kaliti ([07](07-TARQATISH.md) §7.9)
- ❌ Frontend framework ([08](08-FRONTEND.md) F6)
- ❌ Mijozlar orasidagi umumiy hisobot

---

## A.12 Sinov ma'lumoti

Bosqich yakunida ikkita baza bilan sinaladi:

1. **Rustam akaning read-only nusxasi** — haqiqiy ma'lumot, oltita
   xato aynan shundan topilgan edi
2. **`tools/demo_data.py` dan boshqa soha** — masalan non yoki mebel

Ikkalasi parallel ishlashi va bir-birini ko'rmasligi shart.

> ⚠️ **Jonli tizimga TEGILMAYDI.** Server `/var/www/tizim` va lokal
> `~/Desktop/rustam_aka/` — boshqa chatda boshqariladi. Bu yerda
> faqat nusxa.
