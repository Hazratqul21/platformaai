# 005 — AI QATLAMI

**Sana:** retrospektiv
**Fayllar:** `app/llm.py` (521) · `app/agent.py` (921) ·
`app/genui.py` (400) · `app/routers/agent.py` (271) ·
`static/js/pages/ai.js` (379) · `static/js/core/genui.js` (241)

---

## `llm.py` — provayder-neytral qatlam

Yuqoridagi kod qaysi provayder ishlayotganini **bilmaydi**. U faqat
`javob_ol(xabarlar, asboblar, korsatma)` chaqiradi.

Ichida Anthropic / OpenAI / Gemini uchun uchta moslashtiruvchi.
Xabarlar ichki, provayderdan mustaqil shaklda saqlanadi va yuborish
oldidan o'giriladi.

### Zanjir — kvota tugaganda

```python
ZAXIRA_MODELLAR = {
  "gemini":    ["gemini-2.5-flash", "gemini-3.5-flash-lite", ...],
  "openai":    ["gpt-5-mini", "gpt-4.1-mini"],
  "anthropic": ["claude-sonnet-5", "claude-haiku-4-5-..."],
}
```

Avval o'sha provayderning zaxira modeliga, keyin boshqa provayderga.
Bepul Gemini tarifida `gemini-3.5-flash` kvotasi **nol** — shuning
uchun zanjir amalda kerak bo'ldi, nazariy emas.

### Uchta amaliy muammo va yechimi

**1. `content=None`** — Gemini ba'zan bo'sh javob qaytaradi.
`'NoneType' object has no attribute 'parts'` → 502. Qo'riqlandi.

**2. `thought_signature`** — Gemini 3.x javobida imzo qaytaradi va
keyingi so'rovda uni **echo qilishni talab qiladi**. Model suhbat
o'rtasida almashsa 400 xatosi. **Yechim:** model turn boshida
qotiriladi (`qotirilgan_model`).

**3. `MALFORMED_FUNCTION_CALL`** — sxema yoki imzo aybdor deb
o'ylandi. Alohida probe bilan tekshirildi: izolyatsiyada `STOP`
qaytdi, ya'ni **sxema aybdor emas**. Haqiqiy sabab — javob hajmi.
Yechim: token byudjeti oshirildi, asboblarga `nechta` parametri,
umumiy hajm chegarasi va qisqartirish bilan qayta urinish.

> Bu **yo'q qilinmagan, yumshatilgan** — halol aytiladi.

**4. `kalit_shubhali()`** — `.env` da `sk-...` kabi o'rin egallovchi
qolib ketsa tanib oladi. Aks holda tizim «kalit bor» deb aldab,
keyin tushunarsiz xato berardi.

---

## `agent.py` — agentik halqa

`suhbat_oqim()` — generator:

```
{"tur": "qadam"} → {"tur": "asbob"} → {"tur": "asbob_ok"}
→ ... → {"tur": "yakun"}
```

Frontend har qadamni **jonli ko'rsatadi** — foydalanuvchi AI nima
qilayotganini ko'rib turadi, «o'ylayapti...» degan qora quti emas.

### To'rt agent — nega bitta emas

| Agent | Asboblar | Kimga |
|---|---|---|
| sozlash | 6 ta (profil yasash) | Rahbar |
| ombor | 3 ta | Rahbar, sklad, sex |
| moliya | 3 ta | Rahbar, buxgalter |
| buyurtma | buyurtma asboblari | Rahbar, menejer, sex |

**40 asbob bitta agentga berilsa model qaysi birini chaqirishni
chalkashtiradi va aniqlik tushadi.** Bu amalda tekshirilgan, nazariy
emas.

Har agent = tizim ko'rsatmasi + asboblar qismi + rol cheklovi.
Yangi agent qo'shish arzon, chunki halqa bitta.

### Raqamlar bitta manbadan

Moliya asboblari `services.debt_aging` / `client_balance` ni
chaqiradi. Bir vaqtlar agentning o'z formulasi bor edi va **AI
1 457 mln, ekran 853 mln** ko'rsatgan edi. Endi ikkalasi bir joydan
oladi.

### Hajm qo'riqchisi

`MAX_ASBOB_JAVOBI = 12 000`. Oshsa `_javobni_qisqartir()` uzun
ro'yxatlarni ikki barobar qisqartiradi va modelga qisqaroq javob
so'rash ko'rsatmasi qo'shiladi.

---

## `genui.py` — model chizgan interfeys

**Asosiy g'oya: komponent MODUL bo'yicha emas, MA'LUMOT SHAKLI
bo'yicha.**

Agar «buyurtma kartasi», «mijoz kartasi», «material kartasi» deb
yozilsa — har yangi bo'limga yangi komponent kerak bo'lardi va
konstruktor g'oyasi buzilardi.

**8 primitiv:** `jadval` · `korsatkichlar` · `tafsilot` ·
`taqsimot` · `profil_oynasi` · `tasdiq` · `hujjat` · `ogoh`

Ular bilan **istalgan** bo'lim ko'rsatiladi — mavjudi ham, AI
kelajakda yasaydigani ham.

### Model — ishonchsiz manba

Komponent modeldan keladi. Shuning uchun `tekshir()`:

- `MAX_KOMPONENT=6`, `MAX_QATOR=60`, `MAX_USTUN=8`, `MAX_MATN=300`
- `hujjat` da faqat `/api/` havolalar qoladi (tashqi havola —
  fishing yo'li)
- frontendda hamma matn `textContent` bilan qo'yiladi,
  **`innerHTML` ishlatilmaydi**

`tests/genui_test.py` aynan buzuq va xavfli komponentlarni yuboradi.

### Tasdiq qoidasi — o'zgarmaydi

> **AI bazaga o'zi hech narsa yozmaydi.** Taklif qiladi → odam tugma
> bosadi → audit jurnaliga **odam** yoziladi.

5 amal: `profilni_faollashtir` · `buyurtma_maqomi` ·
`mijozni_bloklash` · `kredit_limiti` · `eng_past_qoldiq`

`_buyurtma_maqomi` → `routers.orders.set_status` ni chaqiradi.
Ombor yechish qoidasi ikki joyda bo'lmasligi uchun.

---

## Oqim — NDJSON

`POST /api/agent/oqim` → `StreamingResponse`, har qadam bitta JSON
qator. Frontendda `response.body.getReader()`.

**Nega SSE emas:** SSE `GET` talab qiladi, savol matni esa uzun
bo'lishi mumkin va URL ga sig'maydi.

To'xtatish `AbortController` bilan.

---

## Qoldi (C bosqichi)

- RAG — hozir AI qonunchilikni bilmaydi
- Xotira — har suhbat noldan boshlanadi
- Ko'p qadamli reja — hozir bir qadamli
- Oltin to'plam sinovi — 50+ savol, raqam tekshiruvi
