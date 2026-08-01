"""HAR BIR SOHA PROFILI TO'LIQ HAYOT SIKLIDAN O'TADIMI — konformlik testi.

Bu testning maqsadi: yangi soha qo'shilganda uni QO'LDA sinash kerak
bo'lmasin. Profil qo'shildi -> shu test uni avtomat tekshiradi.

Har profil uchun:
  1. faollashtiriladi
  2. profil ta'rifidan HAQIQIY qiymatlar yasaladi (variantlar/standart/min)
  3. mijoz + buyurtma yaratiladi
  4. matnlar bo'sh emasligi tekshiriladi
  5. validatsiya ishlashi tekshiriladi (majburiy maydonsiz -> 400)
  6. buyurtma butun status oqimi bo'ylab yuritiladi (boshlanish -> topshirildi)
  7. hujjatlar (act.pdf, nakladnoy.pdf) yasaladi

Ishga tushirish:
    DATABASE_URL="sqlite:////tmp/p.db" SEED_EMPTY=1 PORT=8030 \
        .venv/bin/python -m app.main
    .venv/bin/python tests/profil_test.py
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = os.getenv("BASE", "http://localhost:8030")
XATOLAR: list[str] = []


def call(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        gavda = e.read()
        try:
            return e.code, json.loads(gavda)
        except ValueError:
            return e.code, {"detail": gavda[:200].decode("utf-8", "replace")}


def bayt(path, token):
    req = urllib.request.Request(BASE + path)
    req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, len(r.read())
    except urllib.error.HTTPError as e:
        return e.code, 0


def tekshir(profil, nom, shart, izoh=""):
    if not shart:
        XATOLAR.append(f"{profil}: {nom} — {izoh}")
    return shart


def namuna_qiymat(md):
    """Maydon ta'rifidan HAQIQIY, qoidalarga mos qiymat yasaydi."""
    if md.get("standart") is not None:
        return md["standart"]
    if md.get("variantlar"):
        return md["variantlar"][0]
    tur = md["tur"]
    if tur == "butun":
        return md.get("min") if md.get("min") is not None else 100
    if tur == "kasr":
        return str(md.get("min") or 1)
    if tur == "mantiq":
        return False
    return "Sinov"


def profilni_sina(kalit, nom, token):
    s, _ = call("POST", "/api/soha/faollashtirish", {"kalit": kalit}, token)
    if not tekshir(kalit, "faollashtirish", s == 200, f"status={s}"):
        return

    s, joriy = call("GET", "/api/soha/joriy", token=token)
    maydonlar = [md for md in joriy["maydonlar"] if not md["hisoblanadi"]]
    attrs = {md["kalit"]: namuna_qiymat(md) for md in maydonlar}

    s, c = call("POST", "/api/clients",
                {"company": f"Sinov mijoz ({kalit})", "phone": "901234567"}, token)
    if not tekshir(kalit, "mijoz yaratish", s == 200, str(c)[:120]):
        return

    s, o = call("POST", "/api/orders",
                {"client_id": c["id"], "qty": 100, "unit_price": 5000,
                 "product_name": "Sinov", "attributes": attrs}, token)
    if not tekshir(kalit, "buyurtma yaratish", s == 200, str(o)[:200]):
        return

    # matnlar bo'sh qolmasin — bo'sh bo'lsa shablonda xato kalit bor
    tekshir(kalit, "size matni", bool(o.get("size")), "bo'sh")
    tekshir(kalit, "tur matni", bool(o.get("tur")), "bo'sh")
    tekshir(kalit, "tarkib matni", bool(o.get("tarkib")), "bo'sh")
    tekshir(kalit, "attributes to'ldi",
            len(o.get("attributes") or {}) >= len(maydonlar),
            f"{len(o.get('attributes') or {})} < {len(maydonlar)}")

    # Validatsiya: majburiy maydonsiz rad etilsin.
    # DIQQAT: standarti BOR maydon sinovga yaramaydi — u berilmasa ham
    # profil o'zi to'ldiradi va buyurtma to'g'ri o'tadi. Shuning uchun
    # faqat standartsiz majburiy maydon tanlanadi.
    majburiy = [md for md in maydonlar
                if md["majburiy"] and md.get("standart") is None]
    if majburiy:
        kam = {k: v for k, v in attrs.items() if k != majburiy[0]["kalit"]}
        s, d = call("POST", "/api/orders",
                    {"client_id": c["id"], "qty": 10, "unit_price": 100,
                     "attributes": kam}, token)
        tekshir(kalit, "majburiy maydon tekshiruvi", s == 400, f"status={s}")

    # To'liq status oqimi: boshlanishdan topshirilgangacha.
    # Oqim GRAFIK bo'ylab yuriladi, chunki modulda oraliq bosqich bo'lishi
    # mumkin (servisda: Qabul qilindi -> Tashxis -> Tuzatilmoqda).
    kartochka = {st["nom"]: st for st in joriy["statuslar"]}
    joriy_status = o["status"]
    yurildi = [joriy_status]
    for _ in range(len(kartochka)):
        st = kartochka.get(joriy_status)
        if st is None or st["mano"] == "topshirildi":
            break
        # "bekor" ga ketmaymiz — maqsad to'liq sikldan o'tish
        keyingi = [k for k in st["keyingi"]
                   if kartochka.get(k, {}).get("mano") != "bekor"
                   and k not in yurildi]
        if not keyingi:
            break
        # topshirilganga eng tez olib boradigan yo'nalish
        tartib = {"muzokara": 0, "ishlab_chiqarish": 1, "tayyor": 2, "topshirildi": 3}
        keyingi.sort(key=lambda k: tartib.get(kartochka[k]["mano"], 0), reverse=True)
        maqsad = keyingi[0]
        s, d = call("POST", f"/api/orders/{o['id']}/status?status="
                    + urllib.parse.quote(maqsad), token=token)
        if not tekshir(kalit, f"status '{joriy_status}' -> '{maqsad}'", s == 200,
                       str(d)[:140]):
            break
        joriy_status = maqsad
        yurildi.append(maqsad)

    tekshir(kalit, "to'liq siklga yetdi",
            kartochka.get(joriy_status, {}).get("mano") == "topshirildi",
            f"to'xtagan joyi: {joriy_status}")

    for hujjat in (f"/api/reports/act/{o['id']}.pdf",
                   f"/api/reports/nakladnoy/{o['id']}.pdf"):
        st, hajm = bayt(hujjat, token)
        tekshir(kalit, hujjat.split("/")[-1], st == 200 and hajm > 1000,
                f"status={st} hajm={hajm}")

    print(f"  ✓ {kalit:<16} {nom:<32} "
          f"{o['size']!r} · {o['tarkib']!r}")


def main():
    s, d = call("POST", "/api/auth/login", {"login": "admin", "password": "1234"})
    if s != 200:
        print(f"❌ Login ishlamadi ({s}). Server {BASE} da ishlayaptimi?")
        raise SystemExit(1)
    token = d["token"]

    s, profillar = call("GET", "/api/soha/profillar", token=token)
    print(f"Topilgan profil: {len(profillar)}\n")
    for p in profillar:
        profilni_sina(p["kalit"], p["nom"], token)

    print()
    if XATOLAR:
        print(f"❌ {len(XATOLAR)} ta muammo:")
        for x in XATOLAR:
            print("   -", x)
        raise SystemExit(1)
    print(f"✅ HAMMA {len(profillar)} PROFIL TO'LIQ SIKLDAN O'TDI")


if __name__ == "__main__":
    main()
