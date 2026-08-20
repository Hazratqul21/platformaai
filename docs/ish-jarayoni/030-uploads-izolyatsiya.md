# 030 — UPLOADS AKKAUNT BO'YICHA IZOLYATSIYA

**Sana:** 2026-08-20
**Holat:** ✅ ishlaydi — rasm faqat o'z akkauntida ochiladi

---

## Muammo

Rasmlar flat `/app/uploads/` papkada edi va `StaticFiles` mount bilan
berilardi. Ijarachilikda bu **leak**: `karton.innasoft.uz/uploads/
order_86.jpg` va `mebel.innasoft.uz/uploads/order_86.jpg` bitta faylni
berardi — bir akkaunt boshqasining rasmini ko'ra olardi.

---

## Yechim

### Saqlash — akkaunt papkasiga (`orders.py`)

```
/app/uploads/<baza_nomi>/order_*.jpg    ← inna_karton, inna_mebel...
```

`tenancy.kalit()` papka nomini beradi (ijarachiliksiz rejimda
"_yagona").

### Berish — akkaunt-aware route (`main.py`)

Flat `StaticFiles` mount O'CHIRILDI, o'rniga:

```python
@app.get("/uploads/{fayl}")
def upload_fayl(fayl):
    yol = UPLOAD_DIR / tenancy.kalit() / fayl   # JORIY akkaunt papkasi
    if yol.is_file(): return FileResponse(yol)
    raise HTTPException(404)
```

- Host'dan aniqlangan akkauntning papkasidan beriladi
- **Ijarachilikda flat fallback YO'Q** — aks holda subdomen orqali
  leak bo'lardi. Yagona rejimda esa eski flat rasmlar ham ishlaydi
- Path traversal (`..`, `/`) `_SAFE_FAYL` regex bilan rad etiladi

---

## Isbot

| Tekshiruv | Natija |
|---|---|
| karton o'z rasmini ochadi | ✅ 200 |
| mebel karton rasmini ochadi | ✅ **404 (izolyatsiya)** |
| path traversal `../etc/passwd` | ✅ 400 (rad) |

Mavjud 79 karton rasmi `/app/uploads/inna_karton/` ga ko'chirildi.

---

## Nozik joy — nega auth yo'q

`/uploads/{fayl}` auth talab QILMAYDI: `<img src>` brauzerda auth
sarlavha yubormaydi. Shuning uchun URL bo'yicha ochiq (avvalgi
StaticFiles ham shunday edi), lekin endi akkaunt papkasi bilan
izolyatsiyalangan. Fayl nomi tasodifiy (`order_ID_timestamp`),
taxmin qilib topish qiyin. himoya_audit ochiq ro'yxatida sababi
bilan.

---

## Regressiya

himoya_audit 157/157.
