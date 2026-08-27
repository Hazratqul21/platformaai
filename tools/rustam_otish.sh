#!/usr/bin/env bash
# =====================================================================
#  RUSTAM AKA — YAKUNIY O'TISH
#
#  Serverda ishga tushiriladi:   sudo bash tools/rustam_otish.sh
#
#  MANTIQ: har qadamdan keyin TEKSHIRUV bor va tekshiruv yiqilsa
#  skript SHU YERDA to'xtaydi. Yarim ko'chgan holatda oldinga
#  yurmaydi — chunki eski tizim hali joyida turadi va orqaga
#  qaytish bir buyruq.
#
#  ESKI TIZIM O'CHIRILMAYDI. U faqat to'xtatiladi. Fayllari,
#  bazasi, systemd birligi — hammasi joyida qoladi.
# =====================================================================
set -euo pipefail

KOD="tizim"
BAZA="inna_tizim"
ESKI_DB="/var/www/tizim/gofra_erp.db"
ESKI_UPLOADS="/var/www/tizim/uploads"
SANA=$(date +%F-%H%M%S)
ISH="/tmp/otish-$SANA"
ZAXIRA="/var/www/innasoft-platforma/zaxira/rustam-otish-$SANA"

mkdir -p "$ISH" "$ZAXIRA"

qadam(){ printf "\n\033[1;36m▶ %s\033[0m\n" "$*"; }
xato(){ printf "\n\033[1;31m✖ TO'XTATILDI: %s\033[0m\n" "$*"; echo
        echo "Ma'lumot YO'QOLMADI: eski baza faqat o'qildi, o'zgartirilmadi."
        echo
        echo "QAYTARISH (qaysi qadamda to'xtagan bo'lsa ham ishlaydi):"
        echo "  sudo bash tools/rustam_qaytarish.sh $ZAXIRA"
        exit 1; }
ok(){ printf "  \033[1;32m✓\033[0m %s\n" "$*"; }

# ---------------------------------------------------------------- 1
qadam "1/10  Old tekshiruv"
[ -f "$ESKI_DB" ] || xato "eski baza topilmadi: $ESKI_DB"
docker ps --format '{{.Names}}' | grep -qx innasoft-app || xato "innasoft-app ishlamayapti"
docker ps --format '{{.Names}}' | grep -qx innasoft-db  || xato "innasoft-db ishlamayapti"
BOSH=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
[ "$BOSH" -ge 5 ] || xato "diskda joy kam: ${BOSH}G"
docker exec innasoft-db psql -U innasoft -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname='$BAZA'" | grep -q 1 \
  && xato "'$BAZA' allaqachon bor — avval uni ko'rib chiqing"
ok "hamma shart bajarildi (bo'sh joy ${BOSH}G)"

# ---------------------------------------------------------------- 2
qadam "2/10  Zaxira (o'tishdan OLDINGI holat)"
cp "$ESKI_DB" "$ZAXIRA/gofra_erp.db"
tar czf "$ZAXIRA/uploads.tar.gz" -C "$(dirname "$ESKI_UPLOADS")" "$(basename "$ESKI_UPLOADS")"
cp /etc/nginx/sites-enabled/tizim "$ZAXIRA/nginx-tizim.conf" 2>/dev/null || true
ok "$ZAXIRA ($(du -sh "$ZAXIRA" | cut -f1))"

# ---------------------------------------------------------------- 3
qadam "3/10  Eski tizim TO'XTATILADI — shu yerdan uzilish boshlanadi"
systemctl stop tizim.service
sleep 2
systemctl is-active tizim.service >/dev/null && xato "to'xtamadi"
UZILISH_BOSHI=$(date +%s)
ok "to'xtadi $(date +%H:%M:%S)"

# ---------------------------------------------------------------- 4
qadam "4/10  Yakuniy nusxa (to'xtagandan KEYIN — eng so'nggi holat)"
python3 - <<PY
import sqlite3
a=sqlite3.connect("file:$ESKI_DB?mode=ro", uri=True)
b=sqlite3.connect("$ISH/manba.db"); a.backup(b); b.close(); a.close()
PY
python3 -c "
import sqlite3,sys
c=sqlite3.connect('$ISH/manba.db')
assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
print('  buyurtma:', c.execute('SELECT count(*) FROM orders').fetchone()[0],
      'kassa:', c.execute('SELECT count(*) FROM kassa_entries').fetchone()[0])
" || xato "nusxa buzuq"
ok "olindi va butunligi tekshirildi"

# ---------------------------------------------------------------- 5
qadam "5/10  Akkaunt yozuvi va bazasi (profil: karton)"
docker cp "$ISH/manba.db" innasoft-app:/tmp/manba.db >/dev/null
# `-i` SHART: usiz `docker exec` stdin ni konteynerga uzatmaydi va
# `python -` BO'SH kirish o'qib, hech nima qilmasdan 0 bilan chiqadi.
# Ya'ni qadam «bajarildi» ko'rinadi, aslida hech nima bo'lmaydi.
# Aynan shu 2026-08-28 dagi birinchi urinishni yiqitdi.
docker exec -i innasoft-app python - <<'PY' || xato "akkaunt yaratilmadi"
from app.platforma import xizmat, tayyorlash
from app.platforma.db import BoshqaruvSession
import app.platforma.models as pm
b = BoshqaruvSession()
try:
    bor = b.query(pm.Akkaunt).filter(pm.Akkaunt.kod == "tizim").first()
    if bor is None:
        xizmat.akkaunt_yarat(b, "tizim", "Rustam aka — Gofra Karton sexi",
                             kim="ko'chirish")
        print("  akkaunt yozuvi yaratildi")
    else:
        print("  akkaunt yozuvi allaqachon bor")
finally:
    b.close()
tayyorlash.akkaunt_tayyorla("inna_tizim",
                            admin_parol="vaqtinchalik-kochirishda-almashadi",
                            profil_kaliti="karton")
print("  baza va sxema tayyor")
PY
# ISHONMAYMIZ, TEKSHIRAMIZ: baza rostdan yaratildimi.
docker exec innasoft-db psql -U innasoft -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname='$BAZA'" | grep -q 1 \
  || xato "5-qadam bajarilgandek ko'rindi, lekin '$BAZA' bazasi yaratilmagan"
ok "akkaunt tayyor va baza mavjudligi tekshirildi"

# ---------------------------------------------------------------- 6
qadam "6/10  Ma'lumot ko'chirilmoqda (--kirish: sessiyalar ham)"
docker exec innasoft-app sh -c '
  export DATABASE_URL=$(python -c "
import os
print(os.environ[\"MIJOZ_DB_SHABLON\"].replace(\"{baza}\", \"inna_tizim\"))
")
  python tools/kochir.py /tmp/manba.db --kirish' || xato "ko'chirish yiqildi"
ok "ko'chirildi"

# ---------------------------------------------------------------- 7
qadam "7/10  ISBOT — manbada nima bor edi, platformaga nima yetdi"
docker exec innasoft-app sh -c '
  export DATABASE_URL=$(python -c "
import os
print(os.environ[\"MIJOZ_DB_SHABLON\"].replace(\"{baza}\", \"inna_tizim\"))
")
  python tools/solishtir.py /tmp/manba.db' || xato "MA'LUMOT YO'QOLGAN — o'tish bekor"
ok "hech narsa yo'qolmadi"

# ---------------------------------------------------------------- 8
qadam "8/10  Rasm fayllari"
docker exec innasoft-app mkdir -p "/app/uploads/$BAZA"
if [ -d "$ESKI_UPLOADS" ]; then
  docker cp "$ESKI_UPLOADS/." "innasoft-app:/app/uploads/$BAZA/" >/dev/null
fi
MANBA_N=$(find "$ESKI_UPLOADS" -type f 2>/dev/null | wc -l)
YANGI_N=$(docker exec innasoft-app sh -c "find /app/uploads/$BAZA -type f | wc -l")
echo "  manbada $MANBA_N, ko'chdi $YANGI_N"
[ "$YANGI_N" -ge "$MANBA_N" ] || xato "rasm kam ko'chdi"
ok "rasmlar joyida"

# ---------------------------------------------------------------- 9
qadam "9/10  nginx — tizim.innasoft.uz platformaga qaratiladi"
# Wildcard `*.innasoft.uz` allaqachon platformaga (8100) qaraydi.
# Shuning uchun ALOHIDA `tizim` qoidasini olib qo'yish yetarli.
mv /etc/nginx/sites-enabled/tizim "$ZAXIRA/nginx-tizim.disabled" 2>/dev/null || true
nginx -t || { mv "$ZAXIRA/nginx-tizim.disabled" /etc/nginx/sites-enabled/tizim
              nginx -t && systemctl reload nginx
              xato "nginx sozlamasi yaroqsiz — qaytarildi"; }
systemctl reload nginx
ok "qaratildi"

# --------------------------------------------------------------- 10
qadam "10/10  Yakuniy tekshiruv"
sleep 3
KOD_HTTP=$(curl -sS -m 20 -o /dev/null -w '%{http_code}' https://tizim.innasoft.uz/)
[ "$KOD_HTTP" = "200" ] || xato "tizim.innasoft.uz javob bermadi ($KOD_HTTP)"
UZILISH=$(( $(date +%s) - UZILISH_BOSHI ))
ok "tizim.innasoft.uz -> 200"
printf "\n\033[1;32m✅ O'TISH TUGADI\033[0m — uzilish: %s soniya\n\n" "$UZILISH"

cat <<SON
Zaxira:  $ZAXIRA
Eski tizim TO'XTATILGAN, lekin O'CHIRILMAGAN.

ORQAGA QAYTARISH (bir daqiqa ichida):
  cp $ZAXIRA/nginx-tizim.disabled /etc/nginx/sites-enabled/tizim
  nginx -t && systemctl reload nginx
  systemctl start tizim.service

Bir necha hafta kuzatilgach, eski tizimni o'chirish mumkin.
SON
