# INNASOFT — DIZAYN TIZIMI VA UI KARKASI

Bu hujjat dizaynning bitta manbasi. Maqsad: keyin rasm, video, screenshot,
animatsiya yoki yangi modul qo‘shilganda mahsulot turli uslublarga bo‘linib
ketmasin.

## 1. Brend qoidasi

Ikki qatlam bor, ular bir-birini almashtirmaydi:

| Qatlam | Vazifasi | Uslub |
|---|---|---|
| **INNASOFT corporate** | `innasoft.uz`, mahsulotlar, xizmatlar | cream + qora + ultra-violet + lime, editorial |
| **INNA product** | `app.innasoft.uz`, login, ERP | tinch, aniq, ma’lumotga yo‘naltirilgan; corporate ranglari kontrolli urg‘u sifatida |

Ranglarning yagona texnik manbasi: `static/css/brand.css`.

| Token | Qiymat | Qachon |
|---|---:|---|
| `--brand-paper` | `#F7F0EA` | corporate va login fonlari |
| `--brand-ink` | `#090909` | asosiy matn, premium CTA |
| `--brand-violet` | `#5520CF` | mahsulot, muhim qatlam, brand urg‘u |
| `--brand-lime` | `#C9F000` | faqat tasdiq, marker, kuchli urg‘u |
| `--brand-muted` | `#5B5754` | ikkinchi darajali izoh |

**Lime hech qachon uzun matn, fonning katta qismi yoki xato holati uchun
ishlatilmaydi.** U e’tibor nuqtasi, xolos.

## 2. Domen va yo‘nalish xaritasi

```text
innasoft.uz / www.innasoft.uz  → korporativ sayt
app.innasoft.uz                → INNA AI Business Platform
<mijoz>.innasoft.uz            → mijozning shaxsiy ERP ish maydoni
admin.innasoft.uz              → platforma operatori paneli
```

Korporativ saytdagi kartaga faqat manzili mavjud mahsulot uchun tashqi URL
beriladi. Tayyor bo‘lmagan mahsulot hech qachon 404 yoki “tez kunda” sahifaga
yuborilmaydi; u xizmat briefi yoki aloqa bo‘limiga olib boradi.

## 3. Kerakli sahifa karkaslari

| Prioritet | Sahifa | Minimal bloklar | Keyin qo‘shiladigan media |
|---|---|---|---|
| P0 | Corporate bosh sahifa | header, hero, ecosystem, services, process, CTA, footer | hero video / mahsulot screenshots |
| P0 | Kirish | brand, akkaunt konteksti, login forma, product preview | haqiqiy product preview video |
| P0 | Ro‘yxatdan o‘tish | progress, korxona, yo‘nalish, rejim, xulosa | INN/soha kontekst illustratsiyasi |
| P0 | Tizim yig‘ilishi | status, real agent oqimi, chat, ERPga kirish | yengil micro-animation |
| P1 | Platforma kabineti | tarif, AI sarfi, to‘lovlar, yordam | billing diagrams |
| P1 | ERP dashboard | holat, KPI, ishlar, AI tavsiya, bo‘sh holatlar | real customer-safe screenshots |
| P2 | Case studies | muammo, yechim, natija, CTA | loyiha foto/video |

## 4. Qurilishi shart komponentlar

Har komponentda kamida `default`, `hover/focus`, `disabled`, `loading`,
`empty`, `error` holatlari aniqlanadi.

1. **BrandHeader** — corporate nav, mobil menu, active state.
2. **PrimaryButton / SecondaryButton / TextLink** — bitta o‘lcham, focus ring
   va loading holati.
3. **ProductCard** — mavjud mahsulotga URL yoki xizmat briefiga ichki yo‘l.
4. **StatusBadge** — tayyorlanmoqda, muvaffaqiyatli, ogohlantirish, xato;
   rang bilan birga matn va ikonka ham bo‘ladi.
5. **FormField** — label, helper, xato, disabled va password reveal.
6. **WorkspaceContext** — qaysi akkaunt/subdomenga kirilayotgani.
7. **ProductPreview** — faqat `Konseptual interfeys` deb belgilangan statik
   preview yoki aniq `Jonli ma’lumot` belgili real preview.
8. **EmptyState** — bo‘sh ERP ekranlari uchun keyingi aniq amal.
9. **SkeletonState** — yuklanayotgan jadval/karta uchun layout shift bermaydi.
10. **ConfirmDialog** — qaytarib bo‘lmaydigan amallar uchun.

## 5. Asset registry

Asset qo‘shishdan oldin bu jadvalga kiradi. Shunda rasm qayerda ishlatilishi,
egasi va yangilanishi noma’lum qolmaydi.

| Asset | Format / nisbat | Ishlatiladigan joy | Holat |
|---|---|---|---|
| Logo lockup | SVG, dark/light | header, login, favicon | kerak |
| INNA product preview | 16:10 PNG/WebP, 2x | corporate hero, login o‘ngi | keyin haqiqiy screenshot bilan |
| ORDO login preview v2 | 1586×992 WebP, 16:10 | ORDO kirish sahifasi o‘ngi | konseptual, customer-safe; keyin haqiqiy screenshot bilan |
| ERP modul previewlari | 4:3 PNG/WebP, 2x | product cards, case | kerak |
| Customer-safe case media | WebP/MP4 | case study | faqat ruxsat bilan |
| UI icons | SVG, 24px grid | mahsulot va sahifalar | bitta icon set |
| Motion assets | Lottie yoki CSS | bezak, funksiyani bildirmaydi | P2 |

Qoidalar:

- Screenshotlarda haqiqiy mijoz ma’lumoti bo‘lmaydi; demo yoki maskalangan
  ma’lumot ishlatiladi.
- “Live”, “real-time”, “tayyor” kabi so‘zlar faqat haqiqiy ma’lumotga nisbatan
  ishlatiladi.
- Raster rasm WebP/AVIF, logo va ikonka SVG bo‘ladi.
- Har asset uchun mobil crop alohida tekshiriladi.

## 6. Ishlash va adashmaslik quality gate’i

Har yangi UI bo‘lagi merge/rebuild oldidan:

- klaviatura bilan to‘liq ochiladi (`Tab`, `Enter`, `Escape`);
- 360px, 768px, 1280px va 1440px da tekshiriladi;
- loading, xato va bo‘sh holati mavjud;
- CTA haqiqiy manzilga olib boradi;
- faqat rangga tayanib status bildirilmaydi;
- `prefers-reduced-motion` hurmat qilinadi;
- screenshot/mockup aniq belgilangan;
- kontrast normal matnda kamida WCAG AA bo‘ladi;
- API xatosi foydalanuvchiga texnik stack trace ko‘rsatmaydi.

Lokal, ma’lumotga tegmaydigan asset tekshiruvi:

```bash
python3 tools/ui_static_check.py
```

## 7. Keyingi implementatsiya tartibi

1. Brand tokenlarni corporate va login sahifalariga ulash.
2. Header, button, form field, status badge va empty state’ni reusable qilish.
3. Ro‘yxatdan o‘tish va tizim yig‘ilishi ekranini shu komponentlarga ko‘chirish.
4. ERP dashboard va kabinet uchun holatlar dizayni.
5. Haqiqiy screenshot va assetlar qo‘shilishi.
6. Eng oxirida scroll, hover va intro animatsiyalari.

## 8. Real tizim bilan UI contract

Karkasdagi bloklar taxmin emas. Production UIga ko‘chirishdan oldin ular
mavjud backend contracti bilan bog‘lanadi; endpointi yo‘q modulga “tayyor”
ko‘rinish berilmaydi.

| UI bo‘lagi | Real manba | Kim ko‘radi | Dizayn qoidasi |
|---|---|---|---|
| Boshqaruv dashboardi | `GET /api/finance/dashboard` | Rahbar, Menejer, Buxgalter | Haqiqiy KPI, ombor ogohlantirishi va pul oqimi; soxta raqam yo‘q |
| Yon menyu | `GET /api/soha/bolimlar` | akkaunt + rolga qarab | Menu statik emas, mijoz yo‘nalishiga mos; fallback faqat tarmoq xatosida |
| AI yordamchi | `/api/agent/*`, jumladan oqim va faoliyat | server ruxsat bergan rollar | Tavsiya manbasi/izlari va odam tasdig‘i ko‘rinadi; AI yashirin yozmaydi |
| Obuna va AI sarfi | `GET /api/obuna/mening`, `GET /api/obuna/ai-sarf` | faqat Rahbar | Limit, sarf va obuna holati ochiq tushuntiriladi; limit tugashi ERP o‘qishini yopmaydi |
| AI limitini o‘zgartirish | `POST /api/obuna/ai-limit` | faqat Rahbar | Qaytarilishi mumkin bo‘lgan aniq amal va saqlash feedbacki |

Integratsiya tartibi: avval mavjud class/API contracti ustida CSS va state
komponentlari, keyin bitta sahifa uchun minimal JS rendering, undan keyin
role/API xatosi va mobil sinov. Backend endpointi, autentifikatsiya yoki
hisob-kitob faqat UI dizayni uchun o‘zgartirilmaydi.

### Motion gate

- Dashboard navigation, jadval satrlari va klaviatura bilan takror
  bajariladigan actionlar animatsiyasiz qoladi.
- Button press feedback: `transform` bilan 140ms, faqat feedback maqsadida.
- Modal/toast kabi kamdan-kam holatlarda motion alohida qaror va
  `prefers-reduced-motion` varianti bilan qo‘shiladi.
- `transition: all`, `scale(0)`, layout property animatsiyasi va
  touch qurilmada soxta hover ishlatilmaydi.
