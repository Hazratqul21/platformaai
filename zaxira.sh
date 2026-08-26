#!/usr/bin/env bash
# ============================================================
#  ZAXIRA — HAMMA baza + yuklangan rasmlar
#
#  Kunlik cron uchun:
#      0 3 * * * /opt/innasoft/zaxira.sh >> /var/log/innasoft-zaxira.log 2>&1
#
#  NEGA HAMMASI. Ilgari bu skript FAQAT bitta bazani (`innasoft`)
#  olardi. Ijarachilikda esa har mijoz ALOHIDA bazada yashaydi
#  (`inna_karton`, `inna_mebel`...), akkauntlar ro'yxati esa uchinchi
#  bazada (boshqaruv). Ya'ni mijoz ma'lumotining zaxirasi umuman
#  olinmasdi — «zaxira bor» degan yolg'on tinchlik bilan. Endi
#  serverdagi HAR bir baza alohida faylga olinadi.
#
#  Tiklash (bitta baza):
#      gunzip -c zaxira/baza-inna_karton-2026-08-26-0300.sql.gz | \
#        docker compose exec -T db psql -U innasoft -d inna_karton
#
#      Baza yo'q bo'lsa avval yaratiladi:
#        docker compose exec -T db createdb -U innasoft inna_karton
#
#      Rasmlar: tar xzf zaxira/rasmlar-<sana>.tar.gz -C /
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

XATO=0

# Serverdagi hamma baza. Shablon bazalar va ulanib bo'lmaydiganlar
# tashlab ketiladi. Ro'yxat QO'LDA yozilmaydi: yangi mijoz qo'shilganda
# uni bu yerga ham yozish esdan chiqardi va aynan yangi mijozning
# ma'lumoti zaxirasiz qolardi.
BAZALAR="$(docker compose exec -T db psql -U "$FOYD" -d postgres -Atc \
  "SELECT datname FROM pg_database
    WHERE datallowconn AND datname NOT IN ('postgres','template0','template1')
    ORDER BY datname")" || {
    echo "❌ Bazalar ro'yxati olinmadi — zaxira bajarilmadi"
    exit 1
}

if [ -z "$BAZALAR" ]; then
    echo "❌ Birorta ham baza topilmadi — bu shubhali, tekshiring"
    exit 1
fi

for BAZA in $BAZALAR; do
    echo "[$(date +%T)] Baza zaxirasi: $BAZA"
    # Avval vaqtinchalik nomga yoziladi: dump yarmida uzilib qolsa,
    # buzuq fayl to'g'ri nom bilan qolib, «zaxira bor» degan yolg'on
    # tinchlikni bermasin.
    VAQT="$QAYERGA/.baza-$BAZA-$SANA.sql.gz.tmp"
    if docker compose exec -T db pg_dump -U "$FOYD" "$BAZA" | gzip > "$VAQT"; then
        # Bo'sh yoki juda kichik fayl — dump ishlamagan degani.
        OLCHAM="$(wc -c < "$VAQT" | tr -d ' ')"
        if [ "$OLCHAM" -lt 100 ]; then
            echo "  ❌ $BAZA — dump bo'sh chiqdi ($OLCHAM bayt)"
            rm -f "$VAQT"; XATO=1; continue
        fi
        mv "$VAQT" "$QAYERGA/baza-$BAZA-$SANA.sql.gz"
        echo "  ✅ $BAZA — $(du -h "$QAYERGA/baza-$BAZA-$SANA.sql.gz" | cut -f1)"
    else
        echo "  ❌ $BAZA — pg_dump yiqildi"
        rm -f "$VAQT"; XATO=1
    fi
done

echo "[$(date +%T)] Rasmlar zaxirasi"
# VOLUME NOMI TOPILADI, QOTIRILMAYDI. Compose loyiha nomi papkadan
# olinadi: `/opt/innasoft` -> `innasoft_...`, `/var/www/innasoft-platforma`
# -> `innasoft-platforma_...` (tire bilan). Qotirilgan nom tufayli prodda
# rasm zaxirasi HECH QACHON olinmagan — skript "o'tkazib yuborildi" deb
# yozardi va buni hech kim sezmasdi.
VOLUME="$(docker volume ls --format '{{.Name}}' \
          | grep -E '_innasoft_uploads$' | head -1)"
if [ -z "$VOLUME" ]; then
    echo "  ⚠️  uploads volume topilmadi — rasmlar zaxiralanmadi"
    XATO=1
else
    if docker run --rm -v "$VOLUME":/data:ro -v "$QAYERGA":/zaxira \
         alpine tar czf "/zaxira/rasmlar-$SANA.tar.gz" -C /data . 2>/dev/null; then
        echo "  ✅ $VOLUME — $(du -h "$QAYERGA/rasmlar-$SANA.tar.gz" | cut -f1)"
    else
        echo "  ⚠️  rasmlar zaxiralanmadi ($VOLUME)"
        XATO=1
    fi
fi

echo "[$(date +%T)] $SAQLASH_KUN kundan eski zaxiralar o'chirilmoqda"
find "$QAYERGA" -name 'baza-*.sql.gz'    -mtime "+$SAQLASH_KUN" -delete
find "$QAYERGA" -name 'rasmlar-*.tar.gz' -mtime "+$SAQLASH_KUN" -delete
# Yarmida uzilib qolgan vaqtinchalik fayllar ham qolib ketmasin
find "$QAYERGA" -name '.baza-*.tmp' -mtime +1 -delete 2>/dev/null || true

echo "[$(date +%T)] Tayyor:"
ls -lh "$QAYERGA" | tail -8

if [ "$XATO" -ne 0 ]; then
    echo "❌ Ba'zi bazalar olinmadi (yuqoriga qarang) — cron logini tekshiring"
    exit 1
fi
echo "✅ Hamma baza zaxiralandi"
