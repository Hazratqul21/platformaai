#!/usr/bin/env bash
# =====================================================================
#  OFFSITE ZAXIRA — lokal zaxirani BULUTGA ko'chirish (rclone)
#
#      bash tools/offsite.sh
#      (cron: har tun, lokal zaxiradan KEYIN — masalan 03:30)
#
#  NEGA KERAK: tungi zaxira (`zaxira.sh`) ma'lumot bilan BIR DISKDA
#  turadi. Server yoki disk yo'qolsa — zaxira ham ketadi. Bu skript
#  o'sha zaxira papkasini bulutga (S3/Backblaze/...) ko'chiradi, ya'ni
#  ma'lumotning ikkinchi nusxasi boshqa joyda saqlanadi.
#
#  SOZLASH (maxfiy kalit CHATDAN O'TMAYDI — serverda o'zingiz):
#    1. rclone o'rnatilsin (bir marta, sudo bilan):
#         curl https://rclone.org/install.sh | sudo bash
#    2. bulut ulanmasi sozlansin (interaktiv, kalitlar rclone.conf ga
#       yoziladi, .env ga EMAS):
#         rclone config          # remote nomi: ordo-bulut
#    3. .env ga remote:bucket yo'li qo'shilsin:
#         OFFSITE_REMOTE=ordo-bulut:ordo-zaxira
#       (ixtiyoriy) OFFSITE_SAQLASH_KUN=60   # bulutда necha kun turadi
#
#  SUDO KERAK EMAS (rclone o'rnatilgach). Kalitlar bu skriptда yo'q.
# =====================================================================
set -uo pipefail

JOY="${JOY:-/var/www/innasoft-platforma}"
ZAXIRA="$JOY/zaxira"
cd "$JOY" 2>/dev/null || { echo "JOY topilmadi: $JOY"; exit 2; }
[ -f .env ] && set -a && . ./.env && set +a

REMOTE="${OFFSITE_REMOTE:-}"
SAQLASH_KUN="${OFFSITE_SAQLASH_KUN:-60}"
VAQT="$(date '+%F %T')"

if ! command -v rclone >/dev/null 2>&1; then
  echo "[$VAQT] ✗ rclone o'rnatilmagan — offsite o'tkazildi (skriptdagi SOZLASH ga qarang)"
  exit 2
fi
if [ -z "$REMOTE" ]; then
  echo "[$VAQT] ✗ OFFSITE_REMOTE (.env) yo'q — offsite o'tkazildi"
  exit 2
fi
if [ ! -d "$ZAXIRA" ]; then
  echo "[$VAQT] ✗ zaxira papkasi yo'q: $ZAXIRA"
  exit 2
fi

# copy (sync EMAS): bulutda lokaldan ko'ra ko'proq tarix qolishi mumkin.
# Faqat .gz/.sql.gz/.tar.gz ko'chiriladi — log fayllar shart emas.
echo "[$VAQT] Bulutga ko'chirilmoqda -> $REMOTE"
if rclone copy "$ZAXIRA" "$REMOTE" \
     --include '*.gz' --include '*.sql.gz' --include '*.tar.gz' \
     --transfers 4 --checkers 8 --stats-one-line 2>&1; then
  echo "[$VAQT] ✓ ko'chirildi"
else
  echo "[$VAQT] ✗ rclone copy YIQILDI"
  exit 1
fi

# Bulutда eski nusxalarni tozalash (lokal 14 kun, bulut default 60 kun)
rclone delete "$REMOTE" --min-age "${SAQLASH_KUN}d" --include '*.gz' 2>/dev/null \
  && echo "[$VAQT] ✓ bulutda ${SAQLASH_KUN} kundan eski nusxalar tozalandi" \
  || true

exit 0
