"""IJARACHILIK SINOVI — ikki mijoz bir jarayonda aralashmaydimi.

Bu bosqichning ENG MUHIM sinovi. Tekshiriladigan nuqson turi
«500 xatosi» emas — u JIMGINA noto'g'ri ishlash: bir mijozning
profili yoki ma'lumoti boshqasiga ko'rinishi.

Server kerak emas: ikki SQLite baza, bitta jarayon.
"""
import os
import sys
import tempfile
from pathlib import Path

KOK, QIZIL, TUGA = "\033[92m", "\033[91m", "\033[0m"
_xato = 0


def ok(shart, matn):
    global _xato
    if shart:
        print(f"{KOK}✅{TUGA} {matn}")
    else:
        _xato += 1
        print(f"{QIZIL}❌{TUGA} {matn}")


_tmp = tempfile.mkdtemp(prefix="ijarachilik_")
os.environ["IJARACHILIK"] = "1"
os.environ["BOSHQARUV_DATABASE_URL"] = f"sqlite:///{_tmp}/boshqaruv.db"
os.environ["MIJOZ_DB_SHABLON"] = f"sqlite:///{_tmp}/{{baza}}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/yagona.db"
os.environ["ASOSIY_DOMEN"] = "innasoft.uz"
os.environ["MAX_ENGINE"] = "3"          # LRU ni sinash uchun ataylab kichik

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import domain, tenancy                      # noqa: E402
from app import models as m                          # noqa: E402
from app.db import Base                              # noqa: E402
from app.platforma import xizmat as px               # noqa: E402
from app.platforma.db import BoshqaruvSession, jadvallarni_yarat  # noqa: E402

print("\n" + "=" * 62)
print("IJARACHILIK SINOVI — ikki mijoz bir jarayonda")
print("=" * 62 + "\n")

jadvallarni_yarat()
bdb = BoshqaruvSession()
f_mebel = px.akkaunt_yarat(bdb, "mebelsex", "Mebel Sex")
f_non = px.akkaunt_yarat(bdb, "nonzavod", "Non Zavodi")
bdb.close()


def akkaunt(f):
    return tenancy.Akkaunt(id=f.id, kod=f.kod, baza_nomi=f.baza_nomi)


# Har akkauntning bazasini tayyorlaymiz va HAR XIL profil faollashtiramiz.
def baza_tayyorla(f, profil_kaliti):
    eng = tenancy.akkaunt_engine(f.baza_nomi)
    Base.metadata.create_all(eng)
    sess = tenancy.akkaunt_sessiya(f.baza_nomi)
    tarif = domain.shablonlar()[profil_kaliti]
    import json
    sess.add(m.SohaProfil(kalit=profil_kaliti, nom=tarif["nom"],
                          tarif_json=json.dumps(tarif), faol=True))
    sess.commit()
    return sess


print("1. SO'ROVDAN AKKAUNTNI ANIQLASH")
ok(tenancy.kod_ajrat("mebelsex.innasoft.uz") == "mebelsex", "subdomen ajratildi")
ok(tenancy.kod_ajrat("innasoft.uz") is None, "asosiy domen akkaunt emas")
ok(tenancy.kod_ajrat("www.innasoft.uz") is None, "`www` akkaunt emas")
ok(tenancy.kod_ajrat("a.b.innasoft.uz") is None, "ichma-ich subdomen rad etildi")
ok(tenancy.kod_ajrat("mebelsex.boshqasayt.uz") is None, "begona domen rad etildi")
ok(tenancy.sorovdan_akkaunt("mebelsex.innasoft.uz").baza_nomi == "inna_mebelsex",
   "akkaunt boshqaruv bazasidan topildi")
ok(tenancy.sorovdan_akkaunt("", "nonzavod").kod == "nonzavod",
   "`X-Akkaunt` sarlavhasi ham ishlaydi (Telegram Mini App uchun)")
ok(tenancy.sorovdan_akkaunt("yoqakkaunt.innasoft.uz") is None, "yo'q akkaunt — None")

print("\n2. PROFIL KESHI ARALASHMAYDIMI  ← eng muhimi")
s_mebel = baza_tayyorla(akkaunt(f_mebel), "mebel")
s_non = baza_tayyorla(akkaunt(f_non), "non")

t = tenancy.ornat(akkaunt(f_mebel))
domain.qayta_yukla(s_mebel)
mebel_nomi = domain.profil().nom
tenancy.tozala(t)

t = tenancy.ornat(akkaunt(f_non))
domain.qayta_yukla(s_non)
non_nomi = domain.profil().nom
tenancy.tozala(t)

# Endi ORQAGA qaytamiz: mebel akkaunti hali ham O'Z profilini ko'rishi kerak.
t = tenancy.ornat(akkaunt(f_mebel))
mebel_qayta = domain.profil().nom
mebel_maydonlar = {x.kalit for x in domain.profil().maydonlar}
tenancy.tozala(t)

t = tenancy.ornat(akkaunt(f_non))
non_maydonlar = {x.kalit for x in domain.profil().maydonlar}
tenancy.tozala(t)

ok(mebel_nomi != non_nomi, f"ikki akkaunt ikki xil profil: «{mebel_nomi}» / «{non_nomi}»")
ok(mebel_qayta == mebel_nomi,
   "non zavodi so'rovidan KEYIN ham mebel o'z profilini ko'rdi")
ok(not (mebel_maydonlar & non_maydonlar) or mebel_maydonlar != non_maydonlar,
   f"maydonlar aralashmadi (mebel {len(mebel_maydonlar)}, non {len(non_maydonlar)})")

print("\n3. MA'LUMOT ARALASHMAYDIMI")
s_mebel.add(m.Client(company="Mebel mijozi", phone="+998901112233"))
s_mebel.commit()
s_non.add(m.Client(company="Non mijozi", phone="+998904445566"))
s_non.commit()

mebel_mijozlar = [c.company for c in s_mebel.query(m.Client).all()]
non_mijozlar = [c.company for c in s_non.query(m.Client).all()]
ok(mebel_mijozlar == ["Mebel mijozi"] and non_mijozlar == ["Non mijozi"],
   f"har baza faqat o'z mijozini ko'radi: {mebel_mijozlar} / {non_mijozlar}")

# `get_db` ham to'g'ri bazaga borsinmi
from app.db import get_db                              # noqa: E402
t = tenancy.ornat(akkaunt(f_non))
gen = get_db()
db_non = next(gen)
nomlar = [c.company for c in db_non.query(m.Client).all()]
try:
    next(gen)
except StopIteration:
    pass
tenancy.tozala(t)
ok(nomlar == ["Non mijozi"],
   "`get_db()` joriy akkauntning bazasiga bordi (125 endpoint shu orqali ishlaydi)")

print("\n4. ULANISHLAR CHEGARASI (LRU)")
for i in range(6):
    tenancy.akkaunt_engine(f"sinov_baza_{i}")
ok(tenancy.ochiq_enginelar() <= 3,
   f"MAX_ENGINE=3 — ochiq engine: {tenancy.ochiq_enginelar()} "
   f"(50 mijoz × 30 ulanish = 1500 bo'lib ketmaydi)")

print("\n5. IJARACHILIKSIZ REJIM BUZILMADIMI")
os.environ["IJARACHILIK"] = ""
ok(not tenancy.yoqilganmi(), "o'chirilganda ijarachilik yoqilmagan deb ko'rsatiladi")
ok(tenancy.kalit() == "_yagona", "kesh kaliti yagona rejimda o'zgarmas")
os.environ["IJARACHILIK"] = "1"

print("\n6. KESHNI TOZALASH FAQAT O'Z AKKAUNTSIGA TEGADI")
t = tenancy.ornat(akkaunt(f_mebel))
domain.keshni_tozala()
tenancy.tozala(t)
t = tenancy.ornat(akkaunt(f_non))
hali_bor = domain._KESH.get("inna_nonzavod") is not None
tenancy.tozala(t)
ok(hali_bor, "mebel keshi tozalandi, non keshi tegilmadi")

s_mebel.close()
s_non.close()
tenancy.hammasini_yop()

print("\n" + "=" * 62)
if _xato:
    print(f"{QIZIL}{_xato} TA XATO{TUGA}")
    sys.exit(1)
print(f"{KOK}IKKI MIJOZ ARALASHMADI{TUGA}")
print("=" * 62)
