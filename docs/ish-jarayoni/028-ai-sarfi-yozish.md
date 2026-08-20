# 028 — AI SARFINI YOZISH (ai_sarf ulandi)

**Sana:** 2026-08-20
**Holat:** ✅ ishlaydi — admin/kabinetda haqiqiy AI sarfi

---

## Muammo

AI ishlardi, lekin `ai_sarf` jadvaliga YOZMASDI — admin/kabinet
panelda sarf har doim 0 ko'rinardi. «AI xarajati mijozdan alohida»
xususiyatining o'lchov qismi yo'q edi.

---

## Yechim — ikki qism

### 1. `llm.py` — token sonini qaytaradi

Har provayder javobi endi `kirish_token` + `chiqish_token` beradi:
- Anthropic: `usage.input_tokens` / `output_tokens`
- OpenAI: `usage.prompt_tokens` / `completion_tokens`
- Gemini: `usage_metadata.prompt_token_count` / `candidates_token_count`

`getattr(..., 0)` bilan — usage yo'q bo'lsa 0, yiqilmaydi.

### 2. `agent.py` — har qadamda yozadi

`_ai_sarf_yoz(javob, agent, user_login)` — halqada har LLM
chaqiruvidan keyin (har qadam o'z tokenini sarflaydi):
- `tenancy.joriy()` dan akkauntni oladi
- boshqaruv bazasidagi `ai_sarf` ga `px.sarf_yoz` bilan yozadi
- narx O'SHA PAYTDAGI stavkada QOTIRILADI (009-qadam naqshi)

**QOIDA:** sarf yozish xatosi AI javobini TO'XTATMAYDI (`try/except`).
Sarf yozilmasa ham foydalanuvchi javobsiz qolmasin. Ijarachiliksiz
rejimda (akkaunt yo'q) — o'tkazib yuboriladi.

---

## Isbot

karton.innasoft.uz da AI so'rovi (moliya agenti) → admin panel:

```
platforma jami: 406.63 so'm, 3 so'rov
  karton: 406.63 so'm (3 so'rov)
```

3 so'rov = agent halqasining 3 qadami (qarzdorlar → qarzdorlar →
korsat). Har biri alohida yozildi. Gemini flash narxida realistik.

Endi kabinet (egasi) va admin (biz) haqiqiy AI xarajatini ko'radi —
limit va hisob shundan ishlaydi.

---

## Regressiya

himoya_audit 156/156.

---

## Qoldi (AI sarf bilan bog'liq)

- Kabinet frontendida AI sarfini ko'rsatish (endpoint tayyor)
- Limit tugaganda AI to'xtashini jonli sinash
