import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

load_dotenv()

from .db import Base, engine, get_db, SessionLocal  # noqa: E402
from . import auth as auth_mod  # noqa: E402
from .migrate import (run_migrations, backfill_soha,  # noqa: E402
                      profillarni_yukla, jadvalni_qayta_qur)
from . import models as m  # noqa: E402
from . import domain  # noqa: E402
from .seed import seed  # noqa: E402
from .bot import start_bot_bg  # noqa: E402
from .routers import (clients, orders, warehouse, hr, finance, reports,  # noqa: E402
                      users, constructor, catalog, purchase, kassa, soha,
                      agent)

logging.basicConfig(level=logging.INFO)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def prod_tekshiruvi() -> None:
    """`MUHIT=prod` bo'lsa xavfli standart sozlamalar bilan ishga tushmaydi.

    Sinovda qulay bo'lgan narsalar (standart parol, ochiq CORS, demo
    ma'lumot) prodda xavf. Bularni eslab qolishga tayanmaymiz —
    server o'zi to'xtaydi va nima qilish kerakligini aytadi.
    """
    if os.getenv("MUHIT", "").lower() not in {"prod", "production"}:
        return
    xatolar = []
    url = os.getenv("DATABASE_URL", "")
    if ":innasoft@" in url or ":postgres@" in url:
        xatolar.append("POSTGRES_PASSWORD стандарт қийматда — .env да ўзгартиринг")
    if "*" in ALLOWED_ORIGINS:
        xatolar.append("CORS_ORIGINS=* — аниқ доменни ёзинг")
    if os.getenv("SEED_DEMO") == "1":
        xatolar.append("SEED_DEMO=1 — прод базага демо маълумот юкланмасин")
    if xatolar:
        raise RuntimeError(
            "Прод режимида ишга туширилмади:\n  · " + "\n  · ".join(xatolar))


@asynccontextmanager
async def lifespan(app: FastAPI):
    prod_tekshiruvi()
    Base.metadata.create_all(engine)   # yangi jadvallar
    run_migrations(engine)             # mavjud jadvallarga yangi ustunlar
    # `orders.qty` butun sondan kasrga o'tdi (2.5 m³ beton) — SQLite da
    # ustun turini o'zgartirish uchun jadval qayta quriladi.
    jadvalni_qayta_qur(engine, "orders", m.Order)
    db = SessionLocal()
    try:
        # Profil seed'dan OLDIN yuklanadi: seed buyurtma yaratganda
        # soha_yoz() allaqachon to'g'ri profilni bilishi kerak.
        profillarni_yukla(db)
        domain.qayta_yukla(db)
        seed(db)
        backfill_soha(db)   # eski buyurtmalar attributes'siz qolmasin
    finally:
        db.close()
    start_bot_bg()
    yield


app = FastAPI(title="TIZIM — ishlab chiqarish boshqaruvi",
              version="1.0", lifespan=lifespan)

# CORS standarti «*» EMAS. Frontend shu serverdan beriladi, ya'ni
# cross-origin umuman kerak emas — «*» esa har qanday sayt brauzerdan
# API javobini o'qiy olishini bildirardi. Boshqa domendagi frontend
# kerak bo'lsa `CORS_ORIGINS` ga aniq yoziladi.
ALLOWED_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
if ALLOWED_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                       allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def ijarachilik(request, call_next):
    """So'rovni MIJOZGA bog'laydi.

    Ijarachilik o'chiq bo'lsa hech nima qilmaydi — bitta baza rejimi
    aynan avvalgidek ishlaydi.

    Firma topilmasa 404 emas, 400: «bunday firma yo'q» degani manzil
    xato ekanini bildiradi, mavjud emasligini emas — mijoz kodlarini
    tashqaridan sanab chiqishga yo'l bermaslik uchun javob bir xil.
    """
    from . import tenancy
    if not tenancy.yoqilganmi():
        return await call_next(request)

    yol = request.url.path
    # Statik fayllar va salomatlik tekshiruvi firmasiz ham beriladi.
    if yol == "/" or yol.startswith("/static") or yol == "/api/health":
        return await call_next(request)

    firma = tenancy.sorovdan_firma(request.headers.get("host", ""),
                                   request.headers.get("x-firma", ""))
    if firma is None:
        return JSONResponse({"detail": "Firma aniqlanmadi"}, status_code=400)

    # Obuna tugagan firma O'QIY oladi, lekin YOZA olmaydi.
    # Ma'lumot garovga olinmaydi (docs/07-TARQATISH.md §7.7).
    if (not firma.yozish_mumkinmi
            and request.method not in ("GET", "HEAD", "OPTIONS")):
        return JSONResponse(
            {"detail": "Obuna muddati tugagan — ma'lumot o'qish uchun "
                       "ochiq, yangi yozuv kiritilmaydi"}, status_code=402)

    token = tenancy.ornat(firma)
    try:
        return await call_next(request)
    finally:
        tenancy.tozala(token)


@app.middleware("http")
async def no_cache_static(request, call_next):
    """Statik fayllar keshlanmasin — yangilanishlar darhol yetib borsin."""
    response = await call_next(request)
    p = request.url.path
    if p == "/" or p.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


class LoginIn(BaseModel):
    login: str
    password: str


@app.post("/api/auth/login", tags=["Auth"])
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    return auth_mod.login(db, data.login, data.password, auth_mod.ip_kaliti(request))


@app.get("/api/auth/me", tags=["Auth"])
def me(user=Depends(auth_mod.get_user)):
    return {"name": user.name, "role": user.role, "login": user.login}


@app.post("/api/auth/logout", tags=["Auth"])
def logout_endpoint(authorization: str = Header(default=""), db=Depends(get_db)):
    token = authorization.removeprefix("Bearer ").strip()
    auth_mod.logout(token, db)
    return {"ok": True}


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


@app.post("/api/auth/change-password", tags=["Auth"])
def change_password(data: ChangePasswordIn,
                    user=Depends(auth_mod.get_user_parolsiz),
                    db: Session = Depends(get_db)):
    if not auth_mod.verify_pw(data.old_password, user.password_hash):
        raise HTTPException(400, "Эски пароль нотўғри")
    yangi = (data.new_password or "").strip()
    # 4 belgi juda kam edi. Bu tizimda pul, qarz va mijoz bazasi turadi —
    # eng kamida 8 belgi va standart paroldan boshqa bo'lsin.
    if len(yangi) < 8:
        raise HTTPException(400, "Пароль камида 8 белгидан иборат бўлсин")
    if yangi.lower() in {"1234", "12345678", "password", "admin", "qwerty",
                         "11111111", "00000000"}:
        raise HTTPException(400, "Бу пароль жуда оддий — бошқасини танланг")
    user.password_hash = auth_mod.hash_pw(yangi)
    user.parol_almashtirilsin = False
    db.commit()
    return {"ok": True}


for r in (clients, orders, warehouse, hr, finance, reports, users,
          constructor, catalog, purchase, kassa, soha, agent):
    app.include_router(r.router)


@app.get("/api/health", tags=["Tizim"])
def health(db: Session = Depends(get_db)):
    """Konteyner va monitoring uchun. Bazaga HAQIQIY so'rov yuboradi.

    Faqat «app javob beryaptimi» ni tekshirish yetarli emas: eng ko'p
    uchraydigan nosozlik — web qismi tirik, lekin baza yiqilgan yoki
    ulanish uzilgan holat. Unda /api/health 200 qaytarsa, monitoring
    hech narsa sezmaydi.
    """
    from sqlalchemy import text as _text
    db.execute(_text("SELECT 1"))
    return {"holat": "ok", "profil": domain.profil().kalit}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Brauzerlar shu manzilni so'raydi — bo'lmasa log 404 bilan to'lib ketadi."""
    from fastapi.responses import Response
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
           '<text y=".9em" font-size="90">📦</text></svg>')
    return Response(svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.get("/robots.txt", include_in_schema=False)
def robots():
    """Ichki korxona tizimi — qidiruv tizimlari indekslamasin (va log 404 to'lmasin)."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("User-agent: *\nDisallow: /\n",
                             headers={"Cache-Control": "public, max-age=86400"})


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mahsulot rasmlari (sexda telefonda olingan) — diskda saqlanadi
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0",
                port=int(os.getenv("PORT", "8000")), reload=False)
