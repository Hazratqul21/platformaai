# 002 — SOHA QATLAMI (loyihaning asosiy g'oyasi)

**Sana:** retrospektiv
**Fayllar:** `app/domain.py` (626) · `app/profiles/*.json` (22) ·
`app/modules/*.json` (5)

---

## Nima qilindi

Karton sexi uchun yozilgan ERP dan **soha bilimini kodidan ajratib**,
ma'lumotga (JSON) chiqarish. Natija: 22 soha bitta kod bilan ishlaydi,
yangi soha qo'shish uchun kod yozilmaydi.

Bu — butun loyihaning asosi. Qolgan hamma narsa shundan kelib chiqadi.

---

## Ajratishning mohiyati

```
YADRO (kod — sohani BILMAYDI)      SOHA (ma'lumot — JSON)
─────────────────────────────      ──────────────────────
pul, ombor, mijoz, xodim           qaysi maydonlar bor
hujjat, rol, formula, kassa        qanday retsept
models.py · services.py            bosqichlar, matnlar
```

`Order` jadvali `attributes` ni **saqlaydi, ko'rsatadi, eksport
qiladi** — lekin «Uzunlik 300 mm» nimani anglatishini bilmaydi. Buni
faqat `domain.py` biladi.

---

## Ikki tushuncha: PROFIL va MODUL

| | Nima | Misol |
|---|---|---|
| **PROFIL** | mahsulot ta'rifi: maydonlar, retsept, birliklar | non, mebel, beton |
| **MODUL** | ish tartibi: statuslar, o'tishlar, rollar | ishlab chiqarish, savdo, qurilish |

**Nega ajratilgan:** «non zavodi» va «mebel sexi» — ikki xil SOHA,
lekin **bitta ISH TARTIBI** (buyurtma → sexga → tayyor → topshirildi).
Agar status har profilda takrorlansa, 22 profilda 22 marta bir xil
oqim yozilardi va bittasida xato bo'lsa topib bo'lmasdi.

22 soha 5 ta ish tartibini bo'lishadi.

> Odoo da bu «app», 1C da «конфигурация», SAP da «industry solution».
> Bizda ikkisi ajratilgan — bu ulardan farqimiz.

---

## Eng muhim texnik qaror: status MA'NOSI

Kod hech qachon status **nomini** tekshirmaydi. Faqat ma'nosini:

```
boshlanish · muzokara · ishlab_chiqarish · tayyor · topshirildi · bekor
```

Shuning uchun bir soha «Sexda», ikkinchisi «Тикилмоқда», uchinchisi
«Qurilmoqda» deb atashi mumkin — kod uchun ikkalasi ham
`ishlab_chiqarish`.

**Bu qoida bir marta buzilgan edi:** `debt_aging` qarzni status
nomiga qarab hisoblagan va faol profil boshqa nom ishlatganda qarz
noto'g'ri chiqqan. Endi mezon — `delivered_qty > 0`.

---

## Profil bazada, faylda emas

`app/profiles/*.json` — faqat **boshlang'ich shablon**. Birinchi ishga
tushishda bazaga (`soha_profillar`) ko'chiriladi, keyin haqiqat
bazada.

**Nega muhim:** AI yangi soha yasaganda kod ham, fayl ham yozilmaydi
— bazaga yozuv qo'shiladi. Konstruktor g'oyasi shu bilan ishlaydi.

---

## Asosiy funksiyalar

| Funksiya | Nima qiladi |
|---|---|
| `qayta_yukla()` | faol profilni bazadan o'qib keshga qo'yadi |
| `profil()` / `modul()` | hozirgi faol profil / ish tartibi |
| `manosi()` / `status_nomi()` | nom ↔ ma'no ko'prigi |
| `soha_yoz()` / `soha_oqi()` | `attributes` ga yozish/o'qish |
| `retsept_qatorlari()` | buyurtmaga nima ketishi |
| `xomashyo_kerak()` | qancha material kerak |
| `hosila_hisobla()` | boshqa maydonlardan hisoblanadigan qiymat |
| `tekshir()` | majburiy maydonlar, chegaralar |
| `retsept_ziddiyatlari()` | birlik mos kelmasligi, aylanma bog'liqlik |

---

## Xavf: `_KESH` global o'zgaruvchi

```python
_KESH: Profil | None = None
```

Har so'rovda JSON qayta tahlil qilish isrof — shuning uchun kesh.
Lekin bu **bitta jarayon = bitta baza** deb faraz qiladi.

Ikki mijoz bo'lsa: mebel so'rov yubordi → kesh mebel → non so'rov
yubordi → **nonga mebel maydonlari ko'rinadi**. Xato chiqmaydi,
jimgina noto'g'ri ishlaydi — eng yomon turdagi nuqson.

Faylning bosh izohida bu ogohlantirish **yozib qo'yilgan** (kod
o'qigan odam ko'rsin uchun). Ijarachilikda `contextvars` bilan
yechiladi — 26 ta `profil()` chaqiruvi borligi uchun imzoni
o'zgartirmaslik ma'qul.

---

## Tekshiruv

- `tests/profil_test.py` — 22 profil to'liq siklidan o'tadimi (200
  qaytdimi)
- `tests/chuqur_sinov.py` — o'sha 22 sohada **raqamlar to'g'rimi**

Ikkinchisi muhimroq: birinchisi «ishladi» deydi, ikkinchisi
«to'g'ri hisobladi» deydi.
