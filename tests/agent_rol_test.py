"""AGENT ROL CHEKLOVI — serversiz, LLM kalitisiz.

NEGA ALOHIDA SINOV: bu nuqsonni `jonli_agent_test.py` ushlagan edi,
lekin u faqat haqiqiy LLM kaliti bo'lganda yuradi. Kalitsiz muhitda
(CI, boshqa dasturchi) xato jimgina o'tib ketardi. Rol cheklovi —
himoyaning o'zagi, u har doim tekshirilishi kerak.

Tarixi: 034 da to'rt agent bitta «yordamchi» ga birlashtirildi va
himoya AGENT darajasidan ASBOB darajasiga ko'chirildi. Eski kalitlar
(«moliya», «ombor») ko'rsatmani tahrirlash uchun `AGENTLAR` da qoldi
va yangi filtrni CHETLAB O'TDI: sklad mudiri `agent: "moliya"` deb
yuborsa moliya asboblarini to'liq olardi.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException                       # noqa: E402

from app import agent as ai                             # noqa: E402
from app.routers.agent import _agent_ruxsatini_tekshir  # noqa: E402

YASHIL, QIZIL, TUGA = "\033[92m", "\033[91m", "\033[0m"
XATO = 0


def ok(shart, matn):
    global XATO
    if shart:
        print(f"{YASHIL}✅{TUGA} {matn}")
    else:
        print(f"{QIZIL}❌{TUGA} {matn}")
        XATO += 1


def kod(agent_kalit, rol):
    """Marshrutizator shu juftlikka nima qaytaradi: 'ok' yoki HTTP kodi."""
    try:
        _agent_ruxsatini_tekshir(agent_kalit, rol)
        return "ok"
    except HTTPException as e:
        return e.status_code


print("\n" + "=" * 62)
print("AGENT ROL CHEKLOVI — ikki qatlamli himoya")
print("=" * 62 + "\n")

print("1-QATLAM — marshrutizator (403)")
ok(kod("moliya", "Sklad mudiri") == 403,
   "sklad mudiri moliya agentiga KIRA OLMAYDI")
ok(kod("moliya", "Buxgalter") == "ok", "buxgalter moliya agentiga kiradi")
ok(kod("moliya", "Rahbar") == "ok", "rahbar hamma joyga kiradi")
ok(kod("ombor", "Sklad mudiri") == "ok", "sklad mudiri ombor agentiga kiradi")
ok(kod("sozlash", "Menejer") == 403, "menejer sozlash agentiga kira olmaydi")
ok(kod(ai.YORDAMCHI_KALIT, "Sklad mudiri") == "ok",
   "birlashgan yordamchi hammaga ochiq (asboblari rol bo'yicha filtrlanadi)")
ok(kod(None, "Sklad mudiri") == "ok", "kalitsiz so'rov yordamchiga boradi")
ok(kod("yoq_agent", "Sklad mudiri") == "ok", "noma'lum kalit yordamchiga boradi")
ok(kod("moliya", "Yo'q rol") == 403, "noma'lum rolga AI umuman ochiq emas")

print("\n2-QATLAM — asboblar kesishmasi (1-qatlamdan o'tib ketilsa ham)")
sklad = set(ai.rolga_asboblar("Sklad mudiri"))
moliya = set(ai.AGENTLAR["moliya"]["asboblar"])
ok(not (moliya & sklad),
   f"sklad mudiriga moliya asboblari YETIB BORMAYDI (kesishma {moliya & sklad})")
ok("qarzdorlar" not in sklad, "«qarzdorlar» sklad mudiriga berilmaydi")
ok("qarzdorlar" in set(ai.rolga_asboblar("Buxgalter")),
   "«qarzdorlar» buxgalterga beriladi")

print("\n3-QATLAM — har agentning rollari e'lon qilingan")
for kalit, a in ai.AGENTLAR.items():
    ok(bool(a.get("rollar")), f"«{kalit}» agentida rollar ro'yxati bor")

print()
if XATO:
    print(f"{QIZIL}❌ {XATO} muammo{TUGA}")
    sys.exit(1)
print(f"{YASHIL}✅ ROL CHEKLOVI ISHLAYAPTI — ikki qatlam ham{TUGA}")
