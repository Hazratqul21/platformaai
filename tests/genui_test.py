"""GenUI SINOVI — model yuborgan komponent xavfsiz va to'g'ri tekshiriladimi.

Komponentlar MODELDAN keladi, ya'ni ishonchsiz manba. Bu yerda aynan
shuni sinaymiz: noto'g'ri, haddan tashqari katta yoki xavfli komponent
frontendga yetib bormasin.

Jonli LLM kerak emas — `genui.tekshir()` sof funksiya.

    .venv/bin/python tests/genui_test.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import genui                                  # noqa: E402

XATOLAR = []


def tekshir(nom, shart, izoh=""):
    print(f"{'✓' if shart else '✗'} {nom}" + (f"  [{izoh}]" if not shart and izoh else ""))
    if not shart:
        XATOLAR.append(nom)


def main() -> int:
    # ---- 1. Har primitiv chizilishi kerak --------------------------
    namunalar = {
        "jadval": {"tur": "jadval", "sarlavha": "Qarzdorlar",
                   "ustunlar": ["Mijoz", "Qarz"],
                   "qatorlar": [{"hujayralar": ["A MChJ", "12 000 000 so'm"],
                                 "holat": "xavf"}, ["B MChJ", "500 000 so'm"]]},
        "korsatkichlar": {"tur": "korsatkichlar", "elementlar": [
            {"nom": "Kassa", "qiymat": "48 mln", "ozgarish": "+12%", "holat": "ok"}]},
        "tafsilot": {"tur": "tafsilot", "sarlavha": "Mijoz",
                     "qatorlar": [{"nom": "Qarz", "qiymat": "5 mln", "holat": "ogoh"}]},
        "taqsimot": {"tur": "taqsimot", "birlik": "so'm", "elementlar": [
            {"nom": "0-15 kun", "qiymat": 1200000},
            {"nom": "60+ kun", "qiymat": "800000", "holat": "xavf"}]},
        "profil_oynasi": {"tur": "profil_oynasi", "nom": "Non zavodi",
                          "maydonlar_royxati": [{"nom": "Og'irlik", "tur": "butun",
                                                 "birlik": "g", "majburiy": True}],
                          "retsept": [{"material": "Un", "birlik": "kg",
                                       "miqdor": "0.39 kg"}],
                          "bosqichlar": ["Kutishda", "Sexda", "Tayyor"]},
        "tasdiq": {"tur": "tasdiq", "sarlavha": "Faollashtiraymi?",
                   "matn": "Non zavodi profili", "amal": "profilni_faollashtir",
                   "kirish": {"kalit": "non"}},
        "hujjat": {"tur": "hujjat", "havolalar": [
            {"nom": "Akt", "havola": "/api/reports/act/12.pdf"}]},
        "ogoh": {"tur": "ogoh", "daraja": "xavf", "sarlavha": "Diqqat",
                 "matn": "Ombor tugayapti"},
    }
    for nom, k in namunalar.items():
        try:
            toza = genui.tekshir(k)
            tekshir(f"«{nom}» tekshiruvdan o'tdi", toza["tur"] == nom)
        except genui.KomponentXato as e:
            tekshir(f"«{nom}» tekshiruvdan o'tdi", False, str(e))

    tekshir("hamma primitiv sinaldi",
            set(namunalar) == set(genui.TURLAR),
            f"sinalmagan: {set(genui.TURLAR) - set(namunalar)}")

    # ---- 2. Noto'g'ri kirish rad etilishi kerak ---------------------
    for izoh, buzuq in [
        ("noma'lum tur", {"tur": "hacker_panel"}),
        ("tursiz", {"sarlavha": "x"}),
        ("lug'at emas", "shunchaki matn"),
        ("noma'lum amal", {"tur": "tasdiq", "amal": "bazani_ochir", "kirish": {}}),
        ("amali yo'q tasdiq", {"tur": "tasdiq", "matn": "x"}),
    ]:
        try:
            genui.tekshir(buzuq)
            tekshir(f"rad etildi: {izoh}", False, "o'tkazib yubordi!")
        except (genui.KomponentXato, AttributeError, TypeError):
            tekshir(f"rad etildi: {izoh}", True)

    # ---- 3. Hajm chegaralari ---------------------------------------
    ulkan = {"tur": "jadval", "ustunlar": [f"U{i}" for i in range(40)],
             "qatorlar": [[f"q{i}"] for i in range(5000)]}
    toza = genui.tekshir(ulkan)
    tekshir("jadval qatorlari cheklandi",
            len(toza["qatorlar"]) == genui.MAX_QATOR, str(len(toza["qatorlar"])))
    tekshir("jadval ustunlari cheklandi",
            len(toza["ustunlar"]) == genui.MAX_USTUN, str(len(toza["ustunlar"])))

    kop = [{"tur": "ogoh", "matn": str(i)} for i in range(50)]
    tekshir("komponentlar soni cheklandi",
            len(genui.tekshir_royxat(kop)) == genui.MAX_KOMPONENT)

    # Har maydonning O'Z chegarasi bor (`MAX_MATN` — eng katta ruxsat).
    # Muhimi: 5000 belgi hech qachon frontendga o'tmasin.
    uzun = genui.tekshir({"tur": "ogoh", "matn": "x" * 5000})
    tekshir("uzun matn qisqartirildi",
            0 < len(uzun["matn"]) <= 400, str(len(uzun["matn"])))
    uzun_sarlavha = genui.tekshir({"tur": "ogoh", "sarlavha": "x" * 5000,
                                   "matn": "x"})
    tekshir("uzun sarlavha qisqartirildi",
            len(uzun_sarlavha["sarlavha"]) <= 120,
            str(len(uzun_sarlavha["sarlavha"])))

    # ---- 4. Xavfsizlik ---------------------------------------------
    # HTML frontendda `textContent` bilan qo'yiladi, lekin matn shu
    # yerdan O'ZGARMASDAN o'tishi kerak — «tozalash» nomi bilan
    # foydalanuvchi ma'lumotini buzib qo'ymaslik uchun.
    xss = genui.tekshir({"tur": "ogoh", "matn": "<script>alert(1)</script>"})
    tekshir("matn o'zgartirilmaydi (frontend textContent bilan qo'yadi)",
            xss["matn"] == "<script>alert(1)</script>")

    tashqi = genui.tekshir({"tur": "hujjat", "havolalar": [
        {"nom": "Yomon", "havola": "https://tashqi.example/olib-ketish"},
        {"nom": "Yomon2", "havola": "javascript:alert(1)"},
        {"nom": "Yaxshi", "havola": "/api/reports/act/1.pdf"}]})
    tekshir("faqat ichki /api/ havolasi qoldi",
            [h["nom"] for h in tashqi["havolalar"]] == ["Yaxshi"],
            str(tashqi["havolalar"]))

    # ---- 5. Buzuq komponent qolganini yiqitmaydi -------------------
    aralash = [{"tur": "yoq"}, {"tur": "ogoh", "matn": "ishlaydi"},
               "axlat", {"tur": "tafsilot", "qatorlar": []}]
    natija = genui.tekshir_royxat(aralash)
    tekshir("buzuq komponent tashlanadi, qolgani chiziladi",
            len(natija) == 2, str([k["tur"] for k in natija]))

    # ---- 6. Amallar ro'yxati butunmi -------------------------------
    for nom, t in genui.AMALLAR.items():
        tekshir(f"amal «{nom}» to'liq ta'riflangan",
                all(k in t for k in ("izoh", "tugma", "rollar", "bajar"))
                and callable(t["bajar"]))

    # ---- 7. Modelga beriladigan ko'rsatma to'liqmi -----------------
    korsatma = genui.korsatma_matni()
    yetishmaydi = [n for n in genui.TURLAR if f"`{n}`" not in korsatma]
    tekshir("ko'rsatmada hamma primitiv sanalgan", not yetishmaydi, str(yetishmaydi))
    yetishmaydi = [n for n in genui.AMALLAR if f"`{n}`" not in korsatma]
    tekshir("ko'rsatmada hamma amal sanalgan", not yetishmaydi, str(yetishmaydi))

    print()
    if XATOLAR:
        print(f"❌ {len(XATOLAR)} muammo: " + ", ".join(XATOLAR))
        return 1
    print(f"✅ GenUI TO'G'RI — {len(genui.TURLAR)} primitiv, "
          f"{len(genui.AMALLAR)} tasdiqlanadigan amal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
