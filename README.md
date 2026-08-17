# INNASOFT PLATFORMA

**Har qanday biznes uchun ERP.** Mijoz o'z biznesini aytadi — AI tizimni
unga moslab yig'adi. Kod yozilmaydi, konfiguratsiya to'ldiriladi.

22 ta tayyor soha profili bor: non zavodi, beton, mebel, tikuvchilik,
poyabzal, sut, kimyo, avto servis, ulgurji savdo, karton va boshqalar.
Ro'yxatda yo'q soha bo'lsa — AI yordamchi u uchun yangisini yasaydi.

---

## 1. Tez ishga tushirish

Kerak bo'lgani: **Docker** va **Docker Compose**. Boshqa hech narsa.

```bash
git clone <repo> innasoft_platforma && cd innasoft_platforma
cp .env.example .env
docker compose up -d --build
```

Bir-ikki daqiqadan keyin:

```bash
docker compose ps
```

Ikkala qator ham `healthy` bo'lsa — tayyor. Brauzerda oching:

**http://localhost:8070**

Birinchi kirish: `admin` / `1234` — tizim darhol yangi parol so'raydi va
almashtirmaguningizcha hech narsa ochilmaydi.

### Ishlayotganini tekshirish

```bash
curl localhost:8070/api/health
```

`{"holat":"ok","profil":"..."}` qaytsa — hammasi joyida. Bu tekshiruv
bazaga ham murojaat qiladi, ya'ni «web tirik, baza o'lgan» holatni ham
tutadi.

---

## 2. Qanday ma'lumot bilan boshlash

`.env` da bittasini tanlang:

| Rejim | Nima bo'ladi |
|---|---|
| `SEED_EMPTY=1` | Bo'sh baza, faqat `admin`. **Haqiqiy ish uchun shu.** |
| `SEED_DEMO=1` | Karton sexi namunasi — tizim bilan tanishish uchun |

O'zgartirgandan keyin:

```bash
docker compose down -v && docker compose up -d
```

> `down -v` bazani **o'chiradi**. Ma'lumot bo'lsa avval `./zaxira.sh`.

### `tools/` va `tests/` uchun muhit

Quyidagi vositalar Python muhitini talab qiladi. Bir marta yasab olinadi:

```bash
./run.sh          # .venv ni yaratadi va kutubxonalarni o'rnatadi
                  # (Ctrl+C bilan to'xtating — server kerak emas)
```

Shundan keyin `.venv/bin/python tools/...` buyruqlari ishlaydi.
Vositalar Docker'dagi bazaga `DATABASE_URL` orqali ulanadi:

```bash
export DATABASE_URL="postgresql://innasoft:innasoft@localhost:5440/innasoft"
```

> `run.sh` ni serverni doimiy yuritish uchun ishlatmang — u Dockersiz,
> SQLite bilan ishlaydi. Prod yo'li — `docker compose`.

### 22 sohaga demo ma'lumot

Tizimni to'la ma'lumotda ko'rish uchun (qarz yoshi, FIFO, qisman
topshirish — bo'sh bazada bularning hech biri ko'rinmaydi):

```bash
.venv/bin/python tools/demo_data.py --soha non    # bitta soha
.venv/bin/python tools/demo_data.py --hammasi     # 22 soha
```

**Prod bazasida ishlatmang** — demo haqiqiy ma'lumot bilan aralashadi.

### Eski tizimdan ko'chirish

Mijozning eski TIZIM ERP bazasi (SQLite) bo'lsa:

```bash
.venv/bin/python tools/kochir.py /yo'l/zaxira.db --tekshir   # avval sanaydi
.venv/bin/python tools/kochir.py /yo'l/zaxira.db             # keyin ko'chiradi
```

Manba `mode=ro` bilan ochiladi — unga yozish **SQLite darajasida
imkonsiz**. Baribir jonli bazaga emas, ZAXIRA nusxasiga qarating.

---

## 3. AI yordamchi

Yon menyudagi **«AI ёрдамчи»** bo'limi. To'rt xil yordamchi bor va har
biri o'z rolidagi odamga ochiq:

| Yordamchi | Nima qiladi | Kimga |
|---|---|---|
| Sozlash | Biznesingizni so'rab tizimni yig'adi | Rahbar |
| Ombor | Nima qoldi, nima yetmaydi, nima olish kerak | Rahbar, sklad, sex |
| Moliya | Kim qarzdor, pul holati, muddati o'tganlar | Rahbar, buxgalter |
| Buyurtma | Qaysi zakaz qayerda, kechikdimi, narxi qancha | Rahbar, menejer, sex |

### Kalit qo'yish

`.env` ga **bittasi ham, hammasi ham** yozilishi mumkin:

```dotenv
GEMINI_API_KEY=...        # https://aistudio.google.com
ANTHROPIC_API_KEY=...     # https://platform.claude.com
OPENAI_API_KEY=...        # https://platform.openai.com
```

Bir nechta kalit qo'yilsa **hammasi ishlatiladi**: birinchisining
kvotasi tugasa tizim keyingisiga o'zi o'tadi. Tartibni belgilash uchun
`LLM_PROVAYDER=anthropic` yozing — u birinchi turadi, qolganlari zaxira
bo'lib qoladi.

Qaysi kalit ulanganini AI bo'limining o'ng ustunida ko'rasiz:
● ulangan · ○ qo'yilmagan.

Keyin `docker compose up -d --force-recreate app`.

O'rin egallovchi qiymat (`sk-...`) qolib ketsa tizim uni tanib, «kalit
haqiqiyga o'xshamaydi» deb aytadi — «tayyor» deb aldab, keyin xato
bermaydi.

`OPENAI_BASE_URL` orqali OpenAI-mos har qanday xizmat ham ishlaydi:
DeepSeek, Groq, Together, lokal Ollama.

### Bepul kalit haqida

Bepul Gemini tarifida **kuniga 20 so'rov** (har modelga alohida). Agent
bitta savolga 2–3 so'rov yuboradi, ya'ni kuniga **6–8 savol**. Keyin
«xizmat band» chiqadi va ertaga tiklanadi. Jiddiy foydalanish uchun
pullik tarif kerak.

Model kvotasi tugasa tizim zaxira modelga o'zi o'tadi (`ZAXIRA_MODELLAR`).

### AI nima qildi

AI bo'limining o'ng ustunida:
- ulanish holati (qaysi provayder, qaysi model)
- **AI taklifi bilan bajarilgan o'zgarishlar** — audit jurnalidan
- oxirgi suhbatlar

Har javob ostida «⚙ qaysi asbob chaqirilgan» izi turadi — raqam
qayerdan kelgani ko'rinib turadi.

**Muhim qoida:** agent bazaga o'zi hech narsa yozmaydi. O'zgartirish
kerak bo'lsa u **taklif qiladi**, tugmani odam bosadi va audit jurnaliga
ham o'sha odam yoziladi.

---

## 4. Kundalik buyruqlar

```bash
docker compose ps                    # holat
docker compose logs -f app           # loglar
docker compose restart app           # qayta ishga tushirish
docker compose up -d --build         # kod o'zgargandan keyin
docker compose down                  # to'xtatish (baza qoladi)
```

### Zaxira

```bash
./zaxira.sh
```

Baza va rasmlar `zaxira/` ga tushadi, 14 kun saqlanadi. Cron uchun:

```
0 3 * * * /opt/innasoft/zaxira.sh >> /var/log/innasoft-zaxira.log 2>&1
```

Tiklash:

```bash
gunzip -c zaxira/baza-<sana>.sql.gz | docker compose exec -T db psql -U innasoft innasoft
```

**Tiklashni bir marta sinab ko'ring** — sinalmagan zaxira zaxira emas.

### Baza butunligi

```bash
.venv/bin/python tools/butunlik.py
```

14 ta o'zgarmasni tekshiradi: qarz ikki yo'lda bir xilmi, qarz yoshi
bo'laklari jamiga to'g'ri keladimi, ombor partiyalari qoldiqqa mosmi va
hokazo. Hech narsa yozmaydi. Prodda oyiga bir marta.

---

## 5. Sinov

```bash
./sinov.sh
```

To'qqizta to'plam, har biri toza bazada:

```
✅ 124/124 ENDPOINT HIMOYALANGAN      himoya auditi (serversiz)
✅ GenUI — 8 primitiv, 5 amal          komponent tekshiruvi
✅ HAMMA 22 PROFIL SIKLDAN O'TDI       har soha to'liq ishlaydimi
✅ 22 SOHA — HISOB-KITOB TO'G'RI       raqamlar to'g'rimi
✅ KO'CHIRISH — manba tegilmadi        eski bazadan ko'chirish
✅ KARTON REGRESSIYASI                 eski mijoz mantiqi buzilmadimi
✅ 38 endpoint, 0 xato                 modul auditi
✅ JONLI AGENT ISHLAYAPTI              haqiqiy LLM (kalit bo'lsa)
✅ 14 TEKSHIRUV — BAZA BUTUN           to'la demo bazada
```

Har safar to'liq yurgizing: `e2e_test.py` holatga bog'liq (foydalanuvchi
yaratadi, parol almashtiradi), shuning uchun har to'plamdan oldin baza
tozalanadi.

---

## 6. Prodga chiqarish

To'liq yo'riqnoma: **[DEPLOY.md](DEPLOY.md)** — nginx, HTTPS, cron,
yangilash, tiklash.

Eng qisqasi: `.env` ga `MUHIT=prod` yozing. Shunda server xavfli
standart sozlamalar bilan **ishga tushmaydi**:

- `POSTGRES_PASSWORD` standart qiymatda
- `CORS_ORIGINS=*`
- `SEED_DEMO=1` (prod bazasiga demo ma'lumot)

---

## 7. Loyiha tuzilishi

```
app/
  domain.py       soha qatlami — profil, maydon, retsept, ish tartibi
  models.py       baza jadvallari (yadro: sohaga bog'liq emas)
  services.py     biznes-logika: FIFO, tannarx, qarz, QQS, pul oqimi
  genui.py        AI chizadigan komponentlar + tasdiqlanadigan amallar
  agent.py        AI agentlari va ularning asboblari
  llm.py          provayder qatlami (Anthropic / OpenAI / Gemini)
  profiles/*.json 22 soha ta'rifi — MA'LUMOT, kod emas
  modules/*.json  5 ish tartibi (ishlab chiqarish, savdo, xizmat...)
  routers/        HTTP endpointlar

static/js/core/
  soha.js         forma profildan chiziladi
  genui.js        AI komponentlarini chizish

tools/
  kochir.py       eski bazadan ko'chirish (manba faqat o'qiladi)
  demo_data.py    22 sohaga demo ma'lumot
  butunlik.py     bazadagi raqamlar o'zaro mos keladimi

tests/            sinov to'plamlari (sinov.sh hammasini yurgizadi)
```

**Asosiy qoida:** yangi soha qo'shilganda **kodga tegilmaydi** —
`app/profiles/` ga JSON qo'shiladi yoki AI yordamchi uni o'zi yasaydi.
Buyurtma formasi, bosqichlar, retsept va hujjatlar shundan chiziladi.

---

## 8. Strategiya va reja

Loyihaning qayerga borayotgani, qonuniy talablar, arxitektura qarorlari
va bosqichma-bosqich reja — `docs/` papkasida:

| Hujjat | Nima haqida |
|---|---|
| [00-STRATEGIYA.md](docs/00-STRATEGIYA.md) | biz nima qilyapmiz, kim bilan raqobat, qayerdan boshlash |
| [01-HOZIRGI-HOLAT.md](docs/01-HOZIRGI-HOLAT.md) | nima bor, nima yo'q — raqamlar bilan |
| [02-QONUNCHILIK.md](docs/02-QONUNCHILIK.md) | EHF, fiskal kassa, BHMS — majburiy talablar |
| [03-ARXITEKTURA.md](docs/03-ARXITEKTURA.md) | qobiliyatlar, Bosh kitob, ijarachilik |
| [04-AI-VA-RAG.md](docs/04-AI-VA-RAG.md) | agent, RAG quvuri, AI sinovi |
| [05-INTEGRATSIYALAR.md](docs/05-INTEGRATSIYALAR.md) | Payme/Click/Uzum, EHF, telefoniya |
| [06-YOL-XARITASI.md](docs/06-YOL-XARITASI.md) | bosqichlar, vaqtlar, yopilgan qarorlar |
| [07-TARQATISH.md](docs/07-TARQATISH.md) | SaaS qarori, ma'lumot ajratish, AI sarfi, tarif |
| [08-FRONTEND.md](docs/08-FRONTEND.md) | frontend holati va modernizatsiya tartibi |

---

## 9. Hali qilinmagani

- Ijarachilik — har mijozga alohida baza (2-bosqich)
- Valyuta (USD narx, qotirilgan kurs)
- Telegram botda AI (hozir bot faqat buyurtma tasdig'ini yuboradi)
