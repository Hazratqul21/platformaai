"""JONLI AGENT SINOVI — haqiqiy LLM bilan uchidan uchiga.

Qolgan testlardan farqi: bu HAQIQIY provayderga so'rov yuboradi. Kalit
bo'lmasa o'zi o'tkazib yuboradi (`sinov.sh` da yiqilmasin) — kalit
bo'lsa esa eng muhim narsani tekshiradi:

    · agent asbobni chaqira oladimi
    · `korsat` orqali KOMPONENT chiza oladimi (GenUI)
    · rol cheklovi jonli yo'lda ham ishlaydimi
    · javob o'zbekcha va qisqami

NEGA KERAK: asbob sxemalari provayderdan provayderga boshqacha
o'giriladi. Gemini'da `korsat` obyekt massivi bilan har safar
`MALFORMED_FUNCTION_CALL` bergan edi va buni FAQAT jonli chaqiruv
ko'rsatdi — sxema testlari toza o'tavergan.

Bepul tarifda so'rov chegarasi bor (daqiqasiga ~10), shuning uchun
so'rovlar orasida kutiladi.

    BASE=http://localhost:8070 .venv/bin/python tests/jonli_agent_test.py
"""
import json
import os
import time
import urllib.error
import urllib.request

BASE = os.getenv("BASE", "http://localhost:8070")
KUTISH = float(os.getenv("AGENT_KUTISH", "8"))   # so'rovlar orasida, sekund
XATOLAR = []


def call(method, path, body=None, token=None, timeout=240):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except ValueError:
            return e.code, {}
    except Exception as e:                                # noqa: BLE001
        return 0, {"detail": str(e)}


def tekshir(nom, shart, izoh=""):
    print(f"{'✓' if shart else '✗'} {nom}" + (f"  [{izoh}]" if not shart and izoh else ""))
    if not shart:
        XATOLAR.append(f"{nom}: {izoh}")


SINOV_PAROL = "Sinov2026Parol"


def kirish():
    s, d = call("POST", "/api/auth/login", {"login": "admin", "password": "1234"})
    if s == 200:
        if d.get("parol_almashtirilsin"):
            call("POST", "/api/auth/change-password",
                 {"old_password": "1234", "new_password": SINOV_PAROL}, d["token"])
        return d["token"]
    s, d = call("POST", "/api/auth/login",
                {"login": "admin", "password": SINOV_PAROL})
    if s != 200:
        print(f"❌ Login ({s})")
        raise SystemExit(1)
    return d["token"]


# Har agent uchun: savol + qaysi asbob chaqirilishi kutiladi
STSENARIYLAR = [
    ("ombor", "Omborda nima bor? Jadval qilib ko'rsat.", "ombor_qoldigi"),
    ("moliya", "Kim eng ko'p qarzdor? Jadval qilib ko'rsat.", "qarzdorlar"),
    ("buyurtma", "Qaysi buyurtmalar kechikyapti?", "buyurtmalar"),
    ("sozlash", "Qanday tayyor soha profillari bor?", "profillarni_kor"),
]


def main() -> int:
    token = kirish()
    s, holat = call("GET", "/api/agent/holat", token=token)
    if s != 200 or not holat.get("tayyor"):
        izoh = holat.get("izoh") if isinstance(holat, dict) else ""
        print(f"⏭  JONLI SINOV O'TKAZILDI — LLM kaliti yo'q ({izoh})")
        return 0

    print(f"Provayder: {holat['provayder']} · {holat['model']}\n")

    otkazildi = 0
    for agent, savol, kutilgan_asbob in STSENARIYLAR:
        s, j = call("POST", "/api/agent/xabar",
                    {"matn": savol, "agent": agent}, token)
        # 503 — provayder bandligi yoki so'rov chegarasi. Bu BIZNING
        # xatomiz emas (ayniqsa bepul tarifda), shuning uchun sinov
        # yiqilmaydi — o'tkazib yuboriladi. Aks holda `sinov.sh` tashqi
        # xizmat holatiga qarab tasodifiy qizarardi.
        if s == 503:
            print(f"⏭  [{agent}] provayder band — o'tkazib yuborildi")
            otkazildi += 1
            time.sleep(KUTISH)
            continue
        if not tekshir(f"[{agent}] javob keldi", s == 200,
                       str(j.get("detail"))[:160]):
            time.sleep(KUTISH)
            continue

        asboblar = [i["asbob"] for i in j.get("izlar", [])]
        komponentlar = [k["tur"] for k in j.get("komponentlar", [])]
        javob = (j.get("javob") or "").strip()

        tekshir(f"[{agent}] «{kutilgan_asbob}» asbobini chaqirdi",
                kutilgan_asbob in asboblar, f"chaqirilgan: {asboblar}")
        tekshir(f"[{agent}] matnli javob bor", len(javob) > 5, repr(javob[:80]))
        # `korsat` chaqirilgan bo'lsa — komponent HAQIQATAN chizilgan
        # bo'lishi kerak. Bo'sh qolsa demak tekshiruvdan o'tmagan.
        if "korsat" in asboblar:
            tekshir(f"[{agent}] korsat komponent chizdi",
                    len(komponentlar) > 0,
                    "korsat chaqirilgan, lekin komponent bo'sh")
        print(f"    asboblar: {asboblar} · komponentlar: {komponentlar}")
        print(f"    javob: {javob[:110]}")
        time.sleep(KUTISH)

    # ---- Rol cheklovi jonli yo'lda ---------------------------------
    s, d = call("POST", "/api/users",
                {"login": "sinov_sklad", "password": "Sinov2026Parol",
                 "name": "Sinov", "role": "Sklad mudiri"}, token)
    if s in (200, 409):
        s2, d2 = call("POST", "/api/auth/login",
                      {"login": "sinov_sklad", "password": "Sinov2026Parol"})
        if s2 == 200:
            s3, d3 = call("POST", "/api/agent/xabar",
                          {"matn": "Salom", "agent": "moliya"}, d2["token"])
            tekshir("sklad mudiri moliya agentiga kira olmaydi", s3 == 403,
                    f"kod={s3}")

    print()
    if XATOLAR:
        print(f"❌ {len(XATOLAR)} muammo:")
        for x in XATOLAR:
            print("   ·", x)
        return 1
    if otkazildi == len(STSENARIYLAR):
        print("⏭  HAMMASI O'TKAZIB YUBORILDI — provayder band "
              "(so'rov chegarasi). Kod tekshirilmadi.")
        return 0
    print(f"✅ JONLI AGENT ISHLAYAPTI — asboblar, GenUI va rol cheklovi"
          + (f" ({otkazildi} ta o'tkazib yuborildi)" if otkazildi else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
