# 023 — DEPLOY: test.innasoft.uz

**Sana:** 2026-08-19
**Holat:** ✅ ishlayapti — https://test.innasoft.uz
**Maqsad:** sinov muhiti (haqiqiy ma'lumot bilan tekshirish uchun)

---

## ⚠️ ENG MUHIM: Rustam akaning tizimidan AJRATILGAN

Server `138.249.248.172` da **Rustam akaning jonli tizimi turadi**
(`/var/www/tizim`). Unga **tegilmadi**. Ajratish to'liq:

| Nima | Rustam aka (jonli) | Bizning sinov |
|---|---|---|
| Papka | `/var/www/tizim` | `/var/www/innasoft-platforma` |
| Port | 8090 (localhost) | **8100** (localhost) |
| Baza | SQLite `gofra_erp.db` | **PostgreSQL** konteynerda (5441) |
| Konteyner | — (systemd) | `innasoft-app`, `innasoft-db` |
| Volume | — | `innasoft-platforma_innasoft_pgdata` |
| nginx | `tizim` | `test.innasoft.uz.conf` |
| Zaxira cron | 03:30 | 03:00 |

**Deploydan keyin tekshirildi:** `tizim.innasoft.uz` → 200,
`archive.innasoft.uz` → 200. Ikkalasi ishlayveradi.

---

## Serverning holati (o'lchangan)

| Resurs | Qiymat |
|---|---|
| CPU | 8 yadro |
| RAM | 23 GB (1.6 GB ishlatilgan) |
| Disk | 296 GB (7% to'lgan) |
| Docker | 29.6.1 + Compose v5.2.0 |
| Python | 3.12.3 |

[09-INFRATUZILMA.md](../09-INFRATUZILMA.md) dagi «A. Boshlash»
tavsiyasidan (4 vCPU / 8 GB) **ancha kuchli** — sinov uchun ortig'i
bilan yetadi.

Serverda boshqa loyihalar ham bor: `inna_backend` (8000),
`inna_postgres`, `inna_redis`, `diydor`, `archive`. Portlar
to'qnashmasligi tekshirildi.

---

## Qadamlar

```
1. /var/www/innasoft-platforma yaratildi (sudo, keyin egasi o'zgardi)
2. rsync — kod yuborildi (.git, .venv, *.db, uploads, .env TASHQARI)
3. .env yozildi: MUHIT=prod, generatsiya qilingan parollar, chmod 600
4. docker compose up -d --build
5. nginx: test.innasoft.uz.conf
6. certbot: Let's Encrypt sertifikati (2026-11-17 gacha, avto-yangilanish)
7. zaxira cron: har kuni 03:00
```

### `.env` dagi qarorlar

| Sozlama | Qiymat | Nega |
|---|---|---|
| `MUHIT` | `prod` | xavfli standart sozlama bilan ishga tushmaydi |
| `POSTGRES_PASSWORD` | generatsiya (24 bayt) | standart parol bilan prodda ishlamaydi |
| `ADMIN_PAROL` | generatsiya (14 belgi) | `1234` majburiy almashtirishdan qutulish |
| `CORS_ORIGINS` | `https://test.innasoft.uz` | `*` emas |
| `SEED_EMPTY` | `1` | demo ma'lumot yuklanmaydi |
| `APP_PORT` | `8100` | bo'sh port |
| `POSTGRES_PORT` | `5441` | 5432/5440 band bo'lishi mumkin |
| **`IJARACHILIK`** | **bo'sh** | quyida |

### Nega ijarachilik O'CHIQ

Ko'p akkaunt subdomen bilan ishlaydi (`mijoz.test.innasoft.uz`), buning
uchun **wildcard DNS** (`*.test.innasoft.uz`) va wildcard sertifikat
kerak. Hozir faqat `test.innasoft.uz` ishora qilyapti.

Shuning uchun sinov muhiti **yagona rejimda** — ERP va buxgalteriya
to'g'ridan-to'g'ri ochiladi. Ijarachilikni yoqish uchun DNS ga wildcard
yozuv qo'shilishi kerak (bir qatorlik ish, keyin `.env` da
`IJARACHILIK=1`).

---

## Ikki nuqson deploy paytida topildi

### 1. Docker porti butun internetga ochilardi

`docker-compose.yml` da:

```yaml
ports:
  - "${APP_PORT:-8070}:8000"     # ❌ IP yo'q
```

IP'siz yozilganda Docker portni **0.0.0.0** ga bog'laydi va **UFW
qoidalarini aylanib o'tadi**. Ya'ni serverga qo'yilganda ilova
to'g'ridan-to'g'ri ochiq qolardi — HTTPS'siz, nginx'siz.

`db` servisida bu qoida allaqachon izoh bilan yozilgan edi, `app` da
unutilgan.

**Tuzatildi:** `127.0.0.1:${APP_PORT:-8070}:8000` — tashqariga faqat
nginx orqali chiqadi.

### 2. nginx konfiguratsiyasida `$` belgisi

Heredoc orqali yozganda `\$host` literal backslash bilan tushdi va
redirect `https://\test.innasoft.uz\/` bo'lib chiqdi. `proxy_set_header
Host` ham buzilardi.

Tuzatildi va tashqaridan tekshirildi: `301 → https://test.innasoft.uz/`.

---

## nginx dagi ikki muhim sozlama

```nginx
client_max_body_size 25m;   # sexdagi telefondan rasm keladi
proxy_buffering off;        # AI javobi NDJSON OQIM bilan keladi
proxy_read_timeout 300s;    # agent halqasi uzoq ishlashi mumkin
```

`proxy_buffering off` bo'lmasa AI javobi oxirigacha buferlanadi va
«jonli qadamlar» ko'rinmaydi — ilovaning asosiy xususiyati yo'qoladi.

---

## Tekshiruv (tashqaridan)

```
✅ https://test.innasoft.uz/api/health → 200, {"holat":"ok"}
✅ HTTP → HTTPS 301
✅ TLS sertifikat yaroqli (2026-11-17 gacha)
✅ login ishlaydi, token olinadi
✅ /api/hisob/schetlar → 28 schet (BHMS №21)
✅ /api/hisob/balans → aktiv 0 == passiv 0 (bo'sh baza)
✅ Brauzerda: kirish → 15 bo'lim, «Бухгалтерия» menyuda
✅ Buxgalteriya ekrani: 7 tab, xatosiz
✅ tizim.innasoft.uz va archive.innasoft.uz — 200 (buzilmadi)
```

Startup logi: 22 profil, **28 schet, 10 provodka qoidasi** yuklandi.

---

## Kirish ma'lumotlari

```
Manzil: https://test.innasoft.uz
Login:  admin
Parol:  scratchpad/test_admin_parol.txt da
```

Parol `.env` da (`chmod 600`) va lokal scratchpad'da. **Repoga
yozilmadi.**

---

## Qoldi

1. **AI kalitlari** — `.env` da bo'sh, qo'yilishi kerak
2. **Wildcard DNS** — ijarachilikni yoqish uchun
3. **Rustam akaning ma'lumotini yuklash** — `tools/kochir.py` bilan,
   ZAXIRA nusxasidan (jonli bazaga tegilmaydi)
4. **1C integratsiyasi** — keyingi bosqich
5. Zaxirani tiklashni bir marta sinash (sinalmagan zaxira — zaxira emas)
