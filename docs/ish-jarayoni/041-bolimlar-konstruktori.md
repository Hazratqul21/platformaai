# 041 — BO'LIMLAR KONSTRUKTORI + KASSA BOSH KITOBGA

**Sana:** 2026-08-26
**Holat:** ✅ prodda — bilyard 12 bo'lim, karton 15 (tegilmadi)

---

## Muammo (foydalanuvchi ko'rsatdi)

> «Bu karton gofra emas, bu hamma yo'nalishga tushadigan tool.»

Platforma «har biznesga moslashadi» deb qurilgan, lekin moslashish
FAQAT buyurtma formasi darajasida edi. Tizimning SHAKLI — yon menyu,
hisob-kitob — hamon Rustam akaning karton sexiniki edi.

### Beshta aniq nuqson

1. **Menyu kodda qotirilgan.** `static/js/core/router.js` da
   `const NAV=[...]` — 15 bo'lim, faqat ROLga qarab filtrlanadi.
   Bizneslar orasida farq yo'q.
2. **Tizim bilgan narsani ekran bilmaydi.** `modules/xizmat.json` da
   so'zma-so'z «Ombor ishtirok etmaydi» deb yozilgan, menyu esa xizmat
   biznesiga «Ombor», «Materiallar», «Xomashyo xaridi» ni ko'rsatardi.
3. **Konstruktor forma darajasida.** Profil JSON'i maydon/o'lchov/narx
   beradi, tizim shaklini bermaydi.
4. **AI bo'lim yarata olmaydi.** `genui.py` da 5 ta amal bor, ularning
   birortasi ham menyuga tegmaydi. Ya'ni «AI bilan gaplashsin,
   bo'limlar paydo bo'lsin» IMKONSIZ edi.
5. **Bosh kitob faqat ishlab chiqarish zanjirida.** 10 qoida —
   buyurtma, xarid, material, ish haqi. Xizmat biznesi kunini KASSA
   JURNALIDA o'tkazadi, unga qoida yo'q edi. Natija: bilyardda 177
   kassa yozuvi bor, `foyda-zarar` esa `0/0/0`.

---

## Yechim 1 — bo'limlar MA'LUMOT (`app/bolimlar.py`)

Uch qatlam, yuqoridagisi ustun:

```
1. AKKAUNT TANLOVI   settings['bolimlar']         (mijoz yoki AI yozgan)
2. MODUL STANDARTI   modules/<modul>.json         -> bolimlar
3. HAMMASI           yozuv yo'q -> bugungi holat  (15 bo'lim)
```

3-qatlam ATAYLAB: mavjud akkauntlarda hech narsa o'zgarmaydi.

- `KATALOG` — 15 bo'lim, nomi va ikonkasi bilan (endi bitta manba)
- `MAJBURIY` — `dash`, `ai`, `set`, `help` o'chirilmaydi, aks holda
  mijoz tizimga qaytib kira olmaydi
- `GET /api/soha/bolimlar` — faol va nofaol ro'yxat
- `PUT /api/soha/bolimlar` — faqat Rahbar, audit jurnaliga yoziladi
- `router.js` — menyu serverdan, javob kelmasa eski ro'yxat (zaxira)

`modules/xizmat.json` ga `bolimlar` qo'shildi: ombor uchligi yo'q.

**Prodda:** bilyard 12 bo'lim (`wh mat zakup` yo'q), karton 15 —
buzilmadi.

---

## Yechim 2 — kassa jurnali Bosh kitobga

Ikki yangi qoida (`app/hisob/qoidalar.json`, bazada — mijoz
o'zgartira oladi):

| Hodisa | Provodka |
|---|---|
| `kassa_kirim` | Дт **5010** Кассa — Кт **9030** Xizmatdan daromad |
| `kassa_chiqim` | Дт **9420** Ma'muriy xarajat — Кт **5010** Kassa |

- `hisob/ulash.py` → `kassa_yozuvi()` — GL xatosi kassani to'xtatmaydi
- `routers/kassa.py` — yangi yozuv darhol provodkaga tushadi
- `tools/kassa_gl.py` — eski yozuvlarni o'tkazadi (takrorlamaydi)

**BOG'LANGAN YOZUVGA TEGILMAYDI:** mijoz to'lovi va xarid to'lovi
kassaga NUSXA bo'lib tushadi, ularning provodkasi o'z hodisasidan
yozilgan. Ikkinchi marta yozilsa summa Bosh kitobda ikkilanardi.

**Prodda (bilyard):** 177 provodka · daromad 3 200 000 · xarajat
240 756 500 · aylanma qaydnoma debet == kredit ✅

---

## Yo'l-yo'lakay tutilgan nuqson: `--tekshir` YOLG'ON gapirgan

`tools/kassa_gl.py` ning birinchi variantida tekshiruv rejimi
yozuvchi funksiyani chaqirib, oxirida `db.rollback()` qilardi.
Lekin `hisob/xizmat.py` dagi `provodka_yoz()` **o'z ichida
`db.commit()`** qiladi. Ya'ni vosita ekranga «hech narsa yozilmadi»
deb yozdi va o'sha payt prodda **177 provodka yozib qo'ydi**.

Tuzatildi: tekshiruv rejimida yozuvchi funksiya **umuman
chaqirilmaydi**, faqat sanaladi. Sinovda isbotlandi: `--tekshir` 1 ta
«yozilardi» deydi, bazada 0 ta provodka.

> Saboq: `rollback` — commit qiluvchi funksiya ustidan himoya emas.

---

## Diqqat — oldinga qarab o'zgarish

Endi HAR akkauntda kassa jurnaliga qo'lda kiritilgan yozuv Bosh
kitobga ham tushadi. Karton uchun eski 464 yozuv **ko'chirilmadi**
(kitobi o'rtada o'zgarmasin) — faqat yangi yozuvlar tushadi. Xohlansa
`tools/kassa_gl.py` u yerda ham yurgiziladi.

---

## Qoldi (to'liq konstruktor uchun)

1. **AI ga «bo'lim qo'sh / olib tashla» amali** — `genui.py` ga
   tasdiqlanadigan amal; API tayyor, AI tomoni yo'q
2. **Yangi akkaunt top-toza ochilsin** — hozir 30 profil va to'liq
   menyu bilan ochiladi
3. **Sozlamalarda «bo'limlarni yig'ish» ekrani** — AI'siz ham
4. **Rollar ham ma'lumot bo'lsin** — `models.py` da `ROLES` qotirilgan:
   «Sex boshlig'i», «Sklad mudiri» — bilyard klubida bunday lavozim
   yo'q, u yerda «Barmen», «Administrator» kerak

---

## Qo'shimcha (o'sha kuni davomi) — uchta ish bajarildi

### 1. Zaxira va AI limiti prodda

**Zaxira** ikkita nuqson bilan ishlayotgan ekan:
- faqat `innasoft` bazasi olinardi → mijoz bazalari (`inna_billiard`,
  `inna_karton`) va boshqaruv bazasi **zaxirasiz** edi
- rasm zaxirasi **hech qachon ishlamagan**: skriptda volume nomi
  qotirilgan (`innasoft_platforma_...`), prodda esa `innasoft-platforma_...`
  (tire bilan). Skript «o'tkazib yuborildi» deb yozardi va buni hech
  kim sezmasdi

Endi volume nomi topiladi, hamma baza alohida faylga tushadi. Prodda
yurgizildi: **10 fayl** (8 baza + boshqaruv + 5.1 MB rasm).

**AI limiti** prodda isbotlandi: limit 1 so'm qo'yilganda agent **402**
qaytardi, keyin limit 0 ga qaytarildi.

### 2. Kataloglar profildan (`kataloglar` bloki)

Ilgari har akkauntga karton sexining kataloglari quyilardi —
«Kleychi», «Flekso operatori», «Gofrokarton», «Kraxmal kley».
Bilyard klubida ham aynan shular turgan edi.

- `app/seed.py` → `seed_catalogs(db, kataloglar)` endi PROFILDAN oladi
- `Profil.kataloglar` (`app/domain.py`) — yangi maydon
- `karton.json` ga eski ro'yxat ko'chirildi (karton mijozlari
  o'zgarmasin), `bilyard.json` ga o'ziniki qo'shildi
- profilda katalog bo'lmasa — faqat umumiy o'lchov birliklari,
  qolgani **BO'SH** («yangi mijoz kirganda top-toza» talabi)
- `tools/katalog_yangila.py` — ilgari ochilgan akkauntni profiliga
  moslaydi; **ishlatilayotganiga tegmaydi** (lavozim xodimda,
  bo'lim materialda, birlik xaridda tursa — qoldiriladi)

Prodda bilyardda: 29 yozuv olindi, 20 tasi qo'shildi, keyin qolgan
5 ta begona birlik ham tozalandi. Ma'lumot butun (177 kassa yozuvi).

### 3. AI ga pul asboblari

Agentning 12 asbobi ishlab chiqarish zanjiriga qurilgan edi. Xizmat
biznesida AI ko'radigan narsa deyarli yo'q edi — bilyardning 177
yozuvidan faqat yalpi qoldiq ko'rinardi.

Uchta yangi asbob (`Rahbar`, `Buxgalter` uchun):

| Asbob | Nima beradi |
|---|---|
| `kassa_harakati` | kirim/chiqim, oylar kesimi, tur bo'yicha taqsimot |
| `xarajat_tahlili` | tur ulushi foizda, eng katta yozuvlar, oylik dinamika |
| `buxgalteriya_hisoboti` | Bosh kitobdan foyda-zarar va schetlar |

**Turlar birlashtiriladi.** Excel da bir tur to'rt xil yozilgan edi:
«зарплата», «Зарплата», «зарплата · oylik». Ajratib ko'rsatilsa AI
«oylik 30%» deb XATO xulosa chiqarardi — aslida **90.5%**. Endi
kalit kichik harfga keltiriladi va texnik qo'shimcha olib tashlanadi.
Xuddi shunday «Електро енергия» va «електро енергия» birlashdi
(20.4 + 15 = **35.4 mln**).

`tests/agent_rol_test.py` kuchaytirildi: uchala yangi asbob sklad
mudiri va sex boshlig'iga **berilmasligi** nomi bilan tekshiriladi.

**Prodda haqiqiy AI sinovi** (gemini-3.5-flash) — javobi:
eng katta xarajatlar to'g'ri sanaldi va AI o'zi aniqladi:
«ijara, elektr va marketing xarajatlari `зарплата` turiga qo'shilib
ketgan — ularni ajratib yuritishni tavsiya qilaman».

### Yo'l-yo'lakay

- `hisob_test` aynan **10 ta** provodka qoidasi kutardi (men 2 ta
  qo'shdim). Sinov kuchaytirildi: aniq son emas, **kerakli qoidalar
  ro'yxati** tekshiriladi
- `himoya_audit` yangi `/innasoft` endpointini tutdi (korporativ sayt
  ko'rigi) — oq ro'yxatga sababi bilan qo'shildi: **171/171**

---

## 4. AI CHATDAN BO'LIM YARATISH — zanjir yopildi

Foydalanuvchining asosiy talabi: «o'ng tarafdagi AI chat ikonkasini
bosib gaplashsin, shunda bo'limlar paydo bo'lsin».

Ikki qism qo'shildi:

| Nima | Qayerda |
|---|---|
| `bolimlarni_kor` asbobi | `app/agent.py` — AI menyu holatini KO'RADI (yoqilgan/o'chirilgan, majburiylar) · faqat `Rahbar` |
| `bolimlarni_sozla` amali | `app/genui.py` — TASDIQLANADIGAN amal · faqat `Rahbar` · xavfli=True |

Platformaning qoidasi saqlandi: **agent bazaga o'zi yozmaydi** — u
taklif qiladi, tugmani odam bosadi, audit jurnaliga o'sha odam
yoziladi.

### Yo'l-yo'lakay tutilgan nuqson: bo'sh `kirish`

Birinchi jonli sinovda AI to'g'ri tushundi, jadval chizdi va tugma
taklif qildi — lekin `"kirish": {}` bo'sh edi. Tugma bosilsa amal
«Bo'limlar ro'yxati bo'sh» deb rad etardi, foydalanuvchi esa
«ishlamadi» deb qolardi.

Sabab: ko'rsatmada amallar faqat `- nom — izoh` ko'rinishida
sanalardi, KIRISHI umuman tushuntirilmasdi. Ya'ni bu bitta amalning
emas, **hamma amallarning** muammosi edi.

Tuzatildi:
- har amalga `kirish_namuna` qo'shildi (6 tasiga ham)
- `korsatma_matni()` uni ko'rsatmada chiqaradi
- aniq qoida yozildi: «`kirish` maydonini TO'LDIR, bo'sh qoldirsang
  tugma ishlamaydi, qiymatlarni ASBOB javobidan ol — o'ylab topma»

### Prodda isbotlangan zanjir

```
odam:  «bilyard klubimiz, smeta va buyurtmalar kerak emas —
        kassa, moliya, buxgalteriya va mijozlar yetadi»
   ↓
AI:    jadval bilan ko'rsatdi + tugma taklif qildi
       amal: bolimlarni_sozla
       kirish: {"kalitlar": ["dash","ai","set","help",
                             "kassa","fin","hisob","crm"]}
   ↓
tugma: {"ok": true, "xabar": "Menyu yangilandi: ..."}
   ↓
menyu: dash ai set help kassa fin hisob crm
```

Sinovdan keyin bilyard menyusi **profil standartiga qaytarildi**
(12 bo'lim) — tanlovni mijozning o'zi qilsin.

### Qolgani

1. Sozlamalarda «bo'limlarni yig'ish» ekrani (AI'siz, sichqoncha bilan)
   — UI foydalanuvchi hududida
2. Yangi akkaunt 30 profil bilan emas, TOZA ochilsin
3. Rollar ham ma'lumot bo'lsin (`require_roles` 24+ endpointda qotirilgan)

---

## 5. YANGI AKKAUNT TOZA OCHILADI

Ilgari `bazani_toldir` har yangi mijozning bazasiga **30 ta soha
profilini** ko'chirardi. Bilyard klubining bazasida «Beton zavodi»,
«Poyabzal sexi», «Kolbasa sexi» yotardi.

### Yechim: shablon FAYLDA, mijoz bazasida faqat ishlatilgani

- `migrate.profillarni_yukla(db, faqat={...})` — endi tanlab yuklaydi
- `tayyorlash.bazani_toldir` — FAQAT tanlangan sohani yuklaydi
- `routers/soha.py` — `GET /profillar` ikki manbani birlashtiradi:
  mijoz bazasi + platforma shablonlari (`shablon: true` bayrog'i bilan)
- `POST /faollashtirish` — shablon tanlansa uni **o'sha payt** bazaga
  ko'chiradi («kerak bo'lganda yuklash»)
- `agent.py` — `profillarni_kor` va `profilni_oqi` ham ikki manbadan
  o'qiydi (`manba: akkaunt | shablon`), ya'ni sozlash yordamchisi
  namunalar kutubxonasini yo'qotmadi

**Tanlov kamaymadi** — faqat begona ma'lumot mijoz bazasiga yozilmaydi.

### Yangi profil: `umumiy.json`

Soha tanlanmasdan ro'yxatdan o'tish yo'li bor (odam o'z ishini so'z
bilan yozadi, AI keyin yig'adi). Bunday akkaunt ilgari JIMGINA
`karton` ga tushardi — `domain.qayta_yukla` ning zaxira shabloni
karton edi. Ya'ni gilam yuvish xizmati karton maydonlarini ko'rardi.

Endi `umumiy` profil faollashadi: eng kami — mahsulot nomi, miqdor,
qo'lda narx. Kataloglari ham bo'sh (faqat o'lchov birliklari).

### Sinovda isbotlangan

```
soha TANLAMASDAN ro'yxatdan o'tish
  → bazada 1 ta profil (umumiy) · lavozim 0 · bo'lim 0
  → sozlamalarda 31 ta yo'nalish ko'rinadi (1 baza + 30 shablon)
  → «bilyard» faollashtirildi → shablon bazaga ko'chdi, faol bo'ldi
```

Mavjud akkauntlarga (karton, bilyard, mebel) **tegilmadi** — ularning
bazasidagi 30 profil o'z joyida qoladi, faqat ortiqcha va ko'rinmaydi.


---

## 6. ROLLAR MA'LUMOTGA AYLANDI (`app/rollar.py`)

Eng qimmat qism. `models.ROLES` da beshta nom qotirilgan edi —
«Rahbar», «Menejer», «Sklad mudiri», «Sex boshlig'i», «Buxgalter».
Bular karton sexining lavozimlari. Bilyard klubida «Sex boshlig'i»
yo'q, u yerda «Administrator», «Barmen», «Kassir» ishlaydi.

Qiyinligi: rol shunchaki yorliq emas — `require_roles(...)` 24 dan
ortiq endpointda AYNAN shu nomlar bilan yozilgan, AI asboblari ham
shunga bog'langan. Nomlarni erkin o'zgartirsak ruxsat tizimi quladi.

### Yechim: NOM va HUQUQ ajratildi

```
«Barmen»        -> asos: «Menejer»    (Menejer nima qila olsa, shu)
«Administrator» -> asos: «Rahbar»
«Kassir»        -> asos: «Buxgalter»
```

Mijoz O'Z NOMINI qo'yadi, huquq beshta ASOSDAN biriga bog'lanadi.
**Kodda bironta `require_roles` chaqiruvi o'zgarmadi** — tekshiruv
nomni emas, asosni solishtiradi.

Tekshiruv nuqtalari (hammasi bittaga yig'ildi — `rollar.asos()`):

| Joy | Nima |
|---|---|
| `auth.require_roles` | endpoint himoyasi |
| `genui.amalni_bajar` | AI tasdiqlanadigan amallari |
| `routers/orders.py` | buyurtma bosqichini o'tkazish |
| `routers/agent.py` | AI asboblari va agent ruxsati (5 joy) |
| `routers/users.py` | foydalanuvchi yaratishda ruxsat etilgan rollar |
| `bolimlar.toliq` | menyu — pastda alohida izoh |

### Ikkita muhim ehtiyot chorasi

**1. Asos nomlari HAR DOIM ishlaydi.** `asos()` avval «bu beshta
asosdan birimi» deb qaraydi. Shuning uchun akkaunt o'z ro'yxatini
qo'ygandan keyin ham eski `Rahbar` foydalanuvchisi ishlayveradi —
bilyardda aynan shunday tekshirildi.

**2. Rahbar asosidagi rol o'chirilmaydi.** `saqla()` uni majburan
qo'shadi, aks holda akkauntni boshqaradigan odam qolmasdi.

### Menyu va rol nomi

`bolimlar.KATALOG` dagi `rollar` beshta ASOS nomida yozilgan, frontend
esa nomlarni to'g'ridan-to'g'ri solishtiradi (`n.roles.includes(ME.role)`).
«Barmen» hech qayerda uchramas edi va menyu **bo'm-bo'sh** chiqardi.

Yechim: `GET /api/soha/bolimlar` javobida, huquqi yetsa,
foydalanuvchining O'Z nomi `rollar` ro'yxatiga qo'shib yuboriladi.
Frontendga tegilmadi.

### Profil o'z lavozimini aytadi

`bilyard.json` ga `rollar` bloki qo'shildi — yangi bilyard akkaunti
darrov Administrator/Barmen/Kassir bilan ochiladi. Profilda bo'lmasa
beshta standart nom qoladi (karton, mebel — tegilmadi).

### API

- `GET /api/soha/rollar` → `{rollar: [{nom, asos, standart}], asoslar}`
- `PUT /api/soha/rollar` → `{rollar: [{nom, asos}]}` (faqat Rahbar)

### Yo'l-yo'lakay tutilgan nuqson: `settings.value` 200 belgi

Prodda `PUT /rollar` **500** qaytardi:
`value too long for type character varying(200)`.

`Setting.value` VARCHAR(200) edi, endi u yerda JSON saqlanadi
(bo'limlar, rollar). Beshta rol ~205 belgi chiqdi. Bu `bolimlar`
uchun ham yashirin xavf edi (15 kalit ~100 belgi — chegaraga yaqin).

Tuzatildi: ustun `TEXT` ga o'tkazildi + migratsiya qo'shildi
(PostgreSQL uchun `ALTER COLUMN`, SQLite uzunlikni e'tiborsiz
qoldiradi). **7 ta mijoz bazasida** yurgizildi.

### Prodda isbotlangan

```
bilyard: Administrator->Rahbar · Menejer · Barmen->Menejer
         Kassir->Buxgalter · Buxgalter
karton : Rahbar, Menejer, Sklad mudiri, Sex boshlig'i, Buxgalter (tegilmadi)
```

Lokal to'liq sinovda: Barmen kirdi → mijozlarni ko'rdi (Menejer
huquqi), foydalanuvchilarga kira olmadi (403, Rahbar huquqi),
ro'yxatda yo'q rol bilan foydalanuvchi yaratish rad etildi (400).

---

## ⚠️ TOPILGAN, LEKIN TUZATILMAGAN: moliya O'QISH ochiq

Rol sinovi yo'l-yo'lakay boshqa narsani ko'rsatdi. Kassa va moliyada
YOZISH cheklangan, O'QISH esa har qanday kirgan foydalanuvchiga ochiq:

| Endpoint | Himoya |
|---|---|
| `POST /api/kassa` | `require_roles("Rahbar","Buxgalter")` ✅ |
| **`GET /api/kassa`** | `get_user` — **har rol** ⚠️ |
| **`GET /api/kassa/export.xlsx`** | `get_user` ⚠️ |
| **`GET /api/finance/debtors`** | `get_user` ⚠️ |
| **`GET /api/finance/cashflow`** | `get_user` ⚠️ |
| **`GET /api/finance/dashboard`** | `get_user` ⚠️ |

Ya'ni sklad mudiri (yoki bilyarddagi Barmen) menyuda «Касса» ni
ko'rmaydi, lekin `/api/kassa` ni to'g'ridan-to'g'ri chaqirsa oylik,
ijara va butun pul harakatini o'qiy oladi. **Menyuda yashirish —
himoya emas.**

Bu platformaning O'Z niyatiga zid: `agent.py` da moliya asboblari
ataylab cheklangan («Sklad mudiri va sex boshlig'i KO'RMAYDI»).

### ✅ TUZATILDI (foydalanuvchi tasdiqladi)

Har endpoint MENYUDAGI e'lon bilan moslashtirildi:

| Endpoint | Endi |
|---|---|
| `GET /api/kassa`, `/export.xlsx` | `Rahbar`, `Buxgalter` (menyudagi «Касса» bilan bir xil) |
| `GET /api/finance/payments`, `/debtors`, `/cashflow`, `/dashboard` | `Rahbar`, `Buxgalter`, `Menejer` |

**`GET /api/kassa/firms` TEGILMADI** — u faqat filial NOMLARINI
qaytaradi (pul ma'lumoti emas) va `globals.js` da har sahifada
ishlatiladi. Yopilsa filial filtri hamma rol uchun buzilardi.

`GET /api/finance/audit` ham tegilmadi: audit jurnali AI panelida
hamma rolga ko'rsatiladi, uni yopish alohida qaror.

### `himoya_audit` ga IKKINCHI QATLAM qo'shildi

Birinchi qatlam «tokensiz kirib bo'ladimi» deb qaraydi — shuning
uchun bu bo'shliqni umuman ko'rmagan. Endi ikkinchi qatlam bor: PUL
endpointlari ro'yxati sanaladi va ularda `require_roles` borligi
tekshiriladi.

**Sinov haqiqatan tutishi isbotlandi:** `journal` dan qorovul ataylab
olib tashlandi → audit `❌ app/routers/kassa.py: journal — har rolga
ochiq` deb yiqildi, qaytarilgach yana yashil.

```
✅ 173/173 ENDPOINT HIMOYALANGAN
✅ 10/10 PUL ENDPOINTI ROL BILAN YOPILGAN
```

### Prodda tekshirildi

```
Rahbar (admin):   kassa 200 · dashboard 200 · debtors 200 · cashflow 200
Barmen (Menejer): kassa 403 ← ilgari 200 edi
                  dashboard 200 · mijozlar 200 · foydalanuvchilar 403
```

Sinov uchun yaratilgan `sinov_barmen` foydalanuvchisi o'chirildi —
mijoz bazasida faqat `admin` qoldi.
