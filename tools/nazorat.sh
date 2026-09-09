#!/usr/bin/env bash
# =====================================================================
#  NAZORAT — hamma narsa tirikmi (monitoring)
#
#      bash tools/nazorat.sh
#      (cron: har 5 daqiqada)
#
#  NEGA KERAK (2026-08-28 auditi): ikki narsa JIMGINA buzuq turgan edi —
#  app.innasoft.uz 503, tungi zaxira 2 kun ishlamagan — va hech kim
#  bilmagan. Bu skript har 5 daqiqada tekshiradi va MUAMMO bo'lsa
#  Telegram'ga xabar yuboradi. Sog' bo'lsa — jim (spam yo'q).
#
#  TEKSHIRADI:
#    1. Har akkaunt domeni /api/health -> 200 (boshqaruvdan o'qiladi)
#    2. Konteynerlar (app, db) ishlayaptimi
#    3. Tungi zaxira yangimi (< 26 soat)
#    4. Diskda joy bormi (< 90%)
#
#  XABAR KANALI (ixtiyoriy): .env da
#      NAZORAT_BOT_TOKEN=...      (Telegram bot tokeni — ops uchun alohida)
#      NAZORAT_CHAT_ID=...        (kimga yuborilsin)
#  Berilmasa — faqat logga yoziladi, xabar yuborilmaydi.
#
#  SUDO KERAK EMAS.
# =====================================================================
set -uo pipefail

JOY="${JOY:-/var/www/innasoft-platforma}"
KONT_APP="innasoft-app"
KONT_DB="innasoft-db"
ZAXIRA="$JOY/zaxira"
DOMEN="${ASOSIY_DOMEN:-innasoft.uz}"
ZAXIRA_MAX_SOAT="${ZAXIRA_MAX_SOAT:-26}"
DISK_MAX_FOIZ="${DISK_MAX_FOIZ:-90}"

cd "$JOY" 2>/dev/null || { echo "JOY topilmadi: $JOY"; exit 2; }
[ -f .env ] && set -a && . ./.env && set +a

BOT="${NAZORAT_BOT_TOKEN:-}"
CHAT="${NAZORAT_CHAT_ID:-}"

MUAMMOLAR=()
muammo(){ MUAMMOLAR+=("$1"); }

# ---------------------------------------------------------------- 1
# Konteynerlar
for k in "$KONT_APP" "$KONT_DB"; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$k"; then
    muammo "Konteyner ishlamayapti: $k"
  fi
done

# ---------------------------------------------------------------- 2
# Har akkaunt domeni (boshqaruvdan). Konteyner tirik bo'lsagina.
if docker ps --format '{{.Names}}' | grep -qx "$KONT_DB"; then
  KODLAR="$(docker exec "$KONT_DB" psql -U "${POSTGRES_USER:-innasoft}" -d boshqaruv -Atc \
    "SELECT kod FROM akkauntlar WHERE holat <> 'ochirilgan' ORDER BY kod" 2>/dev/null || true)"
  for kod in $KODLAR; do
    h="$kod.$DOMEN"
    kodht=$(curl -sS -m 12 -o /dev/null -w '%{http_code}' "https://$h/api/health" 2>/dev/null || echo 000)
    [ "$kodht" = "200" ] || muammo "$h -> $kodht (kutilgan 200)"
  done
fi

# ---------------------------------------------------------------- 3
# Zaxira yangimi — eng so'nggi fayl 26 soatdan eski bo'lmasin
if [ -d "$ZAXIRA" ]; then
  YANGI="$(find "$ZAXIRA" -name 'baza-*.sql.gz' -printf '%T@\n' 2>/dev/null | sort -n | tail -1)"
  if [ -z "$YANGI" ]; then
    muammo "Zaxira topilmadi ($ZAXIRA) — tungi zaxira ishlamayapti"
  else
    YOSH_SOAT=$(( ( $(date +%s) - ${YANGI%.*} ) / 3600 ))
    [ "$YOSH_SOAT" -le "$ZAXIRA_MAX_SOAT" ] || \
      muammo "Zaxira eskirgan: oxirgisi ${YOSH_SOAT} soat oldin (chegara ${ZAXIRA_MAX_SOAT}h)"
  fi
else
  muammo "Zaxira papkasi yo'q: $ZAXIRA"
fi

# ---------------------------------------------------------------- 4
# Disk
FOIZ=$(df --output=pcent / | tail -1 | tr -dc '0-9')
[ "${FOIZ:-0}" -lt "$DISK_MAX_FOIZ" ] || muammo "Diskда joy kam: %${FOIZ} band (chegara %${DISK_MAX_FOIZ})"

# ---------------------------------------------------------------- natija
VAQT="$(date '+%F %T')"
if [ "${#MUAMMOLAR[@]}" -eq 0 ]; then
  echo "[$VAQT] ✓ hammasi sog'"
  exit 0
fi

XABAR="🔴 ORDO nazorat — $VAQT"$'\n'
for m in "${MUAMMOLAR[@]}"; do
  echo "[$VAQT] ✗ $m"
  XABAR="$XABAR"$'\n'"• $m"
done

# Telegram (token bo'lsa). URL emas, --data-urlencode bilan xavfsiz.
if [ -n "$BOT" ] && [ -n "$CHAT" ]; then
  curl -sS -m 15 -o /dev/null \
    --data-urlencode "chat_id=$CHAT" \
    --data-urlencode "text=$XABAR" \
    "https://api.telegram.org/bot$BOT/sendMessage" 2>/dev/null \
    && echo "[$VAQT] xabar yuborildi" \
    || echo "[$VAQT] xabar YUBORILMADI (Telegram xatosi)"
else
  echo "[$VAQT] (NAZORAT_BOT_TOKEN/CHAT_ID yo'q — xabar yuborilmadi, faqat log)"
fi

exit 1
