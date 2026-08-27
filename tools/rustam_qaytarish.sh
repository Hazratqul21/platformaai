#!/usr/bin/env bash
# =====================================================================
#  RUSTAM AKA — ORQAGA QAYTARISH
#
#      sudo bash tools/rustam_qaytarish.sh [zaxira-papkasi]
#
#  O'tish qaysi qadamda to'xtagan bo'lsa ham ishlaydi: har bir
#  qadamni ALOHIDA tekshiradi va faqat kerak bo'lganini qaytaradi.
#
#  MUHIM CHEGARA
#  Bu skript ESKI TIZIMNI o'z holiga qaytaradi. Agar o'tishdan
#  keyin odamlar YANGI tizimga ma'lumot kiritgan bo'lsa, o'sha
#  yozuvlar eski tizimda YO'Q — ular platformaning `inna_tizim`
#  bazasida qoladi. Shuning uchun qaytarish o'tishdan keyingi
#  dastlabki soatlarda toza bo'ladi, keyin esa ikki bazani
#  qo'lda birlashtirish kerak bo'ladi.
# =====================================================================
set -uo pipefail

ok(){   printf "  \033[1;32m✓\033[0m %s\n" "$*"; }
diqq(){ printf "  \033[1;33m•\033[0m %s\n" "$*"; }
qadam(){ printf "\n\033[1;36m▶ %s\033[0m\n" "$*"; }

ZAXIRA="${1:-}"
if [ -z "$ZAXIRA" ]; then
  ZAXIRA=$(ls -1dt /var/www/innasoft-platforma/zaxira/rustam-otish-* 2>/dev/null | head -1)
fi
# DIQQAT: standart qiymatni `${VAR:-...}` ichiga yozib bo'lmaydi —
# u yerdagi apostrof (masalan «qo'lda») tirnoq ochib yuboradi va
# butun skript parse bo'lmaydi. Shuning uchun alohida `if`.
if [ -n "$ZAXIRA" ]; then
  echo "Zaxira papkasi: $ZAXIRA"
else
  echo "Zaxira papkasi topilmadi — nginx qoidasi boshqa manbadan tiklanadi"
fi

# ------------------------------------------------------------------ 1
qadam "1/4  nginx — tizim.innasoft.uz eski tizimga qaytariladi"
if [ -f /etc/nginx/sites-enabled/tizim ]; then
  ok "qoida allaqachon joyida — tegilmadi"
else
  MANBA=""
  [ -n "$ZAXIRA" ] && [ -f "$ZAXIRA/nginx-tizim.disabled" ] && MANBA="$ZAXIRA/nginx-tizim.disabled"
  [ -z "$MANBA" ] && [ -n "$ZAXIRA" ] && [ -f "$ZAXIRA/nginx-tizim.conf" ] && MANBA="$ZAXIRA/nginx-tizim.conf"
  [ -z "$MANBA" ] && [ -f /etc/nginx/sites-available/tizim ] && MANBA=/etc/nginx/sites-available/tizim
  if [ -n "$MANBA" ]; then
    cp "$MANBA" /etc/nginx/sites-enabled/tizim
    if nginx -t 2>/dev/null; then
      systemctl reload nginx; ok "qaytarildi ($MANBA)"
    else
      rm -f /etc/nginx/sites-enabled/tizim
      diqq "qoida yaroqsiz — olib tashlandi, nginx tegilmadi"
    fi
  else
    diqq "nginx qoidasi topilmadi — qo'lda tiklash kerak"
  fi
fi

# ------------------------------------------------------------------ 2
qadam "2/4  Eski tizim ishga tushiriladi"
systemctl start tizim.service 2>/dev/null || true
sleep 3
if systemctl is-active --quiet tizim.service; then
  ok "tizim.service ishlayapti"
else
  diqq "ISHGA TUSHMADI — jurnal: journalctl -u tizim.service -n 40"
fi

# ------------------------------------------------------------------ 3
qadam "3/4  Yarim ko'chgan platforma bazasi"
BOR=$(docker exec innasoft-db psql -U innasoft -d postgres -tAc \
      "SELECT 1 FROM pg_database WHERE datname='inna_tizim'" 2>/dev/null)
if [ "$BOR" = "1" ]; then
  diqq "«inna_tizim» bazasi bor. U TEGILMAYDI — ichida ma'lumot"
  diqq "bo'lishi mumkin. Ko'rib chiqib, keraksiz bo'lsa:"
  echo "      docker exec innasoft-db psql -U innasoft -d postgres -c \\"
  echo "        \"DROP DATABASE inna_tizim;\""
  echo "      va boshqaruv bazasidan akkaunt yozuvini oling:"
  echo "      docker exec innasoft-db psql -U innasoft -d boshqaruv -c \\"
  echo "        \"DELETE FROM akkauntlar WHERE kod='tizim';\""
else
  ok "platforma bazasi yaratilmagan — tozalash kerak emas"
fi

# ------------------------------------------------------------------ 4
qadam "4/4  Tekshiruv"
sleep 2
K=$(curl -sS -m 20 -o /dev/null -w '%{http_code}' https://tizim.innasoft.uz/ 2>/dev/null)
if [ "$K" = "200" ]; then
  ok "tizim.innasoft.uz -> 200"
else
  diqq "tizim.innasoft.uz -> $K"
  diqq "DNS keshini kuting yoki: journalctl -u tizim.service -n 40"
fi

if [ -n "$ZAXIRA" ] && [ -f "$ZAXIRA/gofra_erp.db" ]; then
  echo
  echo "Baza zaxirasi: $ZAXIRA/gofra_erp.db"
  echo "Uni tiklash SHART EMAS — o'tish jonli faylni O'ZGARTIRMAYDI,"
  echo "faqat o'qiydi. Bu nusxa faqat ehtiyot uchun."
fi
printf "\n\033[1;32m✅ QAYTARISH TUGADI\033[0m\n"
