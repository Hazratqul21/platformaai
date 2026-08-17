# 8. FRONTEND — hozirgi holat va modernizatsiya

> Qoida: **frontend hozir qayta yozilmaydi.** Avval backend
> arxitekturasi (ijarachilik, Bosh kitob) to'g'rilanadi. Bu hujjat —
> nima qachon qilinishining tartibi.

---

## 8.1 Hozir nima bor

| Ko'rsatkich | Qiymat |
|---|---|
| JS fayllar | 22 ta, vanilla (framework yo'q) |
| Marshrutlash | hash-based (`#/orders`, `#/ai`) |
| Uslub | bitta `style.css` — «Light Liquid Glass» |
| Til | o'zbek (lotin + kirill), rus |
| Mobil | Telegram Mini App to'liq, pastki navigatsiya |
| Multi-firm | foydalanuvchi firmalar orasida almashadi |

**Sahifalar:** `dash` · `orders` · `crm` · `wh` · `hr` · `kassa` ·
`fin` · `ai` · `settings` · `zakup`

**Yadro modullari:** `soha.js` (profildan forma chizadi) ·
`genui.js` (8 primitiv, XSS himoyasi bilan) · `api.js` · `i18n.js`

### Nega vanilla JS yomon qaror emas edi

Loyiha bitta mijoz uchun boshlangan. Framework qo'shish = build
tizimi, bog'liqliklar, versiya muammosi. Vanilla bilan tez borildi va
**ishlaydigan mahsulot chiqdi**. Bu to'g'ri savdo edi.

Endi platforma ko'p mijozli bo'layotgani uchun hisob to'lanadi.

---

## 8.2 Nima og'riyapti

| Muammo | Oqibati |
|---|---|
| 18 ta alohida `<script>` tegi | har sahifa yuklanishida 18 so'rov, tartib muhim, xato beriladi |
| Global scope | funksiya nomlari to'qnashadi, kim kimga bog'liq — ko'rinmaydi |
| Bitta katta `style.css` | o'zgartirish qo'rqinchli — qayerga ta'sir qilishi noma'lum |
| Build yo'q | minifikatsiya, kesh buzish (cache-busting), manba xaritasi yo'q |
| Ofl ayn yo'q | ishlab chiqarish sexida internet uzilsa — ekran bo'sh |
| Test yo'q | backend da 9 to'plam bor, frontendda nol |

---

## 8.3 Tartib — bosqichma-bosqich, qayta yozishsiz

Har qadam **alohida qiymat beradi** va oldingisini buzmaydi.

### F1 — Build tizimi (3–5 kun)

Vite qo'shiladi. 18 ta `<script>` bitta bundlega yig'iladi,
minifikatsiya va kesh buzish paydo bo'ladi.

**Muhim:** kod o'zgarmaydi — faqat `import`/`export` qo'shiladi.
Bir kunda qaytarib bo'ladigan qadam.

**Foyda:** yuklanish tezligi, xato manzili aniq (source map).

### F2 — Modullar (1 hafta)

Global funksiyalar ES modullariga o'tadi. `window.foo` yo'qoladi,
`import { foo } from './core/foo.js'` bo'ladi.

**Foyda:** bog'liqlik ko'rinadi, ishlatilmagan kod topiladi.

### F3 — CSS ajratish (3–5 kun)

`style.css` sahifalar bo'yicha bo'linadi, umumiy qism `core.css` da
qoladi. Ranglar va oraliqlar CSS o'zgaruvchilariga chiqariladi.

**Foyda:** dizayn o'zgartirish xavfsiz bo'ladi. Mijozga brend rangi
berish ham shu yerdan chiqadi (SaaS da kerak bo'ladi).

### F4 — PWA / oflayn (1 hafta)

Service Worker: ilova qobig'i keshlanadi, internet uzilsa oxirgi
ko'rilgan ma'lumot ko'rinadi, yozish navbatga tushadi.

**Nega muhim:** sex va omborda internet beqaror. Ekran bo'sh qolishi
— mijoz uchun «tizim buzildi» degani.

**Chegara:** faqat o'qish oflayn ishlaydi. Moliyaviy yozuvni oflayn
qabul qilib, keyin ziddiyat yechish — alohida katta ish, hozir yo'q.

### F5 — Frontend testlari (1 hafta)

Playwright: asosiy yo'llar — kirish, buyurtma yaratish, to'lov
kiritish, AI ga savol. Har biri bitta test.

**Foyda:** backend o'zgarganda frontend jim buzilmaydi.

### F6 — Framework (SHART EMAS, keyinroq baholanadi)

React/Vue ga o'tish **hozir kerak emas**. F1–F3 dan keyin qayta
baholanadi. Agar F2 dan keyin kod boshqariladigan bo'lsa — o'tilmaydi.

**Qoida:** framework muammoni yechsa qo'shiladi, moda uchun emas.

---

## 8.4 SaaS uchun frontendga qo'shiladigan yangi ekranlar

Ijarachilik bilan birga kerak bo'ladi:

| Ekran | Nima |
|---|---|
| Ro'yxatdan o'tish | telefon/email, tasdiqlash, firma ma'lumoti |
| AI bilan yig'ish sehrgari | 7.4 dagi yo'l — chat ustida, qadamlar ko'rinib turadi |
| Obuna va tarif | joriy tarif, to'lov tarixi, kengaytirish |
| AI sarfi | 7.6 dagi ko'rinish — token, pul, limit, kim ko'p sarflagan |
| Platforma admini | bizga: mijozlar ro'yxati, holat, xato, sarf |

Birinchi ikkitasi — **mijozning birinchi taassuroti**. Ular yaxshi
bo'lmasa, orqadagi 17 ming qator kod ko'rinmaydi ham.

---

## 8.5 Qachon

```
HOZIR (A bosqichi bilan birga):   F1 build · F3 CSS · SaaS ekranlari
KEYIN (B/C bilan parallel):       F2 modullar · F5 testlar
KEYINROQ:                         F4 PWA
BAHOLANADI:                       F6 framework
```

Umumiy: **F1+F3 ≈ 2 hafta**, qolgani bosqichlarga parallel tarqaladi.
