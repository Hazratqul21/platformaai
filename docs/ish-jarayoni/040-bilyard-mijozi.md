# 040 — BILYARD MIJOZI ULANDI (THE BILLIARD)

**Sana:** 2026-08-26
**Holat:** ✅ prodda ishlaydi — `billiard.innasoft.uz`, Mini App bilan

---

## Nima qilindi

Platformaga birinchi **bilyard klubi** ulandi. Mijozning Excel kassa
daftari tizimga kiritildi, Telegram Mini App orqali kirish yoqildi.

| | |
|---|---|
| Manzil | **https://billiard.innasoft.uz** |
| Kirish | `admin` / `1234` |
| Akkaunt | id=7, kod `billiard`, baza `inna_billiard` |
| Soha | **Bilyard klubi** (yangi profil) |
| Bot | **@bilyardhis_bot** — menyuda «ERP ochish» tugmasi |
| Ma'lumot | 177 ta kassa yozuvi (avgust 2026) |

DNS va SSL uchun **hech narsa qilinmadi** — `*.innasoft.uz` wildcard
DNS ham, wildcard sertifikat ham, nginx bloki ham allaqachon bor edi.
Akkaunt yaratilgan zahoti subdomen ishladi.

---

## Yangi profil: `app/profiles/bilyard.json`

Stol vaqtga beriladi, yonida bar ishlaydi. O'lchov birligi — **soat**
(0.5 dan boshlab, kasrli).

Maydonlar: stol raqami · stol turi (rus piramidasi / pul / snuker /
VIP xona) · tarif (kunduzgi / kechki / dam olish / abonement) ·
soatlik narx · o'yin boshlangan vaqt · o'yinchilar soni · bar hisobi.

Narx qo'lda kiritiladi: tarif kunduz/kechga qarab o'zgaradi.

---

## Excel ko'chirish: `tools/bilyard_excel.py`

Mijoz pulni Excel da yuritadi. Har varaq — bir tur harakat:

| Varaq | Yozuv | Summa | Yo'nalish |
|---|---|---|---|
| ПРИХОД | 1 | 3 200 000 | Kirim |
| Запрлата | 13 | 104 340 000 | Chiqim (ijara, svet, oyliklar) |
| Расходы | 131 | 121 120 000 | Chiqim (obed, premiya, oylik) |
| Лист1 | 32 | 15 296 500 | Chiqim (bar tovari) |
| **Лист2**, **3-ЭТ 21 КВ** | — | — | **O'TKAZILDI** |

Oxirgi ikkitasi boshqa varaqlarning JAMI si. Kiritilsa pul ikki marta
sanalardi.

### Sinov ikkita haqiqiy nuqson topdi

**1. Jamlovchi qator yozuv sifatida kirardi.** `Запрлата` da nomi
aynan «зарплата» bo'lgan qator bor va u varaqning jami (104 340 000)
edi. Kiritilganda xarajat **ikki barobar** (208 680 000) chiqardi.
Endi ikki xil tekshiruv: ichida «Итого» bo'lgan matn, va nomi aynan
tur so'zi bo'lgan qator.

**2. Takror himoyasi haqiqiy pulni yeb qo'yardi.** Avval bir xil
(sana + kim + summa) yozuv ikkinchi marta uchrasa tashlab yuborilardi.
Lekin faylda «Алиш ишчи · 50 000 · 07.08» ikki marta bor va **ikkalasi
ham rost** (ikki kishiga premiya). Endi himoya qator darajasida emas,
FAYL darajasida: bazada shu vosita kiritgan yozuv bo'lsa vosita
to'xtaydi, `--tozala` bilan qaytadan kiritiladi.

> Naqsh takrorlandi: real ma'lumot vositani o'rgatadi (027 dagi
> oklad/sdelshina hikoyasi kabi).

---

## Tushum ATAYLAB kiritilmadi

Excel da tushum deyarli yo'q — bitta yozuv (3.2 mln, 3-iyul), holbuki
`Лист2` da qo'lda «биллиард 272 902 000» deb yozilgan. Qaror: eski
tushum kiritilmaydi, **klient uni o'zi tizimga yozadi**.

Natijada birinchi kunlarda kassa **−237 556 500** ko'rsatadi — faqat
xarajat bor. Bu xato emas, kutilgan holat. Klient tushumni yoza
boshlagach raqam o'z holiga keladi.

Yana bir farq: klientning qo'lda yozgan jami (`Лист2`: «харажат
август 120 320 000») bizning yig'indimizdan **800 000 so'mga** farq
qiladi. Bizniki — qatorlarni qo'shib chiqqan raqam.

---

## Mini App

Kod o'zgarmadi — `app/bot.py` allaqachon akkauntning `bot_token` va
`webapp_url` ini olib, botni ishga tushiradi va Telegram menyusiga
`MenuButtonWebApp` qo'yadi.

Token `/api/obuna/bot` orqali qo'yildi (Rahbar roli, akkauntning o'z
subdomenida). Bu endpoint tokenni saqlaydi VA botni **darhol ishga
tushiradi** — serverni qayta yuklash kerak bo'lmadi, ya'ni boshqa
akkauntlar uzilmadi.

Telegram tomonda tasdiqlandi:

```json
{"type": "web_app", "text": "ERP ochish",
 "web_app": {"url": "https://billiard.innasoft.uz/"}}
```

---

## Tekshirildi (tashqaridan)

| Tekshiruv | Natija |
|---|---|
| `admin`/`1234` bilan kirish | ✅ 200, majburiy parol almashtirish yo'q |
| Faol soha | ✅ Bilyard klubi |
| Kassa jurnali | ✅ 177 yozuv, firma «THE BILLIARD» |
| Bot | ✅ polling ishlayapti, Mini App tugmasi o'rnatildi |
| karton / mebel / test | ✅ 200 — buzilmadi |
| **tizim.innasoft.uz (Rustam aka)** | ✅ 200, `tizim.service` faol, baza md5 **o'zgarmagan** |

---

## Nozik joylar

- **`admin`/`1234` ochiq subdomenda.** Foydalanuvchi shunday so'radi.
  Tizimda urinishlar cheklovi bor (5 marta / 15 daqiqa, IP bo'yicha),
  lekin `1234` birinchi urinishdayoq topiladi. Klient birinchi
  kirgandan keyin parol almashtirilsin.
- Profil fayli va vosita konteynerga `docker cp` bilan qo'yildi.
  **Konteyner qayta qurilsa yo'qoladi** — `app/profiles/bilyard.json`
  va `tools/bilyard_excel.py` keyingi deployda repodan kelishi kerak.
- `docker-compose.yml` ga TEGILMADI (039 dagi ogohlantirish).

---

## Qoldi

1. Klient tushumni yozishni boshlasin (Mini App orqali)
2. Parol almashtirilsin
3. Keyingi deployda profil + vosita repodan chiqsin
