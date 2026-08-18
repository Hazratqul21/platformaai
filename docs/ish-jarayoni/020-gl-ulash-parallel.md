# 020 — GL NI AMALLARGA ULASH (parallel davr)

**Sana:** 2026-08-18
**Holat:** ✅ GL parallel yozadi va eski usulga **mos keladi**
**TZ:** [../06-YOL-XARITASI.md](../06-YOL-XARITASI.md) BOSQICH B, 3-qadam

---

## Nima qilindi

Buyurtma topshirilganda va to'lov qabul qilinganda endi **avtomatik
provodka** yoziladi. Eski hisob-kitob (`services.py`) **tegilmadi** —
ikkalasi parallel ishlaydi va `butunlik.py` ularni taqqoslaydi.

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `app/hisob/ulash.py` | **yangi**, 130 qator — ko'prik |
| `app/routers/orders.py` | `/deliver` va `/topshir-batch` da GL chaqiruvi |
| `app/routers/finance.py` | `/payments` da GL chaqiruvi |
| `app/services.py` | **nuqson tuzatildi** (quyida) |
| `tools/butunlik.py` | 5 yangi GL tekshiruvi (14 → 19) |
| `tests/gl_ulash_test.py` | **yangi** — jonli serverda moslik sinovi |

---

## Qaror 1: GL xatosi asosiy amalni TO'XTATMAYDI

`ulash.py` dagi har funksiya `try/except` bilan o'ralgan. Xato bo'lsa
**logga** yoziladi va amal davom etadi.

**Nega:** bugungi hisob-kitob ishlab turibdi va mijoz unga tayanadi.
Agar provodka yozishda xato bo'lsa va u **buyurtma topshirishni
to'xtatsa** — biz ishlayotgan narsani buzgan bo'lamiz.

Xato yashirinmaydi: `butunlik.py` GL va eski usul mos kelmayotganini
darhol ko'rsatadi.

Parallel davr tugagach (raqamlar mos kelgani isbotlangach) bu himoya
olib tashlanadi.

---

## Qaror 2: `set_status` da GL YOZILMAYDI

Statusni to'g'ridan-to'g'ri «topshirildi» ga qo'yish ham topshirish
kabi ko'rinadi. Lekin u yerda GL **ataylab yozilmaydi**.

**Sabab:** qarz eski usulda `delivered_qty` dan hisoblanadi
(`services.client_balance`). `set_status` esa `delivered_qty` ni
o'zgartirmaydi. Agar GL u yerda yozsa — GL qarz ko'rsatardi, eski usul
ko'rsatmasdi va **ikkalasi bir-biriga mos kelmay qolardi**. Parallel
davrning butun ma'nosi shu moslikda.

> Bir vaqt `set_status` ga `delivered_qty = qty` qo'shib qo'ygandim —
> keyin qaytardim. Bu **mavjud xatti-harakatni o'zgartirish** bo'lardi
> va GL ulash bilan aralashib ketardi. Agar bu haqiqatan nuqson bo'lsa,
> alohida tuzatiladi va o'z sinovi bilan.

---

## Qaror 3: qisman topshirishda ULUSH

Buyurtmadan 100 donadan 30 tasi berilsa, provodkaga **butun summa
emas, 30/100 ulushi** yoziladi:

```python
ulush = miqdor / qty
jami  = o.total * ulush
qqs   = o.qqs_summa * ulush
```

Aks holda birinchi qismda butun summa yozilib, qarz ikki barobar
chiqardi. Bu eski usuldagi `total * delivered_qty / qty` bilan **bir xil
formula** — shuning uchun ikkalasi mos keladi.

---

## `butunlik.py` — 5 yangi tekshiruv

| Tekshiruv | Nima qo'riqlaydi |
|---|---|
| balans (debet == kredit) | Дт—Кт shakli buzilmagan |
| GL qarzi (4010) == eski usul | **parallel davrning asosiy mezoni** (ogohlantirish) |
| kassa saldosi manfiy emas | pul manfiy bo'lolmaydi |
| har provodka bir marta storno | ikki marta bekor qilinmagan |
| yopilgan davrda yozuv yo'q | hisobot bilan baza mos |

Ikkinchisi **ogohlantirish** darajasida: eski ma'lumotli bazada GL
faqat yangi amallarni yozadi, shuning uchun farq **tabiiy**. Toza
bazada esa aynan mos kelishi shart — `gl_ulash_test.py` shuni
tekshiradi.

---

## `butunlik.py` MAVJUD NUQSONNI OCHDI

GL ni ulagandan keyin butunlik tekshiruvi qizil berdi:

```
❌ kutilayotgan kirim ≤ jami qarz — kirim=3 000 000 qarz=2 500 000
```

Bu **GL xatosi emas** — `services.cash_flow_forecast` dagi eski nuqson.

**Sabab:** prognoz faqat **buyurtmaga bog'langan** to'lovni ayirardi
(`Payment.order_id IN (...)`). Mijoz esa ko'pincha buyurtmani
ko'rsatmasdan **umumiy summa** to'laydi (`order_id` bo'sh) — u
hisobga olinmay qolardi.

Natijada: rahbar panelida «7 kunda 3 mln keladi» deb turadi, holbuki
mijozlarning jami qarzi 2,5 mln. Ya'ni **prognoz haqiqatdan katta**.

**Tuzatildi:** kirim mijozlarning haqiqiy qarzi bilan cheklandi —
kutilgan pul qarzdan katta bo'lolmaydi.

> Bu oltita eski xato bilan **bir oiladan**: har bo'lim o'z hisobini
> yozgani uchun raqamlar bir-biriga to'g'ri kelmasdi. Bosh kitobning
> butun maqsadi shu — va u hali to'liq ulanmasdanoq bitta nuqsonni
> topdi.

---

## Sinov natijasi

`tests/gl_ulash_test.py` — jonli server, toza baza:

```
✅ GL qarzi (4010) == eski usul jami: 1 000 000 vs 1 000 000
✅ Дт4010 Кт9010 = QQSsiz summa
✅ QQS nol -> QQS qatori umuman yozilmadi
✅ kassa 0 -> 500 000 (to'lov)
✅ to'lovdan keyin GL 500 000 == eski usul 500 000
✅ balans: debet == kredit
✅ provodka hujjatga bog'langan (buyurtma#N)
```

**`butunlik.py`: 19 tekshiruv (14 eski + 5 GL) — toza.**

### Regressiya

himoya 155/155, 9 serversiz to'plam, 22 profil to'liq sikl, 22 soha
hisob-kitobi — hammasi toza.

---

## Sinov toza baza talab qiladi

`gl_ulash_test.py` **global invariantni** tekshiradi (GL 4010 == hamma
mijozning jami qarzi). Boshqa sinovlardan qolgan ma'lumot ustiga
yurgizilsa raqamlar aralashadi.

`sinov.sh` da `yurgiz` orqali qo'shildi — u har to'plamga toza baza
beradi. Test faylining boshida ham yozib qo'yilgan.

---

## Qoldi

1. **Xarid va yetkazuvchiga to'lov** — ko'prikda funksiyalar bor,
   `purchase.py` ga ulanmagan
2. **Ish haqi va sex xarajati** — o'sha holat
3. **Balans hisoboti** (aktiv/passiv shakli)
4. **Frontend** — buxgalteriya bo'limi
5. Parallel davr yakuni: raqamlar mos kelgani isbotlangach hisobotlarni
   GL ga o'tkazish
