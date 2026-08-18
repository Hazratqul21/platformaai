# 018 — AI KO'RSATMASI KODDAN BAZAGA

**Sana:** 2026-08-18
**Holat:** ✅ ishlaydi, brauzerda sinaldi
**Sabab:** foydalanuvchi so'radi — «agentlarga prompt beryapmiz-ku,
shuni o'zgartirsa bo'ladigan qilib qo'y, bu AI ni yangilashga xizmat
qiladi»

---

## Nima qilindi

AI agentlarining ko'rsatmasi (prompt) endi **koddan emas, bazadan**
o'qiladi. Mijoz o'ziga moslaydi, biz esa hamma akkauntga yangi
ko'rsatma bera olamiz — **kod qayta joylanmasdan**.

Bu loyihaning o'z tamoyilining davomi: soha koddan JSON'ga chiqarilgan
edi (`domain.py`), endi prompt ham chiqdi.

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `app/korsatma.py` | **yangi**, 120 qator — uch darajali hal qilish + kesh |
| `app/models.py` | `AgentSozlama` (mijoz bazasida) |
| `app/platforma/models.py` | `AgentShablon` (boshqaruv bazasida) |
| `app/agent.py` | xavfsizlik qismi ajratildi, halqa `korsatma.ol()` dan oladi |
| `app/routers/agent.py` | `GET/PUT/DELETE /api/agent/korsatma` |
| `app/routers/admin.py` | `GET/PUT/DELETE /api/admin/agent-shablon` |
| `static/js/pages/settings.js` | «AI ko'rsatmasi» tabi (+110 qator) |
| `tests/korsatma_test.py` | **yangi**, 9 bo'lim |

---

## Uch daraja — ustuvorlik

```
1. KOD        agent.AGENTLAR[k]["korsatma"]   ← zaxira, yo'qolmaydi
2. PLATFORMA  agent_shablon (boshqaruv bazasi) ← biz, hammaga
3. AKKAUNT    agent_sozlama (mijoz bazasi)     ← mijoz, o'ziga
```

Pastdagisi yuqoridagini bosadi. Ya'ni:

- Biz AI ni yaxshilasak — **hamma akkaunt darhol oladi**, deploy yo'q
- Lekin mijoz o'zi moslagan bo'lsa — **uning tanlovi buzilmaydi**

Bu naqsh `app/profiles/*.json` bilan bir xil: JSON = shablon, baza =
haqiqat.

---

## ⚠️ ENG MUHIM QAROR: xavfsizlik qismi TAHRIRLANMAYDI

Ko'rsatma ikkiga bo'lindi:

```
TAHRIRLANADI              MAJBURAN QO'SHILADI (o'chirib bo'lmaydi)
────────────────          ────────────────────────────────────────
rol ta'rifi               _UMUMIY_USLUB:
ish tartibi                 «Raqamlarni aniq ayt, taxmin qilma —
atamalar                     bilmasang asbob chaqirib bil»
                            «Ma'lumot yo'q bo'lsa o'ylab topma»
                          + GenUI shartnomasi
```

**Nega:** agar mijoz «raqamni o'ylab topma» qoidasini o'chira olsa, AI
qarz summasini taxmin qilib aytishi mumkin. Bu bir marta yetadi —
ishonch yo'qoladi ([../00-STRATEGIYA.md](../00-STRATEGIYA.md) §0.5).

Ekranda xavfsizlik qismi **ko'rsatiladi**, lekin faqat o'qish uchun —
mijoz nima qo'shilayotganini biladi, lekin o'zgartira olmaydi.

---

## Yo'l-yo'lakay topilgan XATO

Ko'rsatmani ajratganda ma'lum bo'ldi: **`sozlash` agentida
`_UMUMIY_USLUB` umuman yo'q edi.**

Sabab: `_UMUMIY_USLUB` faylda `TIZIM_KORSATMASI` dan **keyin**
e'lon qilingan, shuning uchun unga qo'shib bo'lmagan. Qolgan uch
agentda `+ _UMUMIY_USLUB` bor edi, sozlashda yo'q.

Ya'ni **tizimni yig'adigan agent** (eng ko'p yozadigan, profil
yaratadigan) «raqamni o'ylab topma» qoidasisiz ishlagan.

Endi `korsatma.ol()` uni **hammasiga bir xil** qo'shadi.

---

## Xarajat chegarasi — 09-hujjatdan kelib chiqdi

`MAX_UZUNLIK = 8000` belgi. Sabab o'lchangan:
[../09-INFRATUZILMA.md](../09-INFRATUZILMA.md) §9.7 da ko'rsatilgan —
ko'rsatma **har so'rovda** yuboriladi, uzunligi to'g'ridan-to'g'ri
pulga aylanadi.

Ekranda ham yozilgan: «Ko'rsatma har so'rovda AI ga yuboriladi — u
qancha uzun bo'lsa, AI shuncha qimmatga tushadi».

`MIN_UZUNLIK = 40` — bo'sh ko'rsatma ishlamaydigan agent degani.

---

## Kesh — 013 dagi xatoni takrorlamaslik

Kesh **akkaunt bo'yicha** (`tenancy.kalit()`), `domain._KESH` bilan
bir xil naqsh. Ko'rsatma o'zgarganda:

- akkaunt o'zgartirsa → **o'sha akkauntning** keshi tozalanadi
- biz platforma shablonini o'zgartirsak → **hamma** kesh tozalanadi

013-qadamda kesh-miss yo'li unutilgan edi va `karton` ga tushib
qolgandi. Bu safar hal qilish zanjiri bitta funksiyada (`ol()`) va
kesh-miss ham o'sha zanjirdan o'tadi.

---

## Sinov natijasi

`tests/korsatma_test.py` — 9 bo'lim, ikki akkaunt:

```
1. standart holat — hammasi koddan
2. akkaunt o'z ko'rsatmasini yozdi
3. IKKINCHI akkauntga o'tmadi        ← ijarachilik tekshiruvi
4. xavfsizlik qismi yo'qolmadi       ← eng muhimi
5. chegaralar: qisqa/uzun/yo'q agent rad etildi
6. standartga qaytarish
7. platforma darajasi — ikkala akkaunt ham oldi
8. akkaunt tanlovi platformanikidan ustun
9. tokensiz 401
```

### Brauzerda

Sozlamalar → «AI ko'rsatmasi»: 4 ta agent, har biri tahrirlanadigan
maydon, belgi hisoblagichi, manba yorlig'i («Standart» / «Platforma
yangilagan» / «Siz o'zgartirgansiz»), xavfsizlik qismi faqat o'qish
uchun.

Tahrir qilib saqlandi → bazada `agent_sozlama` yozuvi paydo bo'ldi,
auditga **kim o'zgartirgani** yozildi. Konsol toza.

### Regressiya

himoya 142/142, genui, platforma, ijarachilik, royxat, kabinet,
admin — toza. Yagona rejim: 22 profil to'liq siklidan o'tdi.

---

## Xavf va qo'riqlash

| Xavf | Qo'riqlash |
|---|---|
| Xavfsizlik qoidasi o'chirilishi | `ol()` da majburan qo'shiladi, 4-sinov |
| Uzun prompt AI ni qimmatlashtirishi | `MAX_UZUNLIK` + ekranda ogohlantirish |
| Bo'sh prompt agentni buzishi | `MIN_UZUNLIK` |
| Bir akkaunt prompti boshqasiga o'tishi | kesh akkaunt bo'yicha, 3-sinov |
| Kim o'zgartirgani noma'lum qolishi | `audit_logs` + `platforma_audit` |
| Koddagi zaxira yo'qolishi | hech qachon o'chirilmaydi, `DELETE` unga qaytaradi |

---

## Qoldi

1. **Admin panel frontendi** — platforma shabloni hozir faqat API
2. Ko'rsatma **versiyalari** — eskisiga qaytarish (hozir faqat
   «standartga qaytarish»)
3. Ko'rsatma o'zgargach **sinov savoli** yuborish — AI hali to'g'ri
   javob beryaptimi
