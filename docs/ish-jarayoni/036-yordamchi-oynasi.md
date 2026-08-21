# 036 — Yordamchi oynasi: sarlavha, salom va javob ko'rinishi

Sana: 2026-08-21 · Bosqich: frontend sayqal · Holat: bajarildi

## Nima qilindi

035 dan keyin AI paneli mobil ekranda ochib ko'rildi va haqiqiy savol
berildi («Kim qancha qarzdor?») — Rustam akaning haqiqiy ma'lumoti
ustida. Panel ishladi, lekin 5 ta nuqson chiqdi. Hammasi tuzatildi.

| # | Nuqson | Sabab |
|---|--------|-------|
| 1 | Panel boshida faqat model nomi turardi | 034 da yordamchi bittaga tushdi, tanlash ro'yxati yashirildi, o'rniga hech narsa qo'yilmadi |
| 2 | Salom quruq: «Savolingizni yozing.» | `AGENT_SALOM` da `yordamchi` kaliti yo'q edi |
| 3 | Kiritish maydonida konstruktor davridan qolgan matn | «Non zavodimiz bor, kuniga 3000 non yopamiz» |
| 4 | Savolning javobi ekrandan chiqib ketardi | model jadvalga «Telefon» ustunini qo'shardi, «Qarz» esa surilib ketardi |
| 5 | Ekranda xom yulduzchalar: `**Xon xonim**` | matn `textContent` ga qo'yilardi, markdown chizilmasdi |

## Fayllar

- `static/js/pages/agent.js` — sarlavha, salom, kiritish matni, `matnniChiz`
- `app/agent.py` — `qarzdorlar` maydon tartibi va `_UMUMIY_USLUB` ga
  jadval qoidasi

## Nega aynan shunday

**1 va 2 — 034 ning izi.** Yordamchi bittaga birlashtirilganda uning
ko'rinish tomoni oxirigacha olib borilmagan ekan. Endi `agentNom`
sarlavhasi qo'shildi (bitta bo'lsa ko'rinadi, ko'p bo'lsa tanlash
ro'yxatiga o'rin bo'shatadi), salomda esa nima so'rash mumkinligi 4 ta
misol bilan ko'rsatiladi. Salomda nom takrorlanmaydi — u sarlavhada
turibdi.

**4 — ikki bosqichda tuzatildi.** Avval `qarzdorlar` da maydon tartibi
o'zgartirildi (`qarz` nomdan keyin, `telefon` oxiriga). Sinov ko'rsatdi
— YETMADI: model ustunni o'zi tanlar ekan, telefon baribir ikkinchi
bo'lib qoldi. Shundan keyin `_UMUMIY_USLUB` ga qoida yozildi:
3-4 tadan ortiq ustun bo'lmasin, so'ralmagan ustun qo'shilmasin,
ikkinchi ustun — savolning javobi bo'lgan raqam.

Bu qoida `_UMUMIY_USLUB` da — ya'ni admin panelidan o'zgartirilmaydi
(qarang [030](030-korsatma-tahrirlash.md)). Sabab: bu uslub emas,
javobning ko'rinadigan-ko'rinmasligini hal qiladi.

**5 — markdown, lekin HTML QURILMAYDI.** `matnniChiz` matn tugunlari va
`<strong>` elementlarini qo'lda yasaydi, `innerHTML` ishlatilmaydi.
Agent javobi ham, foydalanuvchi matni ham ishonchsiz manba —
xavfsizlik xossasi o'zgarmadi.

## Nimaga tegdi

`app/agent.py` o'zgargani uchun konteyner qayta ishga tushirildi
(statik fayllardan farqli). Boshqa asboblar tegilmadi.

`_UMUMIY_USLUB` — HAMMA agentga qo'shiladi, ya'ni qoida eski 4 ta
agentga ham tegdi. Bu ataylab: qoida ularga ham to'g'ri.

## Xavf

O'rta. `_UMUMIY_USLUB` ga qo'shilgan qoida modelning har javobiga
ta'sir qiladi. Jadval ustunlarini kamaytirish so'ralmagan ma'lumotni
yashiradi — lekin foydalanuvchi so'rasa, model uni baribir chiqaradi
(qoida «so'ralmagan ustunni qo'shma» deydi, «hech qachon ko'rsatma»
demaydi).

## Tekshiruv

Haqiqiy LLM bilan, haqiqiy ma'lumot ustida, mobil ekranda (375px):

- Savol: «Kim qancha qarzdor?»
- **Oldin:** ustunlar `Mijoz · Telefon · Qarz summasi · Kechikkan muddat`
  — qarz ekrandan surilib ketgan
- **Keyin:** ustunlar `Mijoz · Qarz · Kechikish`, qarz ustunining o'ng
  cheti **309 < 375** — surmasdan ko'rinadi
- Raqamlar to'g'ri: Деликатес траде 196 382 895 so'm (moliya ekrani
  bilan bir manbadan — `debt_aging`)
- Sarlavha «Yordamchi», ostida `gemini · gemini-3.5-flash`
- Qalin shrift chizildi; `**a** <img src=x onerror=...>` sinovida
  `<img>` elementi YARATILMADI, matn sifatida qochirildi

## Qoldi

- Summa ustunida «so'm» so'zining oxiri ~10px kesiladi (jadval
  suriladi, ya'ni yetib boriladi)
- Boshqa akkauntlarda (mebel, non) yordamchini sinash
