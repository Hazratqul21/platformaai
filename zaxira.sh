#!/usr/bin/env bash
# ============================================================
#  ZAXIRA — baza + yuklangan rasmlar
#
#  Kunlik cron uchun:
#      0 3 * * * /opt/innasoft/zaxira.sh >> /var/log/innasoft-zaxira.log 2>&1
#
#  Tiklash:
#      gunzip -c zaxira/baza-2026-08-07.sql.gz | \
#        docker compose exec -T db psql -U innasoft innasoft
#      tar xzf zaxira/rasmlar-2026-08-07.tar.gz -C /
# ============================================================
set -euo pipefail

JOY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$JOY"

QAYERGA="${ZAXIRA_JOYI:-$JOY/zaxira}"
SAQLASH_KUN="${ZAXIRA_KUN:-14}"
SANA="$(date +%F-%H%M)"
mkdir -p "$QAYERGA"

# .env dagi POSTGRES_* qiymatlari kerak
[ -f .env ] && set -a && . ./.env && set +a
FOYD="${POSTGRES_USER:-innasoft}"
BAZA="${POSTGRES_DB:-innasoft}"

echo "[$(date +%T)] Baza zaxirasi: $BAZA"
# Avval vaqtinchalik nomga yoziladi: dump yarmida uzilib qolsa,
# buzuq fayl to'g'ri nom bilan qolib, «zaxira bor» degan yolg'on
# tinchlikni bermasin.
docker compose exec -T db pg_dump -U "$FOYD" "$BAZA" \
  | gzip > "$QAYERGA/.baza-$SANA.sql.gz.tmp"
mv "$QAYERGA/.baza-$SANA.sql.gz.tmp" "$QAYERGA/baza-$SANA.sql.gz"

echo "[$(date +%T)] Rasmlar zaxirasi"
docker run --rm \
  -v innasoft_platforma_innasoft_uploads:/data:ro \
  -v "$QAYERGA":/zaxira \
  alpine tar czf "/zaxira/rasmlar-$SANA.tar.gz" -C /data . 2>/dev/null \
  || echo "  · rasmlar hajmi bo'sh yoki volume nomi boshqa — o'tkazib yuborildi"

echo "[$(date +%T)] $SAQLASH_KUN kundan eski zaxiralar o'chirilmoqda"
find "$QAYERGA" -name 'baza-*.sql.gz'    -mtime "+$SAQLASH_KUN" -delete
find "$QAYERGA" -name 'rasmlar-*.tar.gz' -mtime "+$SAQLASH_KUN" -delete

echo "[$(date +%T)] Tayyor:"
ls -lh "$QAYERGA" | tail -5
