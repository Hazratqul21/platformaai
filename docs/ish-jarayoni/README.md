# ISH JARAYONI — ish daftari

> Har yozilgan qism shu yerda qayd etiladi: **nima yozildi, qayerga,
> nima uchun aynan shunday, nimaga tegdi, qanday tekshirildi.**
>
> Maqsad: olti oydan keyin «bu nega shunday yozilgan?» degan savolga
> javob kodni qayta o'qimasdan topilsin.

---

## Yozuv qoidasi

Har yozuv shu bo'limlardan iborat:

| Bo'lim | Nima yoziladi |
|---|---|
| **Nima qilindi** | bir-ikki jumla, aniq |
| **Fayllar** | qaysi fayl, necha qator, yangi/o'zgargan |
| **Nega aynan shunday** | qaralgan muqobillar va nega rad etilgani |
| **Nimaga tegdi** | qaysi mavjud qism ta'sirlandi |
| **Xavf** | nima buzilishi mumkin, qanday qo'riqlanadi |
| **Tekshiruv** | qanday sinaldi, natija |
| **Qoldi** | tugallanmagan qism bo'lsa |

**Halollik qoidasi:** ishlamagan narsa «ishladi» deb yozilmaydi.
Sinalmagan qism «sinalmadi» deb yoziladi.

---

## Yozuvlar

### Retrospektiv — 2026-08-18 gacha yozilganlar

| # | Yozuv | Nima haqida |
|---|---|---|
| 001 | [Yadro va baza](001-yadro-va-baza.md) | `db.py`, `models.py`, `auth.py`, `main.py`, `migrate.py` |
| 002 | [Soha qatlami](002-soha-qatlami.md) | `domain.py`, 22 profil, 5 modul — loyihaning asosiy g'oyasi |
| 003 | [Hisob-kitob](003-hisob-kitob.md) | `services.py`, `kassa_sync.py`, topilgan oltita xato |
| 004 | [Routerlar va eksport](004-routerlar-va-eksport.md) | 13 router, 125 endpoint, hujjat eksporti |
| 005 | [AI qatlami](005-ai-qatlami.md) | `llm.py`, `agent.py`, `genui.py` |
| 006 | [Frontend](006-frontend.md) | `static/` — SPA, GenUI chizuvchi, soha formasi |
| 007 | [Sinov va vositalar](007-sinov-va-vositalar.md) | `tests/`, `tools/` |
| 008 | [Hujjatlar](008-hujjatlar.md) | `docs/` — strategiya va reja |

### Joriy ish — A bosqichi (ijarachilik / SaaS)

| # | Yozuv | Holat |
|---|---|---|
| 009 | [Boshqaruv bazasi](009-boshqaruv-bazasi.md) | ✅ tugallandi — 6 jadval, sinov toza |
| 010 | [Lending sahifasi](010-lending-sahifasi.md) | ✅ kirishdagi tanishtiruv sahifasi |
| 011 | [Ijarachilik yadrosi](011-ijarachilik-yadrosi.md) | ✅ contextvars, firma bo'yicha baza va kesh |
| 012 | [Infratuzilma hisobi](012-infratuzilma-hisobi.md) | ✅ VDS konfiguratsiyasi, AI sarfi — o'lchangan |
| 013 | [Firma tayyorlash va ro'yxat](013-firma-tayyorlash-va-royxat.md) | ✅ ro'yxatdan o'tish → baza → ERP to'liq oqim |
| 014 | [Ro'yxat frontend](014-royxat-frontend.md) | ✅ lending → forma → baza (brauzerda sinaldi) |
| 015 | [Akkaunt nomlash tuzatishi](015-akkaunt-nomlash-tuzatishi.md) | ✅ tenant «firma»→«akkaunt» (nom to'qnashuvi) |
| 016 | [Akkaunt kabineti](016-akkaunt-kabineti.md) | ✅ AI sarfi shaffof, limit; platforma tokeni |
| 017 | [Admin paneli](017-admin-paneli.md) | ✅ akkauntlarni ko'rish, muzlatish, platforma sarfi |
| 018 | [AI ko'rsatmasi bazadan](018-ai-korsatmasi-bazadan.md) | ✅ prompt koddan chiqdi, xavfsizlik qismi qulflangan |

### B bosqichi — Bosh kitob (buxgalteriya)

| # | Yozuv | Holat |
|---|---|---|
| 019 | [Bosh kitob poydevori](019-bosh-kitob-poydevori.md) | ✅ dvigatel, qat'iy qoidalar |
| 020 | [GL ulash (parallel)](020-gl-ulash-parallel.md) | ✅ topshirish/to'lov → provodka, eski usulga mos |
| 021 | [GL to'liq ulash + balans](021-gl-toliq-ulash-balans.md) | ✅ xarid/xarajat/avans, balans yig'ilyapti |
| 022 | [Buxgalteriya ekrani](022-buxgalteriya-frontend.md) | ✅ 7 tab; ishlab chiqarish zanjiri ulandi |

### Deploy

| # | Yozuv | Holat |
|---|---|---|
| 023 | [Deploy: test.innasoft.uz](023-deploy-test-innasoft-uz.md) | ✅ ishlayapti, Rustam aka tizimidan ajratilgan |

---

## Bog'liq hujjatlar

- [../README.md](../README.md) — hamma reja bir sahifada
- [../KOD-XARITASI.md](../KOD-XARITASI.md) — har faylda nima bor
- [../A-IJARACHILIK.md](../A-IJARACHILIK.md) — joriy bosqichning TZ si
| 024 | [Rustam aka ma'lumoti yuklandi](024-rustam-aka-malumoti-yuklandi.md) | ✅ test.innasoft.uz ga read-only nusxa, butunlik toza |
| 025 | [Ijarachilik prodda yoqildi](025-ijarachilik-prodda-yoqildi.md) | ✅ 2 akkaunt (karton+mebel), izolyatsiya, Rustam tizimi buzilmadi |
| 027 | [To'liq ma'lumot + admin panel](027-toliq-malumot-va-admin-panel.md) | ✅ kochir 9 jadval qo'shdi, admin.innasoft.uz |
| 028 | [AI sarfini yozish](028-ai-sarfi-yozish.md) | ✅ llm token qaytaradi, agent ai_sarf ga yozadi |
| 029 | [Frontend sayqali (1-tur)](029-frontend-sayqal-1.md) | ✅ buyurtma rasmlari + buxgalteriya bo'sh holati |
| 030 | [Uploads izolyatsiya](030-uploads-izolyatsiya.md) | ✅ rasm akkaunt papkasidan, leak yopildi |
| 031 | [Boshlang'ich qoldiq sehrgari](031-boshlangich-qoldiq-sehrgari.md) | ✅ balans to'ldi (1.56 mlrd, aktiv=passiv) |
| 032 | [Obuna/kabinet ekrani](032-obuna-kabinet-ekrani.md) | ✅ ERP ichida obuna + AI sarfi (ikkinchi login yo'q) |
| 033 | [Akkaunt boti](033-akkaunt-boti.md) | ✅ har akkaunt o'z Telegram boti + Mini App |
| 034 | [Bitta yordamchi](034-bitta-yordamchi.md) | ✅ 4 agent → 1, cheklov asbob darajasiga ko'chdi |
- [035 — Mobil ko'rinish: o'lchab topilgan 5 ta nuqson](035-mobil-korinish.md)
- [036 — Yordamchi oynasi: sarlavha, salom va javob ko'rinishi](036-yordamchi-oynasi.md)
- [037 — Yangi yo'nalishlar, ro'yxatdan o'tish va sinovda topilgan 5 nuqson](037-yonalishlar-va-royxat.md)
- [038 — Kirish oqimi: palitra, sehrgar va tizim yaratilish ekrani](038-kirish-oqimi.md)
