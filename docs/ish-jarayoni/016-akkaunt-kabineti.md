# 016 — AKKAUNT KABINETI (AI sarfi shaffof)

**Sana:** 2026-08-18
**Holat:** ✅ ishlaydi, sinovdan o'tdi
**TZ:** [../07-TARQATISH.md](../07-TARQATISH.md) §7.6, [../08-FRONTEND.md](../08-FRONTEND.md) §8.4

---

## Nima qilindi

Akkaunt egasi endi **o'z AI sarfini ko'radi** va **oylik limit
qo'yadi**. Bu — «AI xarajati mijozdan ALOHIDA olinadi» qarorining
ekrandagi ko'rinishi. 009-qadamda yaratilgan `ai_sarf`/`ai_limitlar`
jadvallari endi endpointga ulandi.

---

## Fayllar

| Fayl | O'zgarish |
|---|---|
| `app/platforma/auth.py` | **yangi**, 60 qator — platforma tokeni, `joriy_user`/`joriy_admin` |
| `app/routers/kabinet.py` | **yangi**, 120 qator — `/mening`, `/ai-sarf`, `/ai-limit` |
| `app/routers/royxat.py` | `/kir` endi platforma tokeni beradi |
| `app/main.py` | kabinet router ulandi, middleware istisnosi |
| `tests/kabinet_test.py` | **yangi**, 130 qator |
| `tests/himoya_audit.py` | `joriy_user`/`joriy_admin` himoya sifatida tan olinadi |
| `sinov.sh` | kabinet sinovi qo'shildi |

---

## Ikki xil autentifikatsiya — nega

Bu qadamda muhim ajratish paydo bo'ldi:

```
ERP TOKEN (app/auth.py)          PLATFORMA TOKEN (platforma/auth.py)
─────────────────────────        ──────────────────────────────────
mijoz bazasidagi auth_tokens     boshqaruv bazasidagi platforma_tokenlar
subdomen ICHIDA                  app.innasoft.uz da (subdomensiz)
ERP ma'lumotiga kirish           tarif, AI sarfi, obuna
Rahbar/Buxgalter/... rollari     egasi / admin
```

**Nega ikkitasi kerak:** kabinet subdomen bazasi **tayyor
bo'lishidan oldin** ham kerak bo'ladi (masalan obuna to'lovi baza
o'chirilgan holatda ham ochiq). Va u boshqaruv bazasi bilan
ishlaydi, mijoz bazasi bilan emas. Bitta token ikkalasiga yaramaydi.

---

## Uch endpoint

| Endpoint | Nima |
|---|---|
| `GET /api/kabinet/mening` | akkaunt + tarif + obuna + AI sarfi xulosasi |
| `GET /api/kabinet/ai-sarf` | tafsilot: agent bo'yicha, foydalanuvchi bo'yicha |
| `POST /api/kabinet/ai-limit` | oylik limit o'rnatish |

### Shaffoflik — nega tafsilot

`/ai-sarf` «186 000 so'm» qayerdan kelganini ko'rsatadi: qaysi agent
qancha, qaysi foydalanuvchi qancha. Hujjatdagi qoida:

> «AI uchun 186 000 so'm» degan hisob tushuntirishsiz kelsa, mijoz
> ishonchini yo'qotadi.

Shuning uchun raqam yalang'och kelmaydi — har doim taqsimoti bilan.

---

## Limit mantiqi — 009 dan qayta ishlatildi

`POST /api/kabinet/ai-limit` `ai_limitlar` ga yozadi, `/mening`
esa `px.limit_holati()` ni chaqiradi (009-qadamda yozilgan va
sinalgan). Ya'ni yangi mantiq yozilmadi — mavjud funksiya ulandi.

Qoida o'zgarmaydi: **80% ogoh, 100% AI to'xtaydi, ERP ishlayveradi.**

---

## Sinov natijasi

`tests/kabinet_test.py` — TestClient, boshqaruv bazasiga AI sarfi
qo'yiladi, kabinet to'g'ri ko'rsatishini tekshiradi:

```
1. ro'yxat -> /kir -> platforma tokeni
2. tokensiz 401, soxta token 401
3. AI sarfi qo'shildi (gemini + sonnet)
4. /mening: 2 so'rov, sarf > 0, limitsiz = cheklovsiz
5. /ai-sarf: 2 agent, 2 foydalanuvchi; eng ko'p sarflagan (sozlash) birinchi
6. limit sarfning 90% i -> ogoh; 50% i -> AI to'xtatilgan
7. manfiy limit rad etildi
```

### Regressiya

himoya 131/131, genui, platforma, ijarachilik, royxat — hammasi toza.

---

## Topilgan xato — router ulanmagan qolgan

`/api/kabinet/*` 404 qaytardi. Sabab: `include_router` qo'shilishi
kerak bo'lgan joyda izoh matni **015-qadamdagi rename** tufayli
o'zgargan edi («firmasiz» → «akkauntsiz»), shuning uchun avtomatik
almashtirish topolmadi va faqat import qo'shildi.

Qo'lda `app.include_router(kabinet_router.router)` qo'shildi.

> Saboq: rename dan keyin matnga tayangan avtomatik almashtirishlar
> ishlamay qolishi mumkin. Endpoint 404 bo'lsa — birinchi navbatda
> router ulanganini tekshirish kerak.

---

## Xavf va qo'riqlash

| Xavf | Qo'riqlash |
|---|---|
| Kabinet endpointi himoyasiz deb topilishi | `joriy_user` audit HIMOYA to'plamiga qo'shildi (131/131) |
| Boshqa akkaunt sarfini ko'rish | token → user → akkaunt_id, faqat o'ziniki |
| Egasidan boshqa limit qo'yishi | `platforma_roli in (egasi, admin)` |
| Token abadiy yashashi | 30 kun, muddati o'tganlar tozalanadi |

---

## Qoldi

1. **Admin paneli** (`/api/admin/*`) — biz hamma akkauntni ko'ramiz
2. **Kabinet frontend** — hozir faqat backend (ekran keyin)
3. **Obuna to'lovi** — tarif o'zgartirish, to'lov tizimi (B/integratsiya)
4. **bot.py** akkaunt bo'yicha
