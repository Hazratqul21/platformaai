# 037 — Yangi yo'nalishlar, ro'yxatdan o'tish va sinovda topilgan 5 nuqson

Sana: 2026-08-22 · Bosqich: to'liq tekshiruv · Holat: bajarildi

## Nima qilindi

To'liq sinov to'plami yurgizildi (Docker nihoyat lokalda ishladi),
7 ta yangi faoliyat yo'nalishi qo'shildi, ro'yxatdan o'tish oqimi
qayta yozildi. Sinov 5 ta HAQIQIY nuqsonni ochdi — hammasi tuzatildi.

## Topilgan nuqsonlar

### 1. Sinov to'plami ESKI kod ustida yurar ekan

`sinov.sh` `docker compose up -d` qilardi — `--build` siz. Ya'ni
oxirgi yig'ilgan obraz ishlatilardi. 2026-08-22 da o'sha obrazda
`app/routers/hisob.py` UMUMAN YO'Q edi: buxgalteriya endpointlari 404
qaytarardi, sinov esa «✅ o'tdi» deb ko'rsatardi.

Sinov eski kodni tekshirsa, u sinov emas. `--build` qo'shildi.

### 2. «Bosh kitob ulash» sinovi hech qachon yurmagan

`gl_ulash_test.py` to'g'ridan-to'g'ri `ADMIN_PAROL` bilan kirardi,
toza bazada esa admin «1234» bilan QULFLANGAN va avval parol
almashtirilishi kerak. Har safar 401 olib, jimgina chiqib ketardi.
`profil_test.py` dagi tartib ko'chirildi.

### 3. Rol cheklovini chetlab o'tish (himoya nuqsoni)

034 da to'rt agent bitta «yordamchi» ga birlashtirildi va himoya
AGENT darajasidan ASBOB darajasiga ko'chirildi. Lekin eski kalitlar
(«moliya», «ombor») ko'rsatmani tahrirlash uchun `AGENTLAR` da qoldi
— va yangi filtr FAQAT `yordamchi` ga tegdi.

Natija: **sklad mudiri `agent: "moliya"` deb yuborsa, moliya
asboblarini to'liq olardi** — qarzdorlar ro'yxati, pul holati.

Ikki qatlamli tuzatish:
- `_agent_ruxsatini_tekshir()` — marshrutizatorda 403
- `suhbat_oqim` da asboblar HAR DOIM rol bilan kesishtiriladi —
  birinchi qatlamdan o'tib ketilsa ham model taqiqlangan asbobni
  ko'rmaydi

Bu nuqsonni faqat jonli LLM kaliti bo'lgan sinov ushlagan edi.
Kalitsiz muhitda jimgina o'tib ketardi — shuning uchun
`tests/agent_rol_test.py` yozildi (serversiz, kalitsiz).

### 4. `Decimal < str` — chegara solishtiruvi

`kasr` maydonda qiymat `Decimal`, chegara esa JSON dan satr bo'lib
kelardi (`"min": "0"`). Solishtirganda TypeError — butun soha ishdan
chiqardi, xato esa faqat kimdir buyurtma kiritganda chiqardi.

Bu shunchaki mening yozuv xatoyim emas: profillar admin panelidagi
konstruktordan tahrirlanadi, ya'ni odam ham maydonchaga «0» deb
yozsa aynan shu holat yuzaga keladi. Shuning uchun ma'lumotda emas,
`Maydon._chegara()` da to'g'rilandi.

### 5. Matn shablonlarida `{qty}` ishlamasdi

Retsept formulalarida `qty` bor edi ("ogirlik_g * qty / 1000"), matn
shablonlarida yo'q. Ikki joyda ikki xil qoida. Profilda «{qty} kun»
deb yozilsa, `_tuldir` uni «yo'q maydon» deb butun bo'lakni TASHLAB
yuborardi — ijarada o'lcham matni bo'sh chiqdi, ombor xizmatida esa
«m³» jimgina yo'qoldi.

`soha_hammasi()` ga `qty` qo'shildi. Kasrsiz sohada u butun songa
keltiriladi — «7.0 kun» emas, «7 kun».

## Yangi yo'nalishlar (22 -> 29)

| Kalit | Nom | Modul | Nega |
|---|---|---|---|
| `ijara` | Ijara (texnika, uskuna, joy) | xizmat | so'ralgan |
| `elektrik` | Elektr montaj va xizmati | qurilish | so'ralgan |
| `hujjat_aylanishi` | Hujjat aylanishi va konsalting | xizmat | so'ralgan |
| `talim_markazi` | Ta'lim markazi (kurslar) | xizmat | LMS yo'nalishi |
| `ombor_xizmati` | Ombor xizmati (mas'ul saqlash) | xizmat | WMS yo'nalishi |
| `gozallik` | Go'zallik saloni | xizmat | keng tarqalgan |
| `umumiy_ovqatlanish` | Umumiy ovqatlanish | ishlab_chiqarish | retseptli |

Hammasi to'liq sikldan o'tdi (`profil_test`) va raqamlari tekshirildi
(`chuqur_sinov`). Birlik ziddiyati yo'q.

## Ro'yxatdan o'tish oqimi

**Ro'yxat backenddan.** Ilgari `static/js/core/lending.js` ichida
QO'LDA yozilgan massiv turardi. Yangi profil qo'shilganda uni JS da
ham yozish esdan chiqardi va yo'nalish ro'yxatda ko'rinmasdi — ya'ni
yozilgan soha mijozga yetib bormasdi. Yangi ochiq endpoint:
`GET /api/platforma/sohalar`. Manba bitta: `app/profiles/*.json`.

**Qidiruv.** 29 ta yo'nalish oddiy ro'yxatda ko'p. Qidiruv maydonchasi
qo'shildi, tanlangani filtr o'zgarganda saqlanadi, ostida soha izohi
ko'rinadi.

**AI bilan sozlash.** «Sozlash yordamchisi» tizimni mijozning ishiga
moslash uchun yozilgan edi, lekin unga YO'L yo'q edi — yangi kelgan
odam bo'sh ERP ni ko'rib, nimadan boshlashni bilmasdi. Endi
ro'yxatdan o'tish oxirida «AI bilan sozlashni boshlash» tugmasi bor:
u `?sozlash=1` bilan akkauntga olib boradi, kirgandan keyin AI paneli
o'zi ochiladi va sozlash suhbati boshlanadi. Belgi darrov URL dan
olib tashlanadi, aks holda har yangilashda qaytadan ochilaverardi.

## Fayllar

- `sinov.sh` — `--build`, yangi sinov ulandi
- `tests/gl_ulash_test.py` — kirish tartibi
- `tests/agent_rol_test.py` — YANGI
- `tests/himoya_audit.py` — `/sohalar` ochiq ro'yxatga
- `app/routers/agent.py` — `_agent_ruxsatini_tekshir`
- `app/agent.py` — asboblar rol bilan kesishtiriladi
- `app/domain.py` — `_chegara()`, `soha_hammasi` da `qty`
- `app/routers/royxat.py` — `GET /sohalar`
- `app/profiles/*.json` — 7 ta yangi
- `static/js/core/lending.js`, `static/js/core/router.js`

## Tekshiruv

Jonli serverda, haqiqiy ma'lumot bilan:

- `GET /api/platforma/sohalar` -> 29 yo'nalish
- Ro'yxatdan o'tish formasi: qidiruv «elektr» -> 2 ta mos
  (Elektr montaj, Kabel/elektrotexnika); izoh ko'rinadi
- `sinovijara` akkaunti ochildi, ijara profili faollashdi
- Ijara buyurtmasi: 7 kun x 1 500 000 -> o'lcham matni
  **«7 kun, kunlik 1500000 so'm»** (ilgari bo'sh edi)
- `?sozlash=1` -> kirgandan keyin AI paneli ochildi, agent «sozlash»,
  salom chiqdi
- Sozlash yordamchisiga biznes aytildi -> u `modullarni_kor`,
  `profillarni_kor`, `profilni_oqi` asboblarini chaqirib, ijara
  profilini o'qidi va mazmunli savol berdi
- Rol cheklovi: sklad mudiri + moliya -> 403; asboblar kesishmasi
  bo'sh

## Qoldi

- `sinovijara` sinov akkaunti — kerak bo'lmasa o'chiriladi
- Jonli agent sinovi ba'zan tarmoq sababli yiqiladi
  (SSL EOF / server disconnected) — kod muammosi emas
- Yangi 7 yo'nalish uchun demo ma'lumot naqshlari kengaytirilishi
  mumkin
