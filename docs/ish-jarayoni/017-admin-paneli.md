# 017 — ADMIN PANELI

**Sana:** 2026-08-18
**Holat:** ✅ ishlaydi, sinovdan o'tdi
**TZ:** [../A-IJARACHILIK.md](../A-IJARACHILIK.md) §A.6 (admin endpointlari)

---

## Nima qilindi

Biz (platforma operatorlari) endi hamma akkauntni bir joydan
ko'ramiz: holat, tarif, AI sarfi. Akkauntni muzlatish/ochish, platforma
bo'yicha jami AI sarfi, audit jurnali.

Nega kerak: 3-4 akkauntdan keyin qo'lda kuzatib bo'lmaydi.

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `app/routers/admin.py` | **yangi**, 130 qator — 5 endpoint |
| `app/platforma/db.py` | `_admin_boshlangich()` — birinchi admin muhitdan |
| `app/main.py` | admin router ulandi, middleware istisnosi, **auth blok tuzatildi** |
| `tests/admin_test.py` | **yangi**, 130 qator |
| `sinov.sh` | admin sinovi qo'shildi |

---

## Birinchi admin qayerdan keladi

Muammo: admin endpointlari `joriy_admin` talab qiladi, lekin birinchi
adminni kim yaratadi?

**Yechim:** muhit o'zgaruvchisi. `jadvallarni_yarat()` da:

```
PLATFORMA_ADMIN_LOGIN + PLATFORMA_ADMIN_PAROL berilgan bo'lsa
  va hali admin yo'q bo'lsa → yaratiladi
```

Admin **akkauntga tegishli emas** (`akkaunt_id=None`) — u bizning
xodim, tenant emas.

**Nega env:** admin paroli kod ichida yozib qo'yilmasin. Berilmasa
admin yaratilmaydi (sinovda ham shunday — faqat kerak bo'lganda beriladi).

---

## Endpointlar

| Endpoint | Nima |
|---|---|
| `GET /api/admin/akkauntlar` | hamma akkaunt: holat, tarif, tayyorlik, shu oygi AI sarfi |
| `GET /api/admin/akkaunt/{id}` | tafsilot: userlar, baza nomi, AI limiti |
| `POST /api/admin/akkaunt/{id}/holat` | muzlatish / ochish / o'chirish |
| `GET /api/admin/sarf` | platforma bo'yicha jami AI + eng ko'p sarflaganlar |
| `GET /api/admin/audit` | oxirgi platforma amallari |

Hammasi `joriy_admin` bilan himoyalangan — akkaunt egasi kira olmaydi
(403).

---

## Muzlatish mantiqi

```
holat = "muzlatilgan"
  → yozish_mumkinmi = False
  → middleware: YOZISH 402, O'QISH ochiq
  → akkaunt keshi tozalanadi (darhol kuchga kirsin)
```

`akkaunt_keshini_tozala(kod)` chaqiriladi — aks holda middleware eski
holatni keshdan o'qib, muzlatilgan akkaunt yana yozardi.

O'chirish (`ochirilgan`) ma'lumotni **o'chirmaydi** — faqat kirishni
yopadi. Haqiqiy o'chirish alohida, ehtiyot bilan (kod izohida yozilgan).

---

## Topilgan MUHIM xato — login muzlatilganda bloklanardi

Sinov ochdi: muzlatilgan akkauntda `/api/auth/login` **402** qaytardi.

Sabab: login — POST so'rov. Middleware muzlatilgan akkauntda hamma
POST ni bloklaydi. Natijada egasi tizimga **kira olmasdi**, demak
«o'qish va eksport ochiq» qoidasi buzilardi — o'qish uchun ham kirish
kerak.

**Tuzatildi:** `/api/auth/*` har doim ochiq (login, logout, parol).
Login POST bo'lsa ham ma'lumotni o'zgartirmaydi.

> Bu qoida hujjatda bor edi («o'qish ochiq qoladi»), lekin login
> ham blok bo'lgani uchun amalda buzilardi. Sinov to'g'ri holatni
> tekshirgani uchun ushladi.

---

## Sinov natijasi

`tests/admin_test.py` — TestClient, admin muhitdan, ikki akkaunt:

```
1. ikki akkaunt ro'yxatdan o'tadi
2. admin kiradi (roli=admin)
3. akkaunt egasi admin panelidan 403; tokensiz 401
4. admin hamma akkauntni ko'radi (2 ta)
5. akkaunt muzlatiladi -> yozish 402, O'QISH 200 (ochiq)
6. admin qayta ochadi -> yozish 200
7. audit: akkaunt_yaratildi + holat_ozgardi
8. noto'g'ri holat rad etildi
```

### Regressiya

himoya 136/136, genui, platforma, ijarachilik, royxat, kabinet — toza.

---

## Xavf va qo'riqlash

| Xavf | Qo'riqlash |
|---|---|
| Egaga admin huquqi tegishi | `joriy_admin` (platforma_roli == admin) |
| Muzlatilgan akkaunt yozishda davom etishi | kesh tozalanadi, 5-sinov |
| Muzlatilgan egasi kira olmasligi | `/api/auth/*` ochiq, 5-sinov |
| Admin paroli kodda | muhit o'zgaruvchisi |
| O'chirishda ma'lumot yo'qolishi | `ochirilgan` faqat kirishni yopadi |

---

## Qoldi

1. **Admin va kabinet frontend** — hozir faqat backend
2. **Haqiqiy o'chirish** (ma'lumot bilan) — alohida, tasdiq bilan
3. **bot.py** akkaunt bo'yicha
4. **Obuna to'lovi** — tarif o'zgartirish + to'lov (integratsiya)
