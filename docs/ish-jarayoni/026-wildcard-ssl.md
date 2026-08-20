# 026 — WILDCARD SSL (*.innasoft.uz)

**Sana:** 2026-08-20
**Holat:** ✅ ishlaydi — istalgan yangi akkaunt avtomat HTTPS

---

## Nima qilindi

`*.innasoft.uz` uchun Let's Encrypt wildcard sertifikati olindi.
Endi yangi akkaunt ro'yxatdan o'tganda subdomeni (`non.innasoft.uz`)
**darhol HTTPS bilan** ishlaydi — qo'lda sertifikat qo'shish kerak emas.

---

## Nega wildcard kerak edi

Ilgari har akkaunt subdomeni uchun alohida HTTP-01 sertifikat kerak
edi (qo'lda). O'z-o'ziga xizmat SaaS da bu ishlamaydi: mijoz
`non.innasoft.uz` ga ro'yxatdan o'tsa, HTTPS darhol kerak.

Wildcard sertifikat bitta `*.innasoft.uz` bilan HAMMA subdomenni
qamraydi.

---

## Usul: DNS-01 (qo'lda TXT)

Let's Encrypt wildcard'ni faqat DNS-01 orqali beradi (HTTP-01 emas).
Foydalanuvchi tanlovi: **qo'lda TXT** (Cloudflare API tokensiz).

```
certbot certonly --manual --preferred-challenges dns -d "*.innasoft.uz"
  --manual-auth-hook /tmp/print_txt.sh   # TXT ni faylga yozib, flag kutadi
  --manual-cleanup-hook /bin/true
  --cert-name wildcard.innasoft.uz
```

**Muammo:** certbot --manual interaktiv, SSH esa emas. Yechim: auth
hook TXT qiymatni faylga yozadi va `/tmp/txt_done` flagi paydo
bo'lguncha kutadi (`setsid` bilan SSH uzilsa ham yashaydi). Men TXT
ni foydalanuvchiga berdim → u Cloudflare'ga qo'shdi → men flagni
yaratdim → certbot yakunladi.

**Yo'l-yo'lakay:** foydalanuvchi avval Content ga `_acme-challenge`
(Name) ni yozib qo'ydi — dig bilan aniqladim va tuzatishni so'radim.

---

## nginx

`accounts.innasoft.uz.conf`: `server_name *.innasoft.uz` (aniq
`karton/mebel` o'rniga). Aniq nomli bloklar (test/tizim/archive/base/
diydor) wildcard'dan **ustun** turadi — Rustam tizimi va boshqa
loyihalar tegilmadi.

`proxy_set_header Host $host` — MUHIM: app subdomenga qarab akkauntni
aniqlaydi.

---

## Isbot

| Tekshiruv | Natija |
|---|---|
| YANGI `non.innasoft.uz` ochildi | ✅ darhol HTTPS 200, "Non zavodi" |
| (men sertifikat qo'shmadim) | ✅ wildcard avtomat qamradi |
| karton/mebel ogohlantirishsiz | ✅ 200 |
| tizim.innasoft.uz (Rustam) | ✅ 200, buzilmadi |
| sertifikat SAN | ✅ `DNS:*.innasoft.uz`, 2026-11-18 gacha |

---

## ⚠️ MUHIM: avto-yangilanish ISHLAMAYDI

Bu sertifikat `--manual` bilan olingan. Certbot avto-yangilash
vazifasini qo'ydi, LEKIN u ham `--manual` hook ni chaqiradi va
`/tmp/txt_done` flagini kutib **30 daqiqada yiqiladi** (avtomat TXT
qo'sha olmaydi).

**Demak ~90 kunda (2026-11-18 gacha) QO'LDA yangilash kerak:** yana
shu TXT jarayoni. YOKI:

**Tavsiya:** keyinroq **Cloudflare API tokeniga** o'tish — u bilan
`certbot-dns-cloudflare` plaginини o'rnatib, avto-yangilanish to'liq
ishlaydi. Prod uchun to'g'ri yechim shu.

Eslatma taqvimga qo'yilsin: **2026-11-01 atrofida** sertifikatni
yangilash yoki API tokenga o'tish.

---

## Yakuniy SaaS holati

```
test.innasoft.uz    → ro'yxatdan o'tish (lending)
<kod>.innasoft.uz   → akkaunt, avtomat HTTPS (wildcard)
tizim.innasoft.uz   → Rustam JONLI (parallel, tegilmagan)
```

Mijoz ro'yxatdan o'tadi → sekundlarda o'z HTTPS subdomeniga ega
bo'ladi. O'z-o'ziga xizmat SaaS — TAYYOR.

Hozirgi akkauntlar: karton (Rustam), mebel (sinov), non (wildcard
isboti).
