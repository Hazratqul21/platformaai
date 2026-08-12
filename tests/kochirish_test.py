"""KO'CHIRISH SINOVI — eski TIZIM bazasidan ma'lumot yo'qolmasdan o'tadimi.

Haqiqiy mijoz bazasi bilan sinash eng ishonchlisi, lekin uni repoga
qo'yib bo'lmaydi (mijoz siri). Shuning uchun bu yerda eski sxemadagi
SQLite bazasi YASALADI, ko'chiriladi va tekshiriladi:

    yozuvlar soni      eski == yangi
    pul summasi        eski == yangi (tiyingacha)
    karton maydonlari  ustunlardan `attributes` ga to'g'ri o'tdimi
    manba fayl         O'ZGARMAGAN (checksum)

Oxirgi tekshiruv eng muhimi: vosita mijozning bazasiga hech qachon
yozmasligi kerak.

    BASE=http://localhost:8070 .venv/bin/python tests/kochirish_test.py
"""
import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

ILDIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ILDIZ))

XATOLAR = []


def tekshir(nom, shart, izoh=""):
    print(f"{'✓' if shart else '✗'} {nom}" + (f"  [{izoh}]" if not shart and izoh else ""))
    if not shart:
        XATOLAR.append(f"{nom}: {izoh}")


ESKI_SXEMA = """
CREATE TABLE clients (id INTEGER PRIMARY KEY, company VARCHAR(150),
  contact VARCHAR(100), phone VARCHAR(30), inn VARCHAR(20),
  pay_type VARCHAR(20), category VARCHAR(20), credit_limit NUMERIC,
  blacklisted BOOLEAN, firm VARCHAR(60), telegram_chat_id VARCHAR(30),
  created_at DATETIME, opening_balance NUMERIC, opening_date DATE);
CREATE TABLE suppliers (id INTEGER PRIMARY KEY, name VARCHAR(150),
  phone VARCHAR(30), kind VARCHAR(20));
CREATE TABLE materials (id INTEGER PRIMARY KEY, name VARCHAR(120),
  category VARCHAR(50), marka VARCHAR(60), manufacturer VARCHAR(80),
  grammaj VARCHAR(20), unit VARCHAR(20), last_price NUMERIC,
  stock_qty NUMERIC, min_stock NUMERIC, active BOOLEAN, created_at DATETIME);
CREATE TABLE raw_lots (id INTEGER PRIMARY KEY, lot_no VARCHAR(30),
  supplier_id INTEGER, grade VARCHAR(10), grammage INTEGER, qty_kg NUMERIC,
  remaining_kg NUMERIC, price_per_kg NUMERIC, received_at DATE);
CREATE TABLE orders (id INTEGER PRIMARY KEY, client_id INTEGER,
  length_mm INTEGER, width_mm INTEGER, height_mm INTEGER, layers INTEGER,
  grade VARCHAR(10), colors INTEGER, qty INTEGER, m2_per_box NUMERIC,
  unit_cost NUMERIC, unit_price NUMERIC, total NUMERIC,
  prepaid_percent INTEGER, status VARCHAR(30), note VARCHAR(300),
  created_at DATETIME, delivered_at DATE, due_date DATE,
  accepted_stamp BOOLEAN, product_name VARCHAR(100), payment_due_date DATE,
  is_offset BOOLEAN, tur VARCHAR(30), photo VARCHAR(200), delivered_qty INTEGER);
CREATE TABLE payments (id INTEGER PRIMARY KEY, client_id INTEGER,
  order_id INTEGER, amount NUMERIC, method VARCHAR(20), paid_at DATE,
  note VARCHAR(200));
CREATE TABLE kassa_entries (id INTEGER PRIMARY KEY, firm VARCHAR(60),
  direction VARCHAR(10), who VARCHAR(120), note VARCHAR(200), amount NUMERIC,
  currency VARCHAR(10), entry_at DATE, created_by VARCHAR(100));
CREATE TABLE employees (id INTEGER PRIMARY KEY, name VARCHAR(100),
  position VARCHAR(50), phone VARCHAR(30), rate_per_box NUMERIC,
  brigade VARCHAR(50), firm VARCHAR(60), active BOOLEAN);
"""


def eski_baza_yasa(yol: str) -> dict:
    """Eski sxemadagi namuna baza. Kutilgan yig'indilarni qaytaradi."""
    conn = sqlite3.connect(yol)
    conn.executescript(ESKI_SXEMA)
    bugun = date.today().isoformat()

    for i in range(1, 8):
        conn.execute(
            "INSERT INTO clients (id, company, contact, phone, category, "
            "credit_limit, blacklisted, opening_balance, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (i, f"Mijoz {i}", f"Aloqa {i}", f"9011122{i:02d}", "Standart",
             50_000_000, 0, i * 100_000, datetime.utcnow()))
    conn.execute("INSERT INTO suppliers (id,name,phone,kind) VALUES (1,'YB','90',"
                 "'xomashyo')")
    conn.execute("INSERT INTO materials (id,name,unit,last_price,stock_qty,"
                 "min_stock,active) VALUES (1,'Qog''oz','kg',3500,1000,100,1)")
    conn.execute("INSERT INTO raw_lots (id,lot_no,supplier_id,grade,grammage,"
                 "qty_kg,remaining_kg,price_per_kg,received_at) "
                 "VALUES (1,'LOT-1',1,'K1',140,500,300,3500,?)", (bugun,))

    buyurtma_jami = Decimal("0")
    for i in range(1, 13):
        narx, miqdor = Decimal("2500"), 1000 + i * 100
        jami = narx * miqdor
        buyurtma_jami += jami
        conn.execute(
            "INSERT INTO orders (id, client_id, length_mm, width_mm, height_mm,"
            " layers, grade, colors, qty, m2_per_box, unit_cost, unit_price,"
            " total, status, created_at, due_date, payment_due_date,"
            " is_offset, tur, delivered_qty, product_name) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (i, (i % 7) + 1, 300 + i, 200 + i, 150 + i, 3, "K1", i % 3,
             miqdor, "0.7250", 2000, float(narx), float(jami),
             "Yetkazib berildi", datetime.utcnow() - timedelta(days=i * 3),
             bugun, bugun, 0, "3 слой", miqdor, f"Quti {i}"))

    tolov_jami = Decimal("0")
    for i in range(1, 9):
        summa = Decimal("500000") * i
        tolov_jami += summa
        conn.execute("INSERT INTO payments (id,client_id,order_id,amount,method,"
                     "paid_at,note) VALUES (?,?,?,?,?,?,?)",
                     (i, (i % 7) + 1, i, float(summa), "Naqd", bugun, ""))

    kassa_jami = Decimal("0")
    for i in range(1, 21):
        summa = Decimal("100000") * i
        kassa_jami += summa
        conn.execute("INSERT INTO kassa_entries (id,firm,direction,who,note,"
                     "amount,currency,entry_at,created_by) VALUES (?,?,?,?,?,?,?,?,?)",
                     (i, "Asosiy", "Kirim" if i % 2 else "Chiqim", f"Kim {i}",
                      "", float(summa), "so'm", bugun, "sinov"))

    for i in range(1, 5):
        conn.execute("INSERT INTO employees (id,name,position,phone,rate_per_box,"
                     "brigade,firm,active) VALUES (?,?,?,?,?,?,?,?)",
                     (i, f"Xodim {i}", "Stanokchi", "90", 150, "A", "", 1))

    conn.commit()
    conn.close()
    return {"mijozlar": 7, "buyurtmalar": 12, "tolovlar": 8,
            "kassa": 20, "xodimlar": 4,
            "buyurtma_jami": buyurtma_jami, "tolov_jami": tolov_jami,
            "kassa_jami": kassa_jami}


def main() -> int:
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://innasoft:innasoft@localhost:5440/innasoft")

    from app.db import SessionLocal
    from app import models as m

    vaqtinchalik = tempfile.mkdtemp(prefix="kochirish_")
    eski = str(Path(vaqtinchalik) / "eski.db")
    kutilgan = eski_baza_yasa(eski)

    # Manba o'zgarmasligini isbotlash uchun — oldingi barmoq izi
    oldingi_hash = hashlib.sha256(Path(eski).read_bytes()).hexdigest()

    db = SessionLocal()
    oldin = {
        "mijozlar": db.query(m.Client).count(),
        "buyurtmalar": db.query(m.Order).count(),
        "tolovlar": db.query(m.Payment).count(),
        "kassa": db.query(m.KassaEntry).count(),
        "xodimlar": db.query(m.Employee).count(),
    }
    db.close()

    natija = subprocess.run(
        [sys.executable, str(ILDIZ / "tools" / "kochir.py"), eski],
        capture_output=True, text=True, cwd=str(ILDIZ))
    tekshir("ko'chirish vositasi ishladi", natija.returncode == 0,
            (natija.stderr or natija.stdout)[-300:])
    if natija.returncode != 0:
        return 1

    db = SessionLocal()
    try:
        keyin = {
            "mijozlar": db.query(m.Client).count(),
            "buyurtmalar": db.query(m.Order).count(),
            "tolovlar": db.query(m.Payment).count(),
            "kassa": db.query(m.KassaEntry).count(),
            "xodimlar": db.query(m.Employee).count(),
        }
        for kalit, kutilgan_soni in (("mijozlar", 7), ("buyurtmalar", 12),
                                     ("tolovlar", 8), ("kassa", 20),
                                     ("xodimlar", 4)):
            qoshildi = keyin[kalit] - oldin[kalit]
            tekshir(f"{kalit}: {kutilgan_soni} ta ko'chdi",
                    qoshildi == kutilgan_soni, f"qo'shildi {qoshildi}")

        # --- Pul tiyingacha to'g'rimi -----------------------------------
        yangi_buyurtmalar = (db.query(m.Order)
                             .order_by(m.Order.id.desc())
                             .limit(12).all())
        summa = sum(Decimal(str(o.total)) for o in yangi_buyurtmalar)
        tekshir("buyurtmalar summasi tiyingacha mos",
                summa == kutilgan["buyurtma_jami"],
                f"{summa} != {kutilgan['buyurtma_jami']}")

        # --- Karton maydonlari `attributes` ga o'tdimi -------------------
        namuna = yangi_buyurtmalar[0]
        atr = namuna.attributes or {}
        tekshir("karton maydonlari attributes ga o'tdi",
                all(k in atr for k in ("length_mm", "width_mm", "height_mm",
                                       "grade", "layers")),
                str(atr)[:120])
        tekshir("m2_per_box SATR sifatida saqlandi (aniqlik yo'qolmasin)",
                isinstance(atr.get("m2_per_box"), str), repr(atr.get("m2_per_box")))
        tekshir("is_offset mantiqiy turda", isinstance(atr.get("is_offset"), bool),
                repr(atr.get("is_offset")))
    finally:
        db.close()

    # --- ENG MUHIMI: manba tegilmadimi ----------------------------------
    keyingi_hash = hashlib.sha256(Path(eski).read_bytes()).hexdigest()
    tekshir("MANBA FAYL O'ZGARMADI (checksum)", oldingi_hash == keyingi_hash,
            "manba fayl yozilgan — bu jiddiy xato!")

    print()
    if XATOLAR:
        print(f"❌ {len(XATOLAR)} muammo:")
        for x in XATOLAR:
            print("   ·", x)
        return 1
    print("✅ KO'CHIRISH TO'G'RI — ma'lumot yo'qolmadi, manba tegilmadi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
