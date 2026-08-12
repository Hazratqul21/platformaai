# INNASOFT PLATFORMA — prodga chiqarish

Server: Ubuntu 22.04+, 2 CPU / 4 GB RAM / 40 GB disk yetadi.
Kerak bo'lgani: `docker` va `docker compose`. Boshqa hech narsa.

---

## 1. O'rnatish

```bash
git clone <repo> /opt/innasoft && cd /opt/innasoft
cp .env.example .env
```

`.env` da **majburan** o'zgartiriladigan uchta narsa:

```dotenv
MUHIT=prod                       # xavfli standartlar bilan ishga tushmasin
POSTGRES_PASSWORD=<uzun tasodifiy parol>
CORS_ORIGINS=https://erp.sizning-domen.uz
```

Parolni shunday yasang:

```bash
openssl rand -base64 32
```

Ixtiyoriy: `BOT_TOKEN` (Telegram), `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` /
`GEMINI_API_KEY` (AI yordamchi — bittasi yetarli).

```bash
docker compose up -d --build
docker compose ps        # ikkalasi ham «healthy» bo'lishi kerak
```

## 2. Birinchi kirish

`admin` / `1234` bilan kiriladi va tizim **darhol parol so'raydi** —
almashtirmaguningizcha hech qanday API ishlamaydi (403). Bu ataylab:
standart parolli ERP internetda bir kun tursa yetarli.

Avtomatlashtirilgan o'rnatishda `.env` ga `ADMIN_PAROL=...` yozsangiz —
o'sha parol qo'yiladi va majburiy almashtirish so'ralmaydi.

## 3. Sohani tanlash

Sozlamalar → soha profili, yoki AI yordamchidan (o'ng tomondagi ✦
tugmasi) so'rang: «Non zavodimiz bor, kuniga 3000 non yopamiz».
Buyurtma formasi, bosqichlar va retsept shundan keyin o'zi moslashadi —
kodga tegilmaydi.

## 4. HTTPS (nginx)

Ilova 8070-portda, faqat HTTP. Oldiga nginx qo'yiladi:

```nginx
server {
    server_name erp.sizning-domen.uz;
    client_max_body_size 20M;          # mahsulot rasmlari

    location / {
        proxy_pass http://127.0.0.1:8070;
        proxy_set_header Host              $host;
        # Login urinishlarini cheklash IP bo'yicha ishlaydi — bu ikki
        # sarlavhasiz hamma so'rov nginx IP'sidan kelgandek ko'rinadi
        # va bitta odam butun tizimni bloklab qo'yishi mumkin.
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
certbot --nginx -d erp.sizning-domen.uz
```

Postgres porti (5440) **faqat 127.0.0.1** ga bog'langan. Masofadan kerak
bo'lsa SSH tunnel: `ssh -L 5440:127.0.0.1:5440 server`.

## 4b. Eski tizimdan ko'chirish (ixtiyoriy)

Mijozning eski TIZIM ERP bazasi bo'lsa:

```bash
.venv/bin/python tools/kochir.py /yol/zaxira.db --tekshir   # avval sanaydi
.venv/bin/python tools/kochir.py /yol/zaxira.db             # keyin ko'chiradi
```

Manba `mode=ro` bilan ochiladi — **yozish SQLite darajasida imkonsiz**.
Baribir jonli bazaga emas, ZAXIRA nusxasiga qarating.

Ko'chirgandan keyin:

```bash
.venv/bin/python tools/butunlik.py
```

## 5. Zaxira

```bash
crontab -e
0 3 * * * /opt/innasoft/zaxira.sh >> /var/log/innasoft-zaxira.log 2>&1
```

Baza + rasmlar `zaxira/` ga tushadi, 14 kun saqlanadi (`ZAXIRA_KUN` bilan
o'zgartiriladi). **Tiklashni bir marta sinab ko'ring** — sinalmagan
zaxira zaxira emas:

```bash
gunzip -c zaxira/baza-<sana>.sql.gz | docker compose exec -T db psql -U innasoft innasoft
```

## 6. Yangilash

```bash
cd /opt/innasoft && git pull
./zaxira.sh                        # avval zaxira
docker compose up -d --build
```

Migratsiya ishga tushishda o'zi bajariladi (`app/migrate.py`) — ustunlar
faqat QO'SHILADI, hech narsa o'chirilmaydi.

## 6b. Demo ma'lumot (tanishtirish uchun)

```bash
.venv/bin/python tools/demo_data.py --soha non      # bitta soha
.venv/bin/python tools/demo_data.py --hammasi       # 22 soha
```

**Prod bazasida ishlatmang** — demo ma'lumot haqiqiysi bilan aralashadi.

## 7. Kuzatuv

| Nima | Qanday |
|---|---|
| Holat | `curl -fsS localhost:8070/api/health` |
| Loglar | `docker compose logs -f app` |
| Konteynerlar | `docker compose ps` (ikkalasi `healthy`) |
| Baza butunligi | `.venv/bin/python tools/butunlik.py` (oyiga bir marta) |

`/api/health` bazaga haqiqiy `SELECT 1` yuboradi — «web tirik, baza
o'lgan» holatini ham tutadi.

---

## Prod rejimida nima bloklanadi

`MUHIT=prod` bo'lsa quyidagilarda server **ishga tushmaydi** va sababini
aytadi:

- `POSTGRES_PASSWORD` standart qiymatda
- `CORS_ORIGINS=*`
- `SEED_DEMO=1` (prod bazasiga demo ma'lumot)

## Hali qilinmagani

- Ijarachilik (har mijozga alohida baza) — 2-bosqich
- Valyuta (USD narx, qotirilgan kurs)
- Jonli LLM chaqiruvi sinalmagan (haqiqiy kalit bo'lmagani uchun).
  `.env` ga haqiqiy kalit qo'yilsa chat oynasi «tayyor» deb yozadi —
  o'rin egallovchi qiymat (`sk-...`) rad etiladi.
