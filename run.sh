#!/usr/bin/env bash
# TIZIM — ishga tushirish skripti
set -e
cd "$(dirname "$0")"

PY=python3
for cand in python3.13 python3.12 python3.11 python3.10; do
  if command -v "$cand" >/dev/null 2>&1; then PY=$cand; break; fi
done
if [ ! -d .venv ]; then
  echo "→ Virtual muhit yaratilmoqda ($PY)..."
  "$PY" -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
if [ "$SEED_DEMO" = "1" ]; then
  echo "→ DEMO rejim: sinov ma'lumotlari bilan"
elif [ "$SEED_EMPTY" = "1" ]; then
  echo "→ BO'SH rejim: noldan boshlanadi"
else
  echo "→ Birinchi ishga tushirishda Excel ma'lumotlaringiz yuklanadi (xarid + kassa)"
fi
echo "→ Server: http://localhost:${PORT:-8000}  (Ctrl+C — to'xtatish)"
python -m app.main
