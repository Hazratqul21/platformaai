# 038 — Kirish oqimi: palitra, sehrgar va tizim yaratilish ekrani

Sana: 2026-08-22 · Bosqich: kirish tajribasi · Holat: bajarildi
(intro ekrani qoldi)

## Nima qilindi

Yangi mijozning birinchi daqiqasi qayta qurildi:

    intro → sehrgar (INN → yo'nalish → suhbat) → TIZIM YIG'ILISHI → ERP

Ilgari odam ro'yxatdan o'tgach darrov bo'sh ERP ga tushardi: chapda
14 ta bo'lim, o'rtada bo'sh jadval, nimadan boshlashni bilmaydi.

## 1. Palitra sayqallandi

Ranglar hira va to'yinmagan ko'rinardi. Taxmin qilinmadi, o'lchandi:

| | Oldin | Keyin |
|---|---|---|
| urg'u | `#7C7FF0` (yorqinlik 71%) | `#5B5FE6` (63%) |
| oq matn urg'uda | **3.41** | **4.97** |
| `--primary-deep` oq fonda | 4.84 | 7.93 |
| `--ink-3` oq fonda | 4.13 | 4.85 |
| fon | `#EAEDF8` tekis | rangli, ikki nurli |

Oq matn urg'u rangida 3.41 edi — WCAG AA uchun 4.5 kerak. Ya'ni bu
faqat «chiroyli emas» masalasi emas, tugmalardagi yozuv me'yordan
past edi.

Rang OILASI o'zgarmadi (H≈237). CSS/JS/HTML da qotirib yozilgan
31 ta eski rang kodi ham almashtirildi — aks holda yarmi eskicha
qolardi.

## 2. Ro'yxatdan o'tish sehrgari

Bitta uzun forma o'rniga uch qadam. Uzun formani odam ko'rib qo'rqadi.

**1-qadam — INN.** `app/platforma/inn.py` provayder adapteri.
Manzil va kalit admin panelidan sozlanadi (`platforma_sozlamalar`
jadvali). Kalit KODDA yozilmaydi va API orqali to'liq qaytarilmaydi
— faqat oxirgi 4 belgisi (bot tokeni bilan bir naqsh).

Javob shakli turlicha bo'lgani uchun (`name`, `shortName`, `nomi`…)
adapter ehtimoliy nomlar bo'yicha qidiradi — provayder almashganda
kod o'zgarmasin.

**YO'L HECH QACHON BERKILMAYDI.** INN topilmadi, xizmat javob
bermadi, cheklovga urildi — hech biri xato emas. Endpoint 4xx
qaytarmaydi, forma qizil ko'rsatmaydi, odam nomini o'zi yozadi.
Sabab: ro'yxatdan o'tish tashqi xizmatga bog'lanib qolmasin —
xizmat yiqilsa bizning sotuvimiz to'xtaydi.

**Kvota himoyasi.** `/inn/{inn}` ochiq bo'lishi SHART (odam hali
tokensiz), lekin u pullik xizmatga boradi. Cheklovsiz qoldirilsa
oddiy skript bir kechada kvotani yoqib yuboradi va ertalab haqiqiy
mijoz ro'yxatdan o'ta olmaydi. IP bo'yicha soatiga 30 ta.

**2-qadam — yo'nalish.** 29 chip + qidiruv. Ro'yxatda bo'lmasa odam
o'z so'zi bilan yozadi (`soha_matni`) — matn rad etilmaydi, saqlanadi
va suhbatning birinchi kontekstiga aylanadi.

**3-qadam — xulosa va rejim.** Agent (darrov qiladi) yoki Plan
(avval reja).

## 3. Tizim yaratilish ekrani

`?qur=1` bilan kelgan odam ERP ga EMAS, shu ekranga tushadi.

- **Chapda** qurilish tasmasi: agent asbob chaqirgan sari kartochka
  paydo bo'ladi. Tepada qarama-qarshi aylanadigan ikki gayka.
- **O'ngda** AI suhbati — ERP dagi bilan AYNI panel. Ikkinchi chat
  yozilmadi: bitta joyda tuzatilsa, ikkalasida ham tuzaladi.

Tasma o'ylab topilgan animatsiya EMAS. U `.agent-iz` (chaqirilgan
asboblar) ni kuzatadi — agent hech narsa qilmasa, chapda ham hech
narsa chiqmaydi. Ko'rsatilayotgan narsa haqiqiy ishning aksi.

**Ovoz** WebAudio bilan yasaladi, fayl yo'q: mp3 ~20 KB, uni yuklash
kerak, keshdan chiqadi, avtoijro bloklanishi mumkin. Bu yerda ikkita
sinus to'lqin. Brauzer ruxsat bermasa jimgina o'tkazib yuboriladi.
O'chirib qo'yish tugmasi bor.

## Fayllar

- `static/css/style.css` — palitra, `.rx-*`, `.qur-*`
- `static/js/core/royxat.js` — YANGI, sehrgar
- `static/js/core/qurish.js` — YANGI, yaratilish ekrani
- `static/js/core/lending.js` — eski forma olib tashlandi (228→87)
- `static/js/core/router.js` — `enterApp` avval qurish ekranini tekshiradi
- `app/platforma/inn.py` — YANGI, provayder adapteri + cheklov
- `app/platforma/models.py` — `PlatformaSozlama`
- `app/platforma/xizmat.py` — `sozlama_yoz` / `sozlama_oqi`
- `app/routers/royxat.py` — `/inn/{inn}`, yangi maydonlar
- `app/routers/admin.py` — `/sozlamalar`, `/sozlama/{kalit}`

## Tekshiruv

Jonli serverda, haqiqiy LLM bilan:

- Himoya auditi: **168/168** (12 tasi ataylab ochiq)
- Cheklov: 35 so'rovdan 5 tasi to'xtatildi, boshqa IP bloklanmadi
- INN ulanmagan holat: `{"topildi":false,"qolda":true}`, HTTP **200**
- Sehrgar: 1-qadam 8 maydon, 2-qadam 29 chip + qidiruv
  («ijara» → 1 mos), 3-qadam xulosa + ikki rejim
- **Shablonsiz yo'nalish sinovi:** `gilamservis` akkaunti «gilam
  yuvish xizmati» matni bilan ochildi. Agent 6 ta asbob chaqirib
  `gilam_yuvish` profilini YASADI — maydonlar «Maydoni (kv.metr),
  Gilam turi, Xizmat turi», bosqichlar «Qabul qilindi → Yuvilmoqda →
  Quritilmoqda → Tayyor → Egasiga topshirildi», sinov buyurtmasi
  2 gilam / 12 m². Chapda 6 kartochka paydo bo'ldi, «Tizimga kirish»
  ochildi va ERP shu profil bilan ishga tushdi.

## 4. Intro ekrani

Scroll bilan ochiladigan bo'limlar, jonli kadr, uch qadam ko'rgazmasi.

**VIDEO EMAS, JONLI KADR.** Brauzer kadri ichida haqiqiy interfeys
elementlari CSS bilan harakatlanadi: gayka aylanadi, kartochkalar
navbat bilan chiqadi, chatda «yozmoqda» nuqtalari va javob paydo
bo'ladi. Nega video qo'yilmadi:

- video fayl 2–5 MB, mobil internetda sahifani sekinlashtiradi
- avtoijro ko'p brauzerda bloklanadi (ovozsiz bo'lsa ham)
- video ESKIRADI — interfeys o'zgarsa qayta yozish kerak

Kadrdagi ranglar palitra o'zgaruvchilaridan keladi, ya'ni interfeys
o'zgarsa kadr ham o'zgaradi. Haqiqiy video qo'yilsa
`.lnd-kadr-ekran` ichiga tushadi.

Kadr ko'rsatayotgan narsa o'ylab topilgan emas: bu aynan
`gilamservis` akkauntida bo'lgan haqiqiy yozuv.

### Ochilish animatsiyasi — BEZAK, SHART EMAS

Avval `[data-korin]{opacity:0}` deb yozildi va ochilish butunlay
`IntersectionObserver` ga bog'liq edi. Brauzerda sinovda kuzatuvchi
**umuman ishga tushmadi** — hatto boshlang'ich chaqiruv ham
bo'lmadi — va butun intro sahifasi **BO'SH** ko'rindi.

Tuzatildi: kontent standart holatda KO'RINADI. Yashirish faqat JS
kuzatuvchini muvaffaqiyatli o'rnatgach qo'yiladi (`.korin-yoniq`).
Ustiga 1.5 soniyalik xavfsizlik taymeri — birorta bo'lim ochilmagan
bo'lsa, majburan ochiladi.

Qoida: bezak ishlamasa, kontent yo'qolmasligi kerak.

`prefers-reduced-motion` hurmat qilinadi — vestibulyar buzilishi bor
odam uchun bu tibbiy masala, bezak emas.

### Eskirgan raqamlar tuzatildi

Sarlavhada «22 soha» va chiplar ro'yxati JS da qotirib yozilgan edi
(izohda «API yopiq» deb asoslangan — lekin `/api/platforma/sohalar`
endi ochiq). Natijada 29 yo'nalishdan 22 tasi ko'rinardi. Endi
ikkalasi ham backenddan; qo'ldagi ro'yxat faqat so'rov yiqilganda
ishlatiladigan zaxira.

«Ochiq gapiramiz» bo'limi ham yangilandi: Bosh kitob va ombor
harakati endi «bor» tomonda. Halollik ikki tomonlama — yo'q narsani
va'da qilmaslik ham, bor narsani kamsitmaslik ham.

## Qoldi

- INN provayderining haqiqiy manzili va kaliti — siz kiritasiz
- Admin panelida sozlamalar ekrani (backend tayyor, UI qoldi)
- `gilamservis` va `sinovijara` — sinov akkauntlari
