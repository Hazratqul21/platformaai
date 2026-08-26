#!/usr/bin/env python3
"""CSV ZAXIRA — akkaunt ma'lumotini odam o'qiydigan ko'rinishda saqlaydi.

    .venv/bin/python tools/csv_zaxira.py                    # hamma jadval
    .venv/bin/python tools/csv_zaxira.py --qayerga /yo'l    # boshqa papkaga
    .venv/bin/python tools/csv_zaxira.py --jadval kassa_entries

NEGA `pg_dump` DAN TASHQARI. `zaxira.sh` ning SQL dumpi tiklash uchun,
lekin uni Excel'da ochib bo'lmaydi va ichida nima borligini ko'rish
uchun bazaga tiklash kerak. CSV esa mijozga ham, bizga ham darrov
o'qiladi: «bilyardda nima bor edi» degan savolga fayl ochib javob
beriladi.

HECH NARSA YOZMAYDI — faqat `SELECT`. Manba bazaga ta'siri yo'q.

MAXFIYLIK: `users.password_hash` va `auth_tokens.token` ustunlari
CSV ga TUSHMAYDI. Zaxira fayli qo'ldan-qo'lga o'tadi, parol xeshi va
sessiya tokeni esa unda yotmasligi kerak.
"""
import argparse
import csv
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text                 # noqa: E402
from app.db import engine                            # noqa: E402

KOK, SARIQ, TUGA = "\033[92m", "\033[93m", "\033[0m"

# Zaxiraga TUSHMAYDIGAN ustunlar: jadval -> {ustunlar}
SIR_USTUNLAR = {
    "users": {"password_hash"},
    "auth_tokens": {"token"},
    "settings": set(),          # sozlamalar ochiq — sir emas
}


def zaxira(qayerga: Path, faqat: str = "") -> dict:
    insp = inspect(engine)
    jadvallar = sorted(insp.get_table_names())
    if faqat:
        jadvallar = [j for j in jadvallar if j == faqat]
        if not jadvallar:
            sys.exit(f"❌ '{faqat}' jadvali topilmadi")

    qayerga.mkdir(parents=True, exist_ok=True)
    hisob = {"jadval": 0, "qator": 0, "bosh": 0, "yashirilgan_ustun": 0}

    with engine.connect() as conn:
        for jadval in jadvallar:
            ustunlar = [c["name"] for c in insp.get_columns(jadval)]
            sir = SIR_USTUNLAR.get(jadval, set())
            olinadi = [u for u in ustunlar if u not in sir]
            hisob["yashirilgan_ustun"] += len(ustunlar) - len(olinadi)
            if not olinadi:
                continue

            nomlar = ", ".join(f'"{u}"' for u in olinadi)
            qatorlar = conn.execute(
                text(f'SELECT {nomlar} FROM "{jadval}"')).fetchall()
            if not qatorlar:
                hisob["bosh"] += 1
                continue

            fayl = qayerga / f"{jadval}.csv"
            with fayl.open("w", newline="", encoding="utf-8-sig") as f:
                # `utf-8-sig` — Excel kirill va o'zbek harflarini
                # BOM'siz buzib ochadi (mijozga yuboriladigan fayl).
                yozuvchi = csv.writer(f)
                yozuvchi.writerow(olinadi)
                for q in qatorlar:
                    yozuvchi.writerow(
                        ["" if v is None else v for v in q])
            hisob["jadval"] += 1
            hisob["qator"] += len(qatorlar)
            print(f"  {jadval:<24} {len(qatorlar):>6} qator")

    return hisob


def main():
    p = argparse.ArgumentParser(description="Akkaunt ma'lumotini CSV ga")
    p.add_argument("--qayerga", default="",
                   help="Papka (standart: zaxira/csv-<sana>)")
    p.add_argument("--jadval", default="", help="Faqat bitta jadval")
    a = p.parse_args()

    sana = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    qayerga = Path(a.qayerga) if a.qayerga else \
        Path(__file__).resolve().parent.parent / "zaxira" / f"csv-{sana}"

    print(f"\nManba (faqat o'qish): {engine.url.database}")
    print(f"Qayerga: {qayerga}\n")
    h = zaxira(qayerga, a.jadval)

    print(f"\n{'='*46}")
    print(f"  fayl (jadval)      {h['jadval']:>6}")
    print(f"  jami qator         {h['qator']:>6}")
    print(f"  bo'sh jadval       {h['bosh']:>6}  (fayl yasalmadi)")
    if h["yashirilgan_ustun"]:
        print(f"  {SARIQ}yashirilgan ustun  {h['yashirilgan_ustun']:>6}"
              f"  (parol xeshi, token){TUGA}")
    print(f"{'='*46}")
    print(f"{KOK}✅ CSV zaxira tayyor{TUGA}")


if __name__ == "__main__":
    main()
