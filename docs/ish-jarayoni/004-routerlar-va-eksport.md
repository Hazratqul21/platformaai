# 004 — ROUTERLAR VA HUJJAT EKSPORTI

**Sana:** retrospektiv
**Fayllar:** `app/routers/*.py` — 13 fayl, **125 endpoint**

---

## Nima qilindi

HTTP qatlami. Har router bitta bo'limga javob beradi va hisob-kitobni
`services.py` ga topshiradi.

| Fayl | Endp. | Nima |
|---|---|---|
| `catalog.py` | 20 | material, birlik, lavozim, xizmat, formula |
| `orders.py` | 16 | buyurtma sikli, smeta, retsept, status, topshirish |
| `warehouse.py` | 12 | FIFO partiyalar, qoldiq, inventarizatsiya |
| `reports.py` | 10 | Excel / PDF / DOCX |
| `hr.py` | 10 | xodim, sdelshina, ish haqi, avans |
| `finance.py` | 10 | to'lov, qarzdor, pul oqimi, dashboard |
| `agent.py` | 8 | AI chat, oqim, amal, faoliyat |
| `constructor.py` | 7 | no-code jadval quruvchi |
| `purchase.py` | 6 | xarid, yetkazib beruvchi qarzi |
| `kassa.py` | 5 | kassa jurnali |
| `clients.py` | 5 | mijoz, detalizatsiya |
| `users.py` | 4 | RBAC, parol |
| `soha.py` | 4 | profil boshqaruvi |

---

## Naqsh: har endpoint bir xil ko'rinadi

```python
@router.get("/api/...")
def nimadir(db: Session = Depends(get_db),
            user = Depends(auth.get_user)):
```

**Ikki foydasi bor:**

1. **Himoya unutilmaydi** — `tests/himoya_audit.py` kodni AST bilan
   o'qib, `Depends(get_user)` siz endpointni topadi. Serversiz
   ishlaydi, ya'ni har commit da yuritish arzon.

2. **Ijarachilik arzon bo'ladi** — `get_db` ni firma bo'yicha
   qilish uchun **125 endpointning birortasiga tegilmaydi**.
   Almashtirish bitta faylda.

Ikkinchisi rejalashtirilgan edi, birinchisi amalda isbotlangan.

---

## `orders.py` — eng murakkab router

Buyurtma sikli: yaratish → smeta → sexga → tayyor → topshirish
(qisman ham). Har o'tishda:

- status **ma'nosi** tekshiriladi (`domain.modul`)
- `ishlab_chiqarish` ga o'tganda retsept bo'yicha ombor yechiladi
- topshirilganda qarz yangilanadi va kassaga yoziladi
- Telegram tasdiq zanjiri ishga tushadi

**Muhim:** GenUI ning `buyurtma_maqomi` amali shu yerdagi
`set_status` ni chaqiradi — o'z mantiqini yozmaydi. Aks holda ombor
yechish qoidasi ikki joyda bo'lardi va biri eskirardi.

---

## `reports.py` — hujjatlar

Akt, nakladnoy, sverka — Excel (`openpyxl`), PDF, DOCX.

Rekvizitlar (firma nomi, INN, manzil, hisob raqami) sozlamadan
olinadi — kodda yozilmaydi.

**Cheklov, halol aytiladi:** bu hujjatlar **yuridik kuchga ega
emas** — EHF ulanmaguncha. Buni sotuvda ham aytish kerak
([../00-STRATEGIYA.md](../00-STRATEGIYA.md) §0.6).

---

## `constructor.py` — no-code jadval

`custom_sections` + `custom_records`: foydalanuvchi o'zi jadval
yasab, ustunlarini belgilaydi. AI konstruktorining oddiy shakli.

---

## Tekshiruv

- `tests/himoya_audit.py` — 125/125 himoyalangan, serversiz
- `tests/audit.py` — 38 endpoint jonli serverda, 0 xato
- `tests/e2e_test.py` — to'liq hayotiy sikl
