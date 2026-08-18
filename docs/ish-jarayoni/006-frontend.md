# 006 — FRONTEND

**Sana:** retrospektiv
**Fayllar:** `static/` — 25 fayl, 4 435 qator

---

## Nima qilindi

Vanilla JS SPA, hash marshrutlash, «Light Liquid Glass» dizayni,
uch til, Telegram Mini App.

---

## Nega framework yo'q

Loyiha **bitta mijoz** uchun boshlangan. Framework qo'shish = build
tizimi + bog'liqliklar + versiya muammosi. Vanilla bilan tez borildi
va **ishlaydigan mahsulot chiqdi**.

Bu o'sha paytda to'g'ri savdo edi. Endi platforma ko'p mijozli
bo'layotgani uchun hisob to'lanadi — [../08-FRONTEND.md](../08-FRONTEND.md).

---

## `core/soha.js` — frontend ham konstruktor

Eng muhim frontend fayli. Buyurtma formasini **`/api/soha/joriy`
javobidan chizadi**:

```
sohaFormaHtml()  → maydonlarni profildan chizadi
sohaFormaOl()    → forma qiymatlarini yig'adi
sohaTekshir()    → majburiy maydon, chegara
sohaQadamlar()   → status bosqichlari
sohaMano()       → status ma'nosi (nomi emas)
```

**Natija:** yangi soha qo'shilganda JS ga tegilmaydi. Agar bu
qilinmaganida, har profil uchun alohida forma yozilardi va
«AI tizim yasab beradi» va'dasi frontendда uzilardi.

---

## `core/genui.js` — model chizgan komponent

8 primitivni chizadi. **Qat'iy qoida: model matnini `innerHTML`
bilan qo'yish taqiqlanadi**, faqat `textContent`. Aks holda model
(yoki model orqali o'tgan ma'lumot) sahifaga skript kirita olardi.

---

## `pages/ai.js` — AI ish maydoni

- oqimli yuborish, `AbortController` bilan to'xtatish
- jonli o'tgan vaqt hisoblagichi
- asbob nomlari odam tiliga o'giriladi (`AI_ASBOB_MATNI`)
- o'ng ustun: ulanish holati, qaysi kalit ulangan (● / ○),
  **AI taklifi bilan bajarilgan o'zgarishlar** (audit jurnalidan)

Oxirgisi «AI hozir nima qilyapti va nima qildi» degan savolga javob.

---

## Boshqa yechimlar

**Uch til** — o'zbek lotin, o'zbek kirill, rus. `DICT` + `t()`.
Kirill kerak, chunki ko'p korxonada shu ishlatiladi.

**Ko'p firma** — bitta foydalanuvchi bir necha sex/firma orasida
almashadi (`setFirm`, `firmBanner`).

**Telegram Mini App** — `IS_TG` bilan aniqlanadi, mobilda pastki
navigatsiya.

**Rasm** — yuborishdan oldin brauzerda kichiklashtiriladi
(`rasmniKichiklashtir`). Sexdagi telefondan 5 MB rasm yuborilsa
sekin internetda ish to'xtaydi.

---

## Ochiq muammolar

| Muammo | Holat |
|---|---|
| 24 ta `<script>` tegi | F1 (Vite) |
| Global scope | F2 |
| Bitta `style.css` (402 qator) | F3 — katta emas, yengil ish |
| Oflayn yo'q | F4 |
| Test yo'q | F5 |

Tartib va sabab: [../08-FRONTEND.md](../08-FRONTEND.md).
