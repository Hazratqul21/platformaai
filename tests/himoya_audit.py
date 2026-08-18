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
    # Ro'yxatdan o'tish — odam hali firmaga ega EMAS, token bo'lishi
    # mumkin emas. Boshqaruv bazasi bilan ishlaydi, ERP ma'lumotiga
    # tegmaydi. Parol tekshiruvi endpoint ichida.
    "/royxat":            "ro'yxatdan o'tish — kirish nuqtasi",
    "/holat/{akkaunt_kod}": "baza tayyorlanish holati — sir emas",
    "/kir":               "platforma kabinetiga kirish nuqtasi",
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
