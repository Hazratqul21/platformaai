# 003 — HISOB-KITOB VA TOPILGAN OLTITA XATO

**Sana:** retrospektiv
**Fayllar:** `app/services.py` (1 077, 34 funksiya) · `app/kassa_sync.py` (164)

---

## Nima qilindi

Hamma hisob-kitob bitta faylga yig'ildi. Router faqat chaqiradi,
o'zi hisoblamaydi.

**Nega:** bir vaqtlar qarz ikki joyda hisoblanardi — moliya ekranida
va AI agentida. Formulalar ajralib ketdi va AI 1 457 mln, ekran
853 mln ko'rsatdi. Bitta manba bo'lmasa bu muqarrar.

---

## Guruhlar

| Guruh | Funksiyalar |
|---|---|
| Formula | `eval_formula`, `safe_formula_check` — foydalanuvchi yozgan formula, AST bilan tekshiriladi (`eval` xavfsiz emas) |
| Tannarx | `unit_cost`, `quote`, `retsept_tannarx`, `ustama_foizi` |
| Ombor | `fifo_writeoff`, `raw_stock_for`, `low_stock_alerts` |
| Qarz | `client_balance`, `client_balances_batch`, `debt_aging`, `supplier_balance`, `credit_check` |
| Pul | `cash_flow_forecast` |
| QQS | `qqs_hisobla` |
| Kadrlar | `payroll` |

---

## QQS — uch rejim

```
yoq     QQS yo'q
ustiga  narx + QQS      (mijoz ko'proq to'laydi)
ichida  narx ichida     (narxdan ajratib olinadi)
```

**`total` — doim mijoz to'laydigan summa.** Bu qoida buzilsa qarz
noto'g'ri chiqadi (quyida shunday bo'lgan).

Stavka buyurtmada qotiriladi.

---

## FIFO — nega partiya

Xomashyo har safar boshqa narxda keladi. «O'rtacha narx» soddaroq,
lekin tannarx soxta chiqadi. FIFO: eng eski partiyadan yechiladi,
har yechim qaysi partiyadan ekani yoziladi.

Retsept bo'yicha yechish **atomar** — yo hammasi, yo hech biri.
Yarim yechilgan holat omborni buzadi.

---

## Haqiqiy ma'lumotda topilgan OLTITA xato

Rustam akaning ma'lumotidan olingan read-only nusxada sinalganda
chiqdi. **Demo ma'lumotda birortasi ham ko'rinmagan edi.**

### 1. QQS qarzdan tushib qolgan
Mijozga 1 120 000 hisob yozilgan, tizim 1 000 000 qarz deb ko'rsatgan.
Sabab: qarz `unit_price × delivered` bilan hisoblangan — QQS siz.
**Tuzatildi:** `total × (delivered/qty)`.

### 2. Qarz yoshi status NOMIGA bog'langan
Faol profil boshqa status nomlarini ishlatganda qarz yoshi bo'sh
chiqqan. **Tuzatildi:** mezon `delivered_qty > 0`.

### 3. Manfiy `opening_balance` (avans) hisobga olinmagan
Mijoz oldindan to'lagan bo'lsa boshlang'ich qoldiq manfiy bo'ladi.
Kod uni qarz deb qo'shib yuborgan. **Faqat haqiqiy ma'lumotda
chiqdi** — demo generatorda avans yo'q edi.

### 4. Pul oqimida noto'g'ri sana ustuni
`due_date` ishlatilgan, `payment_due_date` bo'lishi kerak edi.
**Tuzatildi:** `coalesce(payment_due_date, due_date)`.

### 5. Yetkazib beruvchi qarzi chiqimda yo'q
Prognoz faqat kirimni ko'rsatgan — «pulimiz ko'p» degan noto'g'ri
manzara. **Tuzatildi:** to'lanmagan xaridlar chiqimga qo'shildi.

### 6. `Decimal × float` — TypeError
`quote()` da miqdor float kelganda 500 xatosi. **Tuzatildi:**
`Decimal(str(qty))`.

---

## Xulosa — bu xatolar nimani o'rgatdi

1. **Demo ma'lumot yetarli emas.** Oltitasining hech biri demo bazada
   ko'rinmagan.
2. **Bir xil raqam ikki joyda hisoblanmasin.** AI va ekran
   ajralishining sababi shu edi.
3. **Tuzatish yetarli emas — qo'riqchi kerak.** Shuning uchun
   `tools/butunlik.py` yozildi: 14 o'zgarmas, jumladan «qarz yoshi
   bo'laklari jamiga teng» va «kutilayotgan kirim umumiy qarzdan
   oshmaydi». Bu oltitasining qaytishini ushlaydi.

---

## `kassa_sync.py`

Pul beshta bo'limda yuriladi (mijoz to'lovi, sex xarajati, xodim
avansi, xarid to'lovi, yetkazib beruvchiga to'lov), kassa jurnali
esa bitta bo'lishi kerak. Bu ko'prik har harakatni jurnalga yozadi.

**Aks holda:** kassada 10 mln, hisobotda 12 mln — va farq qayerdan
kelganini topib bo'lmaydi.

---

## Ijarachilikda

`services.py` **o'zgarmaydi** — global holat yo'q, hamma narsa
`db` orqali kiradi. 1 077 qatorlik eng katta fayl eng xavfsizi.
