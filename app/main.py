import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

load_dotenv()

from .db import Base, engine, get_db, SessionLocal  # noqa: E402
from . import auth as auth_mod  # noqa: E402
from .migrate import run_migrations, backfill_soha, profillarni_yukla  # noqa: E402
from . import domain  # noqa: E402
from .seed import seed  # noqa: E402
from .bot import start_bot_bg  # noqa: E402
from .routers import (clients, orders, warehouse, hr, finance, reports,  # noqa: E402
                      users, constructor, catalog, purchase, kassa, soha)

logging.basicConfig(level=logging.INFO)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)   # yangi jadvallar
    run_migrations(engine)             # mavjud jadvallarga yangi ustunlar
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

ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"],
                   allow_headers=["*"])


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
def change_password(data: ChangePasswordIn, user=Depends(auth_mod.get_user),
                    db: Session = Depends(get_db)):
    if not auth_mod.verify_pw(data.old_password, user.password_hash):
        raise HTTPException(400, "Eski parol noto'g'ri")
    if len(data.new_password) < 4:
        raise HTTPException(400, "Kamida 4 belgi")
    user.password_hash = auth_mod.hash_pw(data.new_password)
    db.commit()
    return {"ok": True}


for r in (clients, orders, warehouse, hr, finance, reports, users,
          constructor, catalog, purchase, kassa, soha):
    app.include_router(r.router)


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
