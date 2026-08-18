# 001 — YADRO VA BAZA

**Sana:** retrospektiv (2026-08-18 da yozildi)
**Fayllar:** `app/db.py` (57) · `app/models.py` (561) · `app/auth.py` (137) ·
`app/main.py` (200) · `app/migrate.py` (236) · `app/seed.py` (456)

---

## Nima qilindi

Loyihaning eng past qatlami: baza ulanishi, 33 jadval, kirish va rol
tekshiruvi, FastAPI ilovasi, yengil migratsiya.

---

## `app/db.py` — nega PostgreSQL

SQLite bitta faylga yozadi va yozish paytida **butun bazani qulflaydi**.
Bir sexda 10 kishi ishlaganda «database is locked» chiqadi.

Ikkinchi sabab oldindan yozib qo'yilgan: platformada har mijozga
alohida baza bo'ladi. PostgreSQL da bu `CREATE DATABASE` / `pg_dump`,
SQLite da esa fayl ko'chirish bilan qo'lda.

SQLite baribir qoldirildi — **testlar bir soniyada toza bazadan
boshlashi kerak**. Kod ikkalasida ham ishlaydi.

Hovuz: `pool_size=10, max_overflow=20, pool_pre_ping=True,
pool_recycle=1800`. `pre_ping` — NAT/proxy uzgan ulanishni so'rovdan
oldin tekshiradi, `recycle` — 30 daqiqada yangilaydi.

> ⚠️ Bu sozlama **bitta mijozga** hisoblangan. 50 mijozda 1500 ulanish
> bo'ladi, PostgreSQL standarti 100. Ijarachilikda o'zgaradi.

---

## `app/models.py` — 33 jadval

**Eng muhim qaror: pul ustunlari `Numeric(18,2)`, float emas.**
Float da `0.1 + 0.2 != 0.3`. Moliyaviy dasturda bu qabul qilinmaydi —
oyning oxirida balans bir tiyinga to'g'ri kelmaydi va sababini topib
bo'lmaydi.

**Ikkinchi qaror: `orders.attributes` — JSONB.** Karton uchun
`uzunlik/eni/qalinlik`, non uchun `og'irlik/un_navi`. Agar har soha
uchun ustun qo'shilsa, 22 sohada 200 dan ortiq ustun bo'lardi va
ularning 95% i har qatorda bo'sh turardi.

**Uchinchi: QQS stavkasi buyurtmada saqlanadi.** Davlat stavkani
o'zgartirsa eski hujjatlar buzilmaydi. Bu naqsh keyinroq AI narxini
qotirishda ham ishlatiladi.

---

## `app/auth.py` — himoya

- Parol `bcrypt` bilan
- Token bazada (`auth_tokens`), muddati bor
- `require_roles(*roles)` — endpoint darajasida rol
- **Brute-force cheklovi IP bo'yicha** — `login_cheklovini_tekshir`

`admin/1234` birinchi kirishda majburan almashtiriladi va buni
**backend qulflaydi** — frontenddan aylanib o'tib bo'lmaydi. Parol
kamida 8 belgi, oddiy parollar ro'yxati rad etiladi.

> Bir vaqtlar 4 belgi yetardi. Tizimda pul, qarz va mijoz bazasi
> turganini hisobga olib qattiqlashtirildi.

---

## `app/main.py` — ilova

CORS standarti **`*` emas**. Frontend shu serverdan beriladi, ya'ni
cross-origin umuman kerak emas. `*` esa har qanday sayt brauzerdan
API javobini o'qiy olishini bildirardi.

`MUHIT=prod` da server **ishga tushmaydi**, agar: standart
`POSTGRES_PASSWORD`, `CORS_ORIGINS=*`, yoki `SEED_DEMO=1`. Bu —
«prodga demo ma'lumot bilan chiqib ketish» xatosining oldini oladi.

`lifespan` tartibi muhim: profil `seed` dan **oldin** yuklanadi,
chunki seed buyurtma yaratganda `soha_yoz()` to'g'ri profilni bilishi
kerak.

---

## `app/migrate.py` — nega Alembic emas

`Base.metadata.create_all()` faqat **yangi jadval** yaratadi, mavjud
jadvalga ustun qo'shmaydi. Alembic to'liq yechim, lekin u har
o'zgarishda migratsiya fayli yozishni talab qiladi.

Tanlangan yo'l: modelni inspeksiya qilib **yetishmayotgan ustunni
qo'shadigan** yengil migratsiya. Kichik loyihada tezroq.

**Qoida: migratsiya faqat qo'shadi.** Ustun o'chirish alohida
(`jadvalni_qayta_qur`), ogohlantirish bilan — chunki o'chirish
qaytarib bo'lmaydigan amal.

> Bu qaror ijarachilikda qayta ko'riladi: 50 bazada versiyani
> kuzatish kerak bo'ladi, o'shanda Alembic foydasi ortishi mumkin.

---

## Xavf va qo'riqlash

| Xavf | Qo'riqlash |
|---|---|
| Endpoint himoyasiz qolishi | `tests/himoya_audit.py` — AST bo'yicha, serversiz |
| Prodga demo ma'lumot | `MUHIT=prod` tekshiruvi ishga tushishni to'xtatadi |
| Standart parol qolishi | backend majburan almashtiradi |
| Migratsiyada ma'lumot yo'qolishi | faqat qo'shadi, o'chirish alohida |

---

## Ijarachilikda nima o'zgaradi

`db.py` va `auth.py` — **eng birinchi tegiladigan ikki fayl**.
Tafsilot: [../A-IJARACHILIK.md](../A-IJARACHILIK.md) §A.3.
