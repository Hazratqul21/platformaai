"""HIMOYA AUDITI — har bir endpoint autentifikatsiya talab qiladimi.

Server kerak emas, kod AST bo'yicha o'qiladi: yangi endpoint qo'shilib,
`Depends(get_user)` yozish unutilsa shu yerda ushlanadi. Bir marta shunday
bo'lgan edi va tekshiruvsiz hech kim sezmagan bo'lardi.

DIQQAT: `admin_only = require_roles("Rahbar")` kabi MODUL DARAJASIDAGI
taxalluslar ham hisobga olinadi. Ilgari bu qilinmagani uchun audit 14 ta
soxta «himoyalanmagan» bergan edi — himoya aslida joyida edi.

    .venv/bin/python tests/himoya_audit.py
"""
import ast
import pathlib
import sys

# Ataylab ochiq qoldirilganlar — har biri sababi bilan.
OCHIQ = {
    "/api/auth/login":  "kirish nuqtasi",
    "/api/auth/logout": "faqat berilgan tokenni o'chiradi — begona token "
                        "bilan ham zarar yo'q, egasi allaqachon uni bilgan",
    "/api/health":      "konteyner healthcheck va monitoring",
    "/":                "statik sahifa",
    "/favicon.ico":     "statik",
    "/robots.txt":      "statik",
    # Korporativ sayt ko'rigi — reklama sahifasi, mijoz ma'lumoti yo'q.
    # `static/innasoft.html` ni beradi, bazaga umuman tegmaydi.
    "/innasoft":        "korporativ sayt ko'rigi (statik)",
    # Rasm — `<img src>` auth sarlavha yubormaydi, shuning uchun URL
    # bo'yicha ochiq (avvalgi StaticFiles mount ham shunday edi). Endi
    # akkaunt papkasidan beriladi — bir akkaunt boshqasinikini ko'rmaydi.
    "/uploads/{fayl}":  "mahsulot rasmi — akkaunt papkasidan",
    # Ro'yxatdan o'tish — odam hali firmaga ega EMAS, token bo'lishi
    # mumkin emas. Boshqaruv bazasi bilan ishlaydi, ERP ma'lumotiga
    # tegmaydi. Parol tekshiruvi endpoint ichida.
    "/royxat":            "ro'yxatdan o'tish — kirish nuqtasi",
    "/holat/{akkaunt_kod}": "baza tayyorlanish holati — sir emas",
    "/kir":               "platforma kabinetiga kirish nuqtasi",
    # Faoliyat yo'nalishlari ro'yxati — ro'yxatdan o'tish formasi uni
    # tokengacha ko'rsatadi. Bu koddagi shablonlar ro'yxati, hech
    # kimning ma'lumoti emas; sayt sahifasining o'zida ham turgan.
    "/sohalar":           "yo'nalishlar ro'yxati — mijoz ma'lumoti emas",
    # INN qidiruvi — ro'yxatdan o'tishning 1-qadami, token bo'lishi
    # mumkin emas. Mijoz ma'lumotiga tegmaydi (boshqa bazaga ham
    # bormaydi). PULLIK tashqi xizmatga borgani uchun IP bo'yicha
    # so'rov cheklovi qo'yilgan — `platforma/inn.py: chek_oshdimi`.
    "/inn/{inn}":         "INN qidiruvi — ochiq, lekin IP bo'yicha cheklangan",
}
HIMOYA = {"get_user", "get_user_parolsiz", "require_roles",
          "joriy_user", "joriy_admin"}   # platforma kabineti/admin
USULLAR = {"get", "post", "put", "delete", "patch"}


def _taxalluslar(daraxt: ast.Module) -> set[str]:
    """`admin_only = require_roles("Rahbar")` kabi nomlarni topadi."""
    topilgan = set()
    for tugun in daraxt.body:
        if not (isinstance(tugun, ast.Assign) and isinstance(tugun.value, ast.Call)):
            continue
        f = tugun.value.func
        if (getattr(f, "id", None) or getattr(f, "attr", None)) in HIMOYA:
            topilgan.update(t.id for t in tugun.targets if isinstance(t, ast.Name))
    return topilgan


def audit(ildiz: pathlib.Path) -> tuple[int, list[str]]:
    ochiq, jami = [], 0
    fayllar = sorted((ildiz / "app" / "routers").glob("*.py")) + [ildiz / "app" / "main.py"]
    for fayl in fayllar:
        daraxt = ast.parse(fayl.read_text())
        nomlar = HIMOYA | _taxalluslar(daraxt)
        for tugun in ast.walk(daraxt):
            if not isinstance(tugun, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            yol = None
            for dek in tugun.decorator_list:
                if (isinstance(dek, ast.Call) and isinstance(dek.func, ast.Attribute)
                        and dek.func.attr in USULLAR and dek.args
                        and isinstance(dek.args[0], ast.Constant)):
                    yol = dek.args[0].value
            if yol is None:
                continue
            jami += 1
            manba = ast.unparse(tugun.args)
            if any(n in manba for n in nomlar) or yol in OCHIQ:
                continue
            ochiq.append(f"{fayl.name}: {yol} ({tugun.name})")
    return jami, ochiq


# ---------------------------------------------------------------------
# IKKINCHI QATLAM — «himoyalangan» yetarli emas, TO'G'RI rol kerak.
#
# Birinchi qatlam faqat «tokensiz kirib bo'ladimi» deb qaraydi. Lekin
# `Depends(get_user)` — HAR QANDAY kirgan foydalanuvchi degani. Prodda
# aynan shu bo'shliq topildi: sklad mudiri menyuda «Касса» ni ko'rmasdi,
# lekin `/api/kassa` ni chaqirib oylik va ijarani o'qiy olardi.
# Menyuda yashirish — himoya emas.
# ---------------------------------------------------------------------
ROL_TALAB = {
    "app/routers/kassa.py":   ["journal", "export_xlsx", "add_entry", "del_entry"],
    "app/routers/finance.py": ["payment_list", "debtors", "cashflow",
                               "dashboard", "add_payment", "del_payment"],
}
# `require_roles(...)` dan yasalgan qisqartmalar
QOROVULLAR = ("require_roles", "kassachi", "moliyachi", "admin_only")


def rol_auditi(ildiz) -> list[str]:
    """Pul endpointlari rol bilan yopilganmi."""
    ochiq = []
    for nisbiy, funksiyalar in ROL_TALAB.items():
        fayl = ildiz / nisbiy
        if not fayl.exists():
            ochiq.append(f"{nisbiy}: fayl topilmadi")
            continue
        daraxt = ast.parse(fayl.read_text(encoding="utf-8"))
        imzolar = {t.name: ast.unparse(t.args)
                   for t in ast.walk(daraxt)
                   if isinstance(t, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for nom in funksiyalar:
            if nom not in imzolar:
                ochiq.append(f"{nisbiy}: `{nom}` topilmadi (nomi o'zgardimi?)")
            elif not any(q in imzolar[nom] for q in QOROVULLAR):
                ochiq.append(f"{nisbiy}: `{nom}` — har rolga ochiq")
    return ochiq


def main() -> int:
    ildiz = pathlib.Path(__file__).resolve().parent.parent
    jami, ochiq = audit(ildiz)
    print(f"Tekshirildi: {jami} endpoint "
          f"({len(OCHIQ)} tasi ataylab ochiq — login, health, statik)")
    if ochiq:
        print(f"\n❌ HIMOYALANMAGAN {len(ochiq)} ta:")
        for x in ochiq:
            print("   ·", x)
        return 1
    print(f"\n✅ {jami}/{jami} ENDPOINT HIMOYALANGAN")

    rol_ochiq = rol_auditi(ildiz)
    nechta = sum(len(v) for v in ROL_TALAB.values())
    if rol_ochiq:
        print(f"\n❌ PUL ENDPOINTLARI — ROL HIMOYASI YO'Q ({len(rol_ochiq)} ta):")
        for x in rol_ochiq:
            print("   ·", x)
        return 1
    print(f"✅ {nechta}/{nechta} PUL ENDPOINTI ROL BILAN YOPILGAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
