# E-AUKSION — G'alaba mexanizmi va strategiya asosi (PHASE 5 tayyorgarlik)

> Manba: e-auksion.uz ilovasining o'z matnlari (statik JS) + ochiq qoidalar.
> Kuzatuv: 2026-08-27 (tunda, jonli savdosiz). Jonli tafsilotlar 10:00 da tasdiqlanadi.
> **Maqsad:** tezroq ma'lumot + chuqur tahlil → foydalanuvchi tez va to'g'ri qaror qilsin.
> **Chegara:** MONITOR → ALERT → USER CONFIRMATION → USER BID. Manipulyatsiya/aralashuv YO'Q.

## 1. Lot hayotiy sikli
```
E'lon  →  Ariza + Zakalat (deposit)  →  SAVDO (qadamli narx berish)
      →  G'olib aniqlanadi  →  Oferta shartnomasi (ECP imzo)  →  To'lov  →  Shartnoma (QR)
```
- **Ariza:** `order_end_time` gacha ariza beriladi (`Ariza berish yakunlandi` — deadline).
- **Zakalat:** taklif narxining **kamida 5%** (`zakalad_amount_min_5_percent`). Lot e'lonida foiz ko'rsatilgan (5/10/25%).
- **Savdo boshlanishi:** `auction_game_date` — "Savdo boshlanish vaqti" (odatda 10:00).

## 2. Narx berish ("Give price") — qanday ishlaydi
- Ariza qabul qilingach: `Narx berish` tugmasi (`give_price`, `you_can_give_price`).
- **Ikki rejim:**
  1. **Qadamga bog'langan** taklif — `Auksion qadamlari` (`auction_step_info`). Har qadam belgilangan.
     `first_step` = "Birinchi qadam bahosi", `min_summa` = "Eng past narx".
  2. **Qadamga bog'lanmagan** taklif (`make_auto_bid_offer`, "Auksion qadamiga bog'lanmagan taklif") —
     `less_than_next_price`: "Tizim taklif qilayotgan narxdan kattaroq summani kiriting. Joriy taklif: {next_amount}".
     `percent_notice`: bog'lanmagan taklifda zakalat foizi/summasi e'londagidan farq qilishi mumkin.
- **Auto-bid platformada bor** (`add_auto_bids`, `bid_lot`: "sizning nomingizdan narx berish funksiyasini ishga tushiradi").
  ⚠️ Bu — E-AUKSIONNING O'Z funksiyasi (rasmiy). Bizning tizim buni CHAQIRMAYDI; faqat mavjudligini qayd etamiz.
- Holatlar: `last_confirmed_price` ("Oxirgi tasdiqlangan narx"), `not_submitted` ("Narx tasdiqlanmagan"), `offered_price`.

## 3. O'yindan chiqish va G'olib (sen aytgan mexanizm — tasdiqlangan)
- **3-qadamdan boshlab:** har yangi taklifdan oldin hisobда **yetarli zakalat** bo'lishi shart (`step_1`).
- **Mablag' yetmasa** — keyingi taklifni bera olmaysan (`warning`) → amalda **o'yindan chiqasan**.
- **G'olib** = `G'olib tasdiqlagan taklif` (`winner_stavka`) — eng yuqori tasdiqlangan narx bergani.
  `winner_stavka_time` — tasdiqlangan vaqt. Teng holatda vaqt muhim.
- **Zaxiradagi g'olib** (`second_winner_*`) = 2-o'rin — asosiy g'olib rad etsa, unga o'tadi.
- **Konkurs rejimi:** ba'zi lotlarda narx emas, **ball** (`winner_score` = "G'olib to'plagan umumiy ball") — bu narx+boshqa mezonlar.
- **Yagona ishtirokchi:** raqib bo'lmasa `ishtirokchiga taklif berildi` (`lot_one_result_text`) — savdosiz taklif.
- **G'olib bo'lmaganга zakalat qaytariladi** (`step_2`). G'olibда qo'shimcha zakalat umumiy to'lovга o'tadi (`step_3`), qolgani muddatda (`step_4`).

## 4. Vaqt / countdown
- `card_countdown_title` — arizalar deadline'ига sanoq (`minut`/`secund`).
- Uzaytirish (anti-snayping) qoidasi front matnida **topilmadi** — jonli savdoda tasdiqlanadi (OCHIQ SAVOL).

## 5. Natija va G'oliblik bayonnomasi (PUBLIC — biz kuzatib/tekshiramiz)
- `Auksion natijasi` (`lot_result`), `Auksion yakunlangan vaqt` (`complated_time`).
- **Bayonnoma tekshiruvi (ochiq xizmat):** `how_check_winner_protocol` — "G'oliblik bayonnomasi qanday tekshiriladi?"
  `svc_protocol_desc`: **JSHSHIR yoki STIR + lot raqami** orqali bayonnoma haqiqiyligi.
  `svc_contract_desc`: **QR-kodli** ijara shartnomasi holati onlayn.
- Endpointlar: `closed-auction`, `win-lots`, `user/customer-protocols`, `user/qr-protocols`.

## 6. Real-time kanal
- Front bundle'da WebSocket/socket.io/centrifugo izi **YO'Q** (`rt_hits: []`).
- Ehtimol jonli savdoда **HTTP polling** (kabinet `give-price`/`offers`/`current-auctions` ni takror so'raydi).
- ANIQ tasdiqlash: **10:00, jonli lotда** network kuzatuvi.

## 7. G'alaba OMILLARI (bizning tahlil/model kirishlari — real maydonlarga bog'langan)
| Omil | Manba maydoni | Strategik ma'no |
|---|---|---|
| Raqobat zichligi | `user_orders_apply_cnt`, `offers` | Nechta jiddiy raqib bor |
| Bid chastotasi | `chart/lot-order`, event log | Narx qanchalik tez ko'tarilyapti |
| Narx tezligi (velocity) | `price_history` | Baholangan narxdan qancha oshadi |
| Qolgan vaqt | `auction`/countdown | Qachon qaror kerak |
| **Zakalat balansi** | `user/balance` | ⭐ ASL "chidamlilik" — 3-qadamdan keyin balans yetmasa chiqiladi |
| Tarixiy naqsh | yopilgan auksionlar | O'xshash lotlar qanchaga ketgan |
| Budjet chegarasi | `ea_watchers.max_budget` | Narx budjetga yaqinlashganda ALERT |

**Model natijasi:** `LOW / MEDIUM / HIGH COMPETITION` — UI'da "PROGNOZ" deb aniq belgilanadi (`ea_analysis_results.is_forecast`).

## 8. Bizning YECHIM (qonuniy) — nima qilamiz / nima QILMAYMIZ
QILAMIZ: tezkor lot monitoringi; narx/qatnashuv dinamikasi; budjet/deadline ALERT'lari;
g'alaba ehtimoli prognozi; o'xshash lotlar tarixi; zakalat balansini oldindan rejalashtirish maslahati.
QILMAYMIZ: avtomatik bid; raqiblarга xalal; race-condition/zaiflik ekspluatatsiyasi; natija manipulyatsiyasi.
Bid'ni HAR DOIM foydalanuvchi o'zi, tasdiq bilan qo'yadi.

## OCHIQ SAVOLLAR (10:00 jonli savdoda)
- Real-time kanal: polling intervali yoki WebSocket?
- `give-price` (do-action) so'rov tanasi va javobi (narx tasdiqlanishi).
- `offers`/`chart/lot-order` — bid tarixi qanday ko'rinadi (raqib summalari ochiqmi?).
- Uzaytirish (anti-snayping) qoidasi bormi.
