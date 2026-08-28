"""
E-AUKSION endpoint inventari — BITTA MANBA (discovery: 2026-08-27).
════════════════════════════════════════════════════════════════════
Manba: https://e-auksion.uz  (Davlat elektron savdo platformasi).
Uslub: innaslot_bot/services/uzum_session.py dagi "ENDPOINTS bir joyda".
E-auksion o'zgartirsa — FAQAT shu faylni yangilang.

METOD BELGISI:
  ✅ kuzatilgan (network trafikda ko'rilgan)
  ⏳ real ochilishda tasdiqlanadi (SPA hali chaqirmadi)
  🚫 AMAL (bid/ariza/to'lov) — HUJJATLASHTIRILGAN, avtomatik CHAQIRILMAYDI.
     Model: MONITOR → ALERT → USER CONFIRMATION → USER BID.
OPTIONS ishonchsiz: server wildcard "GET,POST,PUT,PATCH,DELETE,..." qaytaradi.
"""

# ── Domenlar ────────────────────────────────────────────────────────
FRONT_BASE   = "https://e-auksion.uz/api/front"      # ochiq, auth YO'Q
CABINET_BASE = "https://cabinet.e-auksion.uz/api/cabinet"  # login kerak (cookie)
AUTH_ORIGIN  = "https://auth.e-auksion.uz"
MEDIA_BASE   = "https://media.e-auksion.uz"

LANG = "uz"  # ?lang=uz

# ── OCHIQ front (COLLECTOR uchun asosiy) ────────────────────────────
FRONT = {
    "lots_recents":   ("GET",  "/lots/recents"),            # ✅ {total, rows[]}
    "lots_current":   ("GET",  "/lots/current"),            # ✅ jonli auksionlar
    "shop_lots":      ("POST", "/shop-lots"),               # ✅ {page,perPage} -> sahifalangan
    "lands":          ("POST", "/lands"),                   # ✅ yer uchastkalari
    "lot_statistics": ("POST", "/lot-info/lot-statistics"), # ✅ (tana shakli aniqlanadi)
    "favorites":      ("GET",  "/lot-info/favorites"),      # ✅
    "date":           ("GET",  "/common/date"),             # ✅ server vaqti (ms)
    "currency":       ("GET",  "/common/currency"),         # ✅
    "confiscant_groups": ("GET", "/dictionaries/get-confiscant-groups"),  # ✅
    "regional_staffs":   ("GET", "/dictionaries/get-regional-staffs"),    # ✅ hududlar
    "payment_list":      ("GET", "/dictionaries/get-payment-list"),       # ✅
    "last_news":         ("GET", "/publications/last-news"),              # ✅
}

# ── CABINET o'qish (auth) — monitoring uchun ────────────────────────
CABINET_READ = {
    "current_auctions": ("GET",  "/common/current-auctions"),  # ✅ jonli savdo
    "lot_details":      ("GET?", "/lot-info/lot-details"),     # ⏳ to'liq lot
    "short_lot_info":   ("GET?", "/lot-info/short-lot-info"),  # ⏳
    "offers":           ("GET?", "/common/offers"),            # ⏳ takliflar/bidlar
    "lot_zaklad_persent": ("GET?", "/common/lot-zaklad-persent"),  # ⏳
    "chart_lots":       ("GET?", "/chart/lots"),               # ⏳ narx grafigi
    "chart_lot_order":  ("GET?", "/chart/lot-order"),          # ⏳ bid/order grafigi
    "win_lots":         ("GET",  "/win-lots"),                 # ✅ yutilgan lotlar
    "achievements":     ("GET",  "/win-lots/achievements"),    # ✅
    "my_orders":        ("GET?", "/my-orders"),                # ⏳
    "closed_auction":   ("GET?", "/closed-auction"),           # ⏳
    "user_balance":     ("GET",  "/user/balance"),             # ✅
    "user_transactions":("GET?", "/user/transactions"),        # ⏳
    "notifications":    ("GET",  "/user/messages"),            # ✅ perPage,page,notif_type,date_from,date_to
    "unread_notifs":    ("GET",  "/user/unread-messages"),     # ✅
    "user_info":        ("GET?", "/user/info"),                # ⏳
}

# ── AMAL endpointlari — 🚫 avtomatik CHAQIRILMAYDI (hujjat uchun) ────
# Metod real amalda (foydalanuvchi tasdig'i bilan) capture qilinadi.
CABINET_ACTIONS = {
    "login":         ("POST", "/auth/login"),                 # 🚫 sessiya moduli (bir marta)
    "logout":        ("POST", "/auth/logout"),                # 🚫
    "do_action":     ("POST", "/order-actions/do-action"),    # 🚫 ASOSIY amal (bid/ariza/tasdiq)
    "do_with_res":   ("POST", "/order-actions/do-with-res"),  # 🚫 fayl bilan amal
    "exec_order_actions": ("POST", "/exec-order-actions"),    # 🚫
    "user_order":    ("POST", "/user-order"),                 # 🚫 buyurtma/ariza yaratish
    "user_contest_order": ("POST", "/user-contest-order"),    # 🚫 konkurs arizasi
    "payment":       ("POST", "/payment"),                    # 🚫 TO'LOV (pul!)
    "payment_back":  ("POST", "/payment-back"),               # 🚫 pul qaytarish
    "favorite":      ("POST", "/lot-info/favorite"),          # 🚫 (kichik) sevimliga qo'shish
    "send_sms":      ("POST", "/user/send-sms"),              # 🚫
    "change_password":("POST","/user/change-password"),       # 🚫
    "remove_user":   ("POST", "/user/remove-user"),           # 🚫
}
