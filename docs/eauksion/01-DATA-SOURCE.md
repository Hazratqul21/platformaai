# E-AUKSION — Data-source discovery (PHASE 2)

> Manba: `https://e-auksion.uz` (Davlat elektron savdo platformasi).
> Kuzatuv sanasi: 2026-08-27. Metod: brauzerda tarmoq oqimini passiv kuzatish.
> **Faqat ochiq ma'lumot va foydalanuvchining o'z sessiyasi. Manipulyatsiya/bypass yo'q.**

## Domenlar
| Domen | Vazifa | Auth |
|---|---|---|
| `e-auksion.uz` | Ochiq front + `/api/front/*` | Yo'q |
| `auth.e-auksion.uz` | Login portali | — |
| `cabinet.e-auksion.uz` | Shaxsiy kabinet + `/api/cabinet/*` | Ha (cookie/session) |
| `media.e-auksion.uz` | Rasm/media | Yo'q |

## Ochiq API — `/api/front/*` (collector uchun ASOSIY, auth talab qilmaydi)
| Endpoint | Metod | Javob shakli | Izoh |
|---|---|---|---|
| `/api/front/lots/recents?lang=uz` | GET | `{total, rows[]}` | Yaqinda qo'shilgan auksion lotlari |
| `/api/front/lots/current?lang=uz` | GET | `{total, rows[]}` | Ayni jonli auksionlar (bo'sh bo'lishi mumkin) |
| `/api/front/shop-lots?lang=uz` | POST `{page, perPage, ...filtr}` | `{totalPages,totalRows,currentPage,gaming_lots_cnt,rows[]}` | Filtrlangan/do'kon lotlari — asosiy ro'yxat |
| `/api/front/lands` | POST | — | Yer uchastkalari |
| `/api/front/lot-info/lot-statistics` | POST | — | Lot statistikasi (parametr shakli hali aniqlanmagan) |
| `/api/front/common/date?lang=uz` | GET | server vaqti (GMT+5) | Vaqt sinxronizatsiyasi uchun |
| `/api/front/common/currency?lang=uz` | GET | valyuta | |
| `/api/front/dictionaries/get-confiscant-groups` | GET | kategoriyalar | Ma'lumotnoma |
| `/api/front/dictionaries/get-regional-staffs` | GET | hududlar | Ma'lumotnoma |
| `/api/front/dictionaries/get-payment-list` | GET | to'lov turlari | Ma'lumotnoma |

### Lot obyekti (recents.rows[i]) — maydonlar
`id`, `lot_number`, `name`, `full_address`, `confiscant_categories_name`,
`category_id`, `group_id`, `start_price`, `baholangan_narx`, `zaklad_summa`,
`zaklad_percent`, `auction_date_str`, `order_end_time_str`, `lot_statuses_id`,
`lot_type`, `auction_type_id`, `is_descending_auction`, `is_term_payment`,
`term_month`, `user_order_cnt` ("0"/"1+"), `user_orders_apply_cnt`,
`view_count`, `count_favourite`, `file_hash`, `media_url`, `is_favorite`, `is_shop_lot`

## Autentifikatsiyalangan API — `/api/cabinet/*` (faqat KUZATILDI, chaqirilmadi)
| Endpoint | Izoh |
|---|---|
| `POST /api/cabinet/auth/login` | Login |
| `GET /api/cabinet/common/current-auctions` | Foydalanuvchi ishtirokidagi jonli auksionlar (real-time) |
| `GET /api/cabinet/user/balance` | Balans |
| `GET /api/cabinet/win-lots/achievements` | Yutilgan lotlar |
| `GET /api/cabinet/user/messages?perPage&page&notif_type&date_from&date_to` | Bildirishnomalar |
| `GET /api/cabinet/order-contract/count`, `closed-auction/cnt`, `bo-orders/cnt` | Hisoblagichlar |

## Xulosa — LOT MONITOR uchun maqbul rejim
- **Yig'uvchi:** faqat ochiq `/api/front/*` (auth shart emas). HTML parse qilinmaydi.
- **Polling:** hurmatli interval (mas'uliyatli, saytni ortiqcha yuklamaydigan). `common/date` bilan vaqtni sinxronlash.
- **Bid tafsiloti:** ochiq ro'yxatda aniq bid summasi/ishtirokchi kimligi YO'Q — faqat `user_order_cnt`/`user_orders_apply_cnt` (agregat) va `count_favourite`, `view_count`. Aniq bid oqimi jonli auksion xonasida (ehtimol WebSocket) — bu keyingi, ehtiyotkor bosqichda tekshiriladi.
- **Huquqiy:** faqat ochiq ma'lumotni monitoring + o'z hisobi. Boshqa ishtirokchiga xalal / natijani o'zgartirish YO'Q. (qarang `docs/02-QONUNCHILIK.md`)

## Ochiq savollar (keyingi discovery)
- `lot-statistics` POST tanasi (bid tarixi/narx dinamikasi shu yerdami?)
- Jonli auksionda narx o'zgarishi push kanali (WebSocket/SSE) bormi?
- `shop-lots` filtr parametrlari (kategoriya, hudud, status, sana) to'liq ro'yxati.

## Auth mexanizmi — NETWORK orqali tasdiqlangan (2026-08-27)
- **Cookie-based session** (isbot: `include`→200, `omit`→401 himoyalangan endpointlarda).
  JWT/Bearer YO'Q — JS `localStorage`/`sessionStorage` bo'sh, so'rovlar faqat cookie bilan ishlaydi.
- JS-ko'rinadigan cookie'lar: `user` (profil JSON, `id`...), `locale`, `smart_top`, `crisp-client...`.
  Asl **sessiya cookie'si** login javobidagi `Set-Cookie` bilan o'rnatiladi (aniq nom/httpOnly — build vaqtida bitta real login capture'idan tasdiqlanadi).
- Login endpoint: `POST https://cabinet.e-auksion.uz/api/cabinet/auth/login`.

### Auto-login moduli uchun dizayn (innaslot_bot/uzum_session.py uslubida)
- Python `requests.Session()` (yoki `aiohttp` cookie-jar) — login javobidagi barcha cookie'larni avtomatik ushlaydi/qayta yuboradi.
- Kredensiallar `.env`/shifrlangan store'da; **parol ochiq matnda saqlanmaydi**.
- Sessiya cookie'si faylga saqlanadi; muddati tugasa qayta login.
- MONITOR-only: avtomatik bid YO'Q (MONITOR → ALERT → USER CONFIRMATION → USER BID).

### OCHIQ SAVOLLAR (build vaqtida real login capture'idan)
- Login POST tanasi: maydon nomlari (`login`/`username` + `password`), content-type.
- CAPTCHA: YO'Q, SMS/OTP: YO'Q — oddiy login+parol (foydalanuvchi tasdiqladi 2026-08-27). Auto-login toza ishlaydi.
- Sessiya cookie muddati (necha soat/kun) va refresh mexanizmi bormi.
