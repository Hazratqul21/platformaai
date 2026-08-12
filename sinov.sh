#!/usr/bin/env bash
# ============================================================
#  TO'LIQ SINOV — uchala to'plam, har biri TOZA bazada
#
#      ./sinov.sh
#
#  e2e_test.py holatga bog'liq (foydalanuvchi yaratadi, parol
#  almashtiradi), shuning uchun har to'plamdan oldin baza tozalanadi —
#  aks holda ikkinchi yurishda «Bu login band» chiqadi va sinov
#  o'z-o'zidan yiqiladi, kodda hech qanday xato bo'lmasa ham.
# ============================================================
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PORT="${APP_PORT:-8070}"
BAZA="http://localhost:$PORT"
PY="${PY:-.venv/bin/python}"
BAZA_URL="postgresql://${POSTGRES_USER:-innasoft}:${POSTGRES_PASSWORD:-innasoft}@localhost:${POSTGRES_PORT:-5440}/${POSTGRES_DB:-innasoft}"
XATO=0

qayta_tikla() {   # $1 = SEED_DEMO | SEED_EMPTY
    docker compose down -v >/dev/null 2>&1
    env "$1=1" docker compose up -d >/dev/null 2>&1
    for _ in $(seq 40); do
        curl -fsS "$BAZA/api/health" >/dev/null 2>&1 && return 0
        sleep 1
    done
    echo "❌ Server $BAZA da ko'tarilmadi"
    docker compose logs app --tail=20
    exit 1
}

yurgiz() {        # $1 = sarlavha, $2 = seed rejimi, $3 = test fayli
    echo
    echo "════════ $1"
    qayta_tikla "$2"
    BASE="$BAZA" "$PY" "$3" || XATO=1
}

# Serversiz — kod ustidan. Eng arzoni birinchi yurgiziladi.
echo
echo "════════ HIMOYA AUDITI — endpointlar himoyalanganmi"
"$PY" tests/himoya_audit.py || XATO=1

echo
echo "════════ GenUI — komponent tekshiruvi va xavfsizligi"
"$PY" tests/genui_test.py || XATO=1

yurgiz "PROFIL MUVOFIQLIGI — 22 soha to'liq sikldan o'tadimi" \
       SEED_EMPTY tests/profil_test.py
yurgiz "CHUQUR SINOV — har sohada raqamlar to'g'rimi" \
       SEED_EMPTY tests/chuqur_sinov.py
yurgiz "KO'CHIRISH — eski tizimdan ma'lumot yo'qolmasdan o'tadimi" \
       SEED_EMPTY tests/kochirish_test.py
yurgiz "KARTON REGRESSIYASI — eski mijoz mantiqi buzilmadimi" \
       SEED_DEMO tests/e2e_test.py

echo
echo "════════ MODUL AUDITI — 38 endpoint jonli serverda"
"$PY" tests/audit.py "$PORT" || XATO=1

# 22 sohaga to'la demo ma'lumot yasab, butunlikni tekshiramiz. Bo'sh
# bazada ko'rinmaydigan muammolar (qarz yoshi, FIFO, qisman topshirish)
# aynan shu yerda chiqadi.
echo
echo "════════ JONLI AGENT — haqiqiy LLM (kalit bo'lsa)"
BASE="$BAZA" "$PY" tests/jonli_agent_test.py || XATO=1

echo
echo "════════ DEMO MA'LUMOT — 22 soha to'ldiriladi"
qayta_tikla SEED_EMPTY
DATABASE_URL="$BAZA_URL" "$PY" tools/demo_data.py --hammasi || XATO=1
echo
echo "════════ BUTUNLIK — to'la bazada raqamlar o'zaro mos keladimi"
DATABASE_URL="$BAZA_URL" "$PY" tools/butunlik.py || XATO=1

echo
if [ "$XATO" -eq 0 ]; then
    echo "✅ HAMMA SINOV O'TDI"
else
    echo "❌ Sinovlarda muammo bor (yuqoriga qarang)"
fi
exit "$XATO"
