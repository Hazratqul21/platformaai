#!/usr/bin/env bash
# =====================================================================
#  XAVFSIZ DEPLOY — bitta buyruq, git'dan, tekshiruv bilan
#
#      bash tools/deploy.sh
#
#  NEGA BU KERAK (2026-08-28):
#  Ilgari deploy qo'lda `scp` + `docker cp` bilan, har safar fayllarni
#  TANLAB qilinardi. Bir kuni `innasoft.html` tanlovga kirmay qoldi va
#  korporativ sayt 500 berdi. Bu skript hech narsa tanlamaydi:
#  commit qilingan HOLATNI TO'LIQ oladi (`git archive HEAD`), demak
#  fayl unutish jismonan imkonsiz.
#
#  SUDO KERAK EMAS: docker foydalanuvchi guruhida, /var/www/... esa
#  foydalanuvchiniki. `.env`, `docker-compose.yml`, `zaxira/`,
#  `uploads/` — TEGILMAYDI (paketga umuman kirmaydi).
# =====================================================================
set -euo pipefail

SRV="xazratabduraufov@138.249.248.172"
JOY="/var/www/innasoft-platforma"
KONT="innasoft-app"
SANA=$(date +%F-%H%M%S)
ISH="/tmp/deploy-$SANA"

ok(){   printf "  \033[1;32m✓\033[0m %s\n" "$*"; }
qadam(){ printf "\n\033[1;36m▶ %s\033[0m\n" "$*"; }
xato(){ printf "\n\033[1;31m✖ DEPLOY TO'XTADI: %s\033[0m\n" "$*"; exit 1; }

cd "$(git rev-parse --show-toplevel)"

# ---------------------------------------------------------------- 1
qadam "1/6  Git holati"
REV=$(git rev-parse --short HEAD)
if [ -n "$(git status --porcelain)" ]; then
  printf "  \033[1;33m•\033[0m Commit qilinmagan o'zgarishlar bor — ular DEPLOY QILINMAYDI.\n"
  printf "    Faqat oxirgi commit (%s) chiqadi. Davom etilsinmi? [ha/yo'q] " "$REV"
  read -r javob
  [ "$javob" = "ha" ] || xato "bekor qilindi — avval commit qiling"
fi
ok "commit $REV chiqariladi"

# ---------------------------------------------------------------- 2
qadam "2/6  Mahalliy tekshiruv (gate) — qizil bo'lsa prodga chiqmaydi"
XATOLAR=0
while IFS= read -r f; do
  node --check "$f" 2>/dev/null || { echo "    JS xato: $f"; XATOLAR=$((XATOLAR+1)); }
done < <(find static/js -name '*.py' -prune -o -name '*.js' -print)
[ "$XATOLAR" -eq 0 ] || xato "$XATOLAR ta JS faylda sintaksis xatosi"
ok "barcha JS sintaksisi to'g'ri"

if [ -x .venv/bin/python ] && [ -f tools/ui_static_check.py ]; then
  .venv/bin/python tools/ui_static_check.py >/dev/null 2>&1 || xato "UI static check yiqildi"
  ok "UI static check o'tdi"
fi

python3 -c "import ast, glob, sys
for f in glob.glob('app/**/*.py', recursive=True):
    try: ast.parse(open(f).read())
    except SyntaxError as e: print('    Python xato:', f, e); sys.exit(1)
" || xato "app/ da Python sintaksis xatosi"
ok "app/ Python sintaksisi to'g'ri"

# ---------------------------------------------------------------- 3
qadam "3/6  Paket (git archive HEAD — to'liq, tanlovsiz)"
mkdir -p "$ISH"
git archive HEAD app static tools | tar -x -C "$ISH"
FAYL=$(find "$ISH" -type f | wc -l | tr -d ' ')
[ "$FAYL" -gt 50 ] || xato "paket juda kichik ($FAYL fayl) — nimadir noto'g'ri"
ok "$FAYL fayl paketlandi"

# ---------------------------------------------------------------- 4
qadam "4/6  Serverga yuborish va zaxira"
tar czf "$ISH.tar.gz" -C "$ISH" app static tools
scp -q -o BatchMode=yes -o ConnectTimeout=25 "$ISH.tar.gz" "$SRV:/tmp/deploy.tar.gz" \
  || xato "serverga ulanib bo'lmadi"
ssh -o BatchMode=yes -o ConnectTimeout=25 "$SRV" bash -s <<REMOTE || xato "server tomonida xato"
set -euo pipefail
# Deploy oldidan zaxira (app + static)
tar czf /tmp/prod-oldin-$SANA.tar.gz -C "$JOY" app static 2>/dev/null
echo "    zaxira: /tmp/prod-oldin-$SANA.tar.gz"
rm -rf /tmp/dep-$SANA && mkdir -p /tmp/dep-$SANA
tar xzf /tmp/deploy.tar.gz -C /tmp/dep-$SANA
# Manba papka (.env, compose, zaxira, uploads tegilmaydi)
cp -r /tmp/dep-$SANA/app/. "$JOY/app/"
cp -r /tmp/dep-$SANA/static/. "$JOY/static/"
cp -r /tmp/dep-$SANA/tools/. "$JOY/tools/"
echo "$REV" > "$JOY/VERSION"
# Konteynerga
docker cp /tmp/dep-$SANA/app/.    $KONT:/app/app/
docker cp /tmp/dep-$SANA/static/. $KONT:/app/static/
docker cp /tmp/dep-$SANA/tools/.  $KONT:/app/tools/
docker cp "$JOY/VERSION"          $KONT:/app/VERSION
rm -rf /tmp/dep-$SANA /tmp/deploy.tar.gz
REMOTE
ok "yuborildi va zaxira olindi"

# ---------------------------------------------------------------- 5
qadam "5/6  Konteyner qayta ishga tushirilmoqda"
ssh -o BatchMode=yes -o ConnectTimeout=25 "$SRV" "docker restart $KONT" >/dev/null \
  || xato "restart yiqildi"
ok "restart bajarildi"

# ---------------------------------------------------------------- 6
qadam "6/6  Deploydan keyingi tekshiruv"
sleep 8
H=$(ssh -o BatchMode=yes "$SRV" "docker exec $KONT sh -c 'curl -sS -m 5 -o /dev/null -w %{http_code} http://localhost:8000/api/health'" 2>/dev/null || echo 000)
[ "$H" = "200" ] || xato "ilova ko'tarilmadi (/api/health -> $H). ORQAGA: server zaxirasidan tiklang: /tmp/prod-oldin-$SANA.tar.gz"
ok "ilova ichida /api/health 200"

BUZUQ=0
for h in billiard karton mebel test; do
  K=$(curl -sS -m 15 -o /dev/null -w '%{http_code}' "https://$h.innasoft.uz/api/health" 2>/dev/null || echo 000)
  if [ "$K" = "200" ]; then ok "$h.innasoft.uz -> 200"
  else printf "  \033[1;31m✗\033[0m %s -> %s\n" "$h.innasoft.uz" "$K"; BUZUQ=$((BUZUQ+1)); fi
done
[ "$BUZUQ" -eq 0 ] || xato "$BUZUQ ta akkaunt javob bermadi — zaxiradan tiklashni ko'ring"

rm -rf "$ISH" "$ISH.tar.gz"
printf "\n\033[1;32m✅ DEPLOY TUGADI\033[0m — versiya %s jonli\n" "$REV"
