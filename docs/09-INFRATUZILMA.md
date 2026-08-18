# 9. INFRATUZILMA VA AI XARAJATI

> Bu hujjatdagi raqamlar **o'lchangan**, taxmin emas. O'lchov usuli
> har bo'limda ko'rsatilgan. Sana: 2026-08-18.

---

## 9.1 O'lchangan asosiy ko'rsatkichlar

| Nima | Qiymat | Qanday o'lchandi |
|---|---|---|
| Ilova xotirasi (RSS) | **96 MB** | `uvicorn` ishga tushib, `ps -o rss` |
| `/api/health` javobi | **1–30 ms** | `curl -w time_total`, uch marta |
| 1 soha demo bazasi | **228 KB** / 25 buyurtma | SQLite fayl hajmi |
| Bir buyurtma «vazni» | **≈ 9 KB** | 228 KB / 25 (mijoz, to'lov, xarid, ish, material bilan) |

> **Ehtiyot:** o'lchov SQLite da. PostgreSQL indekslar, WAL va
> sahifalash tufayli **3–5 barobar ko'proq** joy oladi. Quyida
> 4× koeffitsient bilan hisoblangan.

---

## 9.2 Bitta mijoz qancha joy oladi

```
1 buyurtma ≈ 9 KB (SQLite) × 4 (PostgreSQL) ≈ 36 KB
```

| Mijoz turi | Buyurtma/oy | Yiliga | Baza/yil |
|---|---|---|---|
| Kichik sex | 50 | 600 | **≈ 22 MB** |
| O'rta korxona | 300 | 3 600 | **≈ 130 MB** |
| Yirik | 1 500 | 18 000 | **≈ 650 MB** |

**Rasmlar alohida** — `uploads/` da, bazada emas. Buyurtma rasmi
brauzerda kichiklashtiriladi (≈ 200–400 KB). 3 600 buyurtmaga 2 ta
rasmdan ≈ **2,5 GB/yil**. Ya'ni **rasm bazadan 20 barobar ko'p joy
oladi** — diskni rasm belgilaydi, baza emas.

---

## 9.3 Ulanishlar — eng qattiq chegara

Bu chegara diskdan ham, protsessordan ham oldin uriladi.

```
50 mijoz × (pool 2 + overflow 3) = 250 ulanish
PostgreSQL standarti              = 100
```

Kodda birinchi qatlam allaqachon bor (`app/tenancy.py`): mijozga
kichik hovuz + LRU (`MAX_ENGINE`). Lekin **prodda PgBouncer shart**:

```
Ilova → PgBouncer (transaction pooling) → PostgreSQL
        1000+ mijoz ulanishi              25–50 haqiqiy ulanish
```

PgBouncer'siz 100 mijozdan oshib bo'lmaydi — qancha RAM qo'shsangiz ham.

---

## 9.4 VDS konfiguratsiyalari

### A. BOSHLASH — 1–10 mijoz

| Resurs | Qiymat | Nega |
|---|---|---|
| vCPU | **4** | ilova + PostgreSQL + zaxira bir vaqtda |
| RAM | **8 GB** | ilova 96 MB × 4 worker ≈ 0,4 GB; qolgani PostgreSQL keshiga |
| Disk | **80 GB NVMe** | baza ~2 GB, rasm ~20 GB, zaxira ~30 GB, tizim ~10 GB |
| Tarmoq | 100 Mbit/s | |
| Narx (taxminan) | 25–45 USD/oy | |

**Muhim:** NVMe majburiy. SATA SSD da PostgreSQL `fsync` sekin bo'ladi
va yozuv paytida butun tizim «osiladi».

### B. O'SISH — 10–50 mijoz

| Resurs | Qiymat |
|---|---|
| vCPU | **8** |
| RAM | **16 GB** |
| Disk | **200 GB NVMe** |
| Qo'shimcha | PgBouncer, zaxira ALOHIDA serverga |

Bu bosqichda **bazani alohida serverga ajratish** boshlanadi:
ilova va PostgreSQL bitta diskda yozuv uchun kurashadi.

### C. YUK — 50–200 mijoz

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  ILOVA ×2    │   │  PostgreSQL  │   │   ZAXIRA     │
│  4 vCPU/8 GB │──▶│  8 vCPU/32GB │──▶│  2 vCPU/8 GB │
│  + nginx     │   │  500 GB NVMe │   │  1 TB HDD    │
└──────────────┘   └──────────────┘   └──────────────┘
                    + PgBouncer
```

Ilova **stateless** — ikkinchi nusxa qo'shish oson. Bitta shart:
`uploads/` umumiy bo'lishi kerak (S3-mos xotira yoki NFS).

---

## 9.5 PostgreSQL sozlamalari

16 GB RAM li server uchun (B variant):

```ini
max_connections = 200            # PgBouncer orqasida ko'p kerak emas
shared_buffers = 4GB             # RAM ning 25%
effective_cache_size = 12GB      # RAM ning 75% — rejalashtiruvchi uchun
work_mem = 16MB                  # har sort/hash uchun, ehtiyot bo'ling
maintenance_work_mem = 1GB       # VACUUM, indeks qurish
wal_buffers = 16MB
checkpoint_completion_target = 0.9
random_page_cost = 1.1           # NVMe uchun (standart 4.0 — HDD uchun)
effective_io_concurrency = 200   # NVMe
max_worker_processes = 8
```

`work_mem` haqida: 200 ulanish × 16 MB = 3,2 GB — bu **eng yomon
holat**. Ko'proq qo'ysangiz og'ir hisobot paytida OOM bo'ladi.

---

## 9.6 ⚠️ QAYERDA joylashishi — huquqiy talab

O'zbekiston qonunchiligida **fuqarolarning shaxsiy ma'lumotlari
O'zbekiston hududidagi serverlarda** saqlanishi talab qilinadi
(«Shaxsga doir ma'lumotlar to'g'risida»gi qonun, 2021-yilgi
o'zgartirishlar).

Bizning tizimda shaxsiy ma'lumot **bor**: mijoz kontakti, telefon,
xodimlar, ish haqi.

```
❌ Hetzner (Germaniya), DigitalOcean, Contabo — arzon, lekin
   shaxsiy ma'lumot uchun mos emas
✅ O'zbekistondagi provayder — majburiy
```

Qo'shimcha foyda: **kechikish**. Toshkentdan Germaniyaga ping
≈ 80–120 ms, mahalliy provayderga ≈ 5–15 ms. Har sahifada 10 so'rov
bo'lsa, farq sezilarli.

> **Tekshirish kerak:** aniq talablar va ro'yxatdan o'tish tartibi
> bo'yicha yuristdan tasdiq oling. Bu hujjat huquqiy maslahat emas.

**Ma'lumotlar markazi tanlashda so'raladigan savollar:**
1. NVMe disk bormi (SATA emas)
2. Snapshot va zaxira qanday olinadi, narxi
3. Tarmoq kafolati (kanal ulushi yoki umumiy)
4. Uptime SLA foizi va kompensatsiya
5. Texnik yordam soat nechada javob beradi (kechasi ham bormi)
6. DDoS himoyasi kiritilganmi

---

## 9.7 AI XARAJATI — bitta foydalanuvchi oyiga qancha

### O'lchov usuli

Taxmin emas, kodning o'zidan o'lchandi:

| Nima | O'lchangan qiymat |
|---|---|
| `moliya` agenti — har so'rovdagi doimiy yuk | **2 101 belgi** (ko'rsatma + asbob sxemasi) |
| `ombor` | 2 430 belgi |
| `buyurtma` | 2 823 belgi |
| `sozlash` (profil yasovchi) | **6 498 belgi** |
| Asbob javobi (demo bazada, o'rtacha) | **1 923 belgi** |
| Asbob javobining chegarasi | 12 000 belgi (`MAX_ASBOB_JAVOBI`) |

Belgidan tokenga: **≈ 3 belgi = 1 token** (o'zbek lotin + JSON).
Narx: `app/platforma/xizmat.py` dagi jadval, 1 USD = 12 600 so'm,
ustama 1,30.

### Bitta savol

| Stsenariy | Kirish | Chiqish | Flash | Sonnet |
|---|---:|---:|---:|---:|
| Oddiy (moliya, 2 qadam) | 2 181 | 1 440 | **70 so'm** | 461 so'm |
| O'rtacha (ombor, 3 qadam) | 4 623 | 2 080 | **108 so'm** | 738 so'm |
| Og'ir (4 qadam, maksimal javob) | 28 204 | 4 120 | **307 so'm** | 2 398 so'm |
| Profil yasash (sozlash, 8 qadam) | 56 179 | 8 280 | **615 so'm** | 4 795 so'm |

### Bitta foydalanuvchi — oyiga (22 ish kuni)

| Foydalanish | Savol/oy | Token/oy | **Flash** | Sonnet |
|---|---:|---:|---:|---:|
| **MINIMAL** — 2 savol/kun | 44 | 159 K | **3 100 so'm** | 20 300 so'm |
| O'rtacha — 8 savol/kun | 176 | 1,2 mln | **19 000 so'm** | 130 000 so'm |
| Faol — 20 savol/kun | 440 | 2,9 mln | **47 500 so'm** | 325 000 so'm |
| **MAKSIMAL** — 40 savol/kun, og'ir | 880 | 28,4 mln | **270 000 so'm** | 2 110 000 so'm |

**Bir martalik:** tizimni AI bilan yig'ish (10 urinish) —
flash **6 150 so'm**, sonnet 48 000 so'm.

### Xulosa — javob

> **Minimal:** ≈ 3 000 so'm/oy (kam ishlatadigan foydalanuvchi, flash)
> **Maksimal:** ≈ 270 000 so'm/oy (kun bo'yi ishlatadigan, flash)
> **Sonnet bilan maksimal:** 2,1 mln so'm/oy — **shuning uchun
> kuchli model kundalik savolga berilmaydi**

10 foydalanuvchili korxona, o'rtacha foydalanish, flash bilan:
**≈ 190 000 so'm/oy**.

### Uch xulosa

**1. Model tanlash — 7 baravar farq.** Flash va Sonnet orasida
farq **7×**. Kundalik savolga (`qarzdorlar`, `pul_holati`) flash
yetarli. Sonnet faqat profil yasashga.

`gemini-3.5-flash-lite` yana **3× arzon** (1 638 / 6 552 so'm 1 mln
tokenga) — oddiy savollar shunga o'tkazilsa sarf yana uchdan biriga
tushadi.

**2. Kirish tokeni chiqishdan ko'p.** Har qadamda ko'rsatma va
asbob sxemasi qayta yuboriladi. Ikki yo'l:
- **Prompt caching** — bir xil ko'rsatma keshlanadi, arzonlashadi
  (Anthropic va Gemini da bor). Bu **eng katta tejash imkoniyati**.
- `sozlash` ko'rsatmasi 6 498 belgi — qisqartirilsa har chaqiruv
  arzonlashadi.

**3. Og'ir stsenariy 4 baravar qimmat.** Sabab: asbob javobi
12 000 belgiga yetganda keyingi qadamlarda u qayta-qayta yuboriladi.
`nechta` parametri bilan javobni cheklash — to'g'ridan-to'g'ri pul
tejash.

### Limit qanday qo'yiladi

`ai_limitlar` jadvali tayyor (`app/platforma/models.py`).
Tavsiya etilgan standart:

| Tarif | Oylik AI limiti |
|---|---|
| Boshlang'ich | 50 000 so'm |
| Biznes | 250 000 so'm |
| Korxona | kelishuv bo'yicha |

80% da ogohlantirish, 100% da AI to'xtaydi — **ERP ishlayveradi**.

---

## 9.8 Zaxira

```
Kunlik  → to'liq `pg_dump`, 14 kun saqlanadi
Doimiy  → WAL arxivi (istalgan daqiqaga tiklash)
Haftalik→ BOSHQA serverga nusxa (bitta server yonib ketsa)
Oylik   → TIKLASH SINALADI
```

> **Sinalmagan zaxira — zaxira emas.** Oyda bir marta bo'sh bazaga
> tiklanadi va `tools/butunlik.py` yurgiziladi. Toza o'tmasa —
> zaxira jarayonida muammo bor.

Hozir `./zaxira.sh` bor va u kunlik nusxa oladi. Ijarachilikda u
**har mijozning bazasini alohida** olishi kerak — hali qilinmagan.

---

## 9.9 Monitoring — nima kuzatiladi

| Ko'rsatkich | Chegara |
|---|---|
| Javob vaqti (p95) | > 1 s — tekshiriladi |
| Xatolar (5xx) | > 1% — darhol |
| Disk to'lishi | > 80% — ogoh |
| PostgreSQL ulanishlari | > 70% — PgBouncer sozlanadi |
| AI sarfi (har mijoz) | limitning 80% i |
| Zaxira | bajarilmasa darhol xabar |

Eng arzon boshlanish: `docker stats` + `pg_stat_statements` +
disk uchun cron. Keyinroq Prometheus/Grafana.

---

## 9.10 Xavfsizlik — server darajasida

Kodda allaqachon bor: 125/125 endpoint himoyalangan, brute-force
cheklovi, standart parol majburan almashtiriladi, `MUHIT=prod` da
xavfli sozlama bilan ishga tushmaydi.

Serverda qo'shiladi:

1. **SSH faqat kalit bilan**, parol bilan kirish o'chiriladi
2. **Faqat 80/443 ochiq**, PostgreSQL porti **tashqariga chiqmaydi**
   (`docker-compose.yml` da allaqachon `127.0.0.1` ga bog'langan)
3. **HTTPS majburiy** — Let's Encrypt, avtomatik yangilanish
4. **Fail2ban**
5. **Avtomatik xavfsizlik yangilanishlari**
6. **Zaxira SHIFRLANGAN** — undagi ma'lumot bazadagidek qimmatli

---

## 9.11 Boshlash uchun ro'yxat

```
[ ] O'zbekistondagi provayder tanlanadi (9.6 dagi 6 savol)
[ ] 4 vCPU / 8 GB / 80 GB NVMe
[ ] Domen: app.innasoft.uz + *.innasoft.uz (wildcard — subdomen uchun)
[ ] Wildcard TLS sertifikat (har mijozga alohida olinmasin)
[ ] Docker + Docker Compose
[ ] PostgreSQL 16 sozlanadi (9.5)
[ ] nginx + HTTPS
[ ] zaxira.sh cron ga
[ ] MUHIT=prod, kuchli parollar, CORS aniq domen
[ ] Tiklash BIR MARTA sinaladi
[ ] AI kalitlari .env da (mijozda emas — SaaS)
[ ] AI limitlari tariflar bo'yicha qo'yiladi
```

**Wildcard sertifikat haqida:** har mijozga alohida sertifikat
olinsa, Let's Encrypt chegarasiga (haftasiga 50 ta) tez yetiladi.
`*.innasoft.uz` bitta sertifikat bilan hamma subdomen yopiladi —
DNS-01 tekshiruvi orqali.
