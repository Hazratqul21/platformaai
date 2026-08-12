FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# KIRILL SHRIFTI — PDF hujjatlar uchun MAJBURIY.
# `python:3.12-slim` da umuman shrift yo'q, shuning uchun reportlab
# Helvetica'ga qaytadi va u kirill harflarini chiza olmaydi: akt va
# nakladnoy kvadratchalar bilan chiqadi. Sinovda fayl 41 KB o'rniga
# 2 KB bo'lib qolgani shundan bilindi.
#
# `curl` — konteyner healthcheck uchun (slim'da yo'q).
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY tests ./tests

# ROOT'SIZ ishlaydi: konteynerda teshik topilsa ham hujumchi darhol
# root bo'lib qolmasin. `uploads` — yagona yoziladigan joy, egasi shu
# foydalanuvchi qilib beriladi.
RUN useradd --system --uid 10001 --create-home tizim \
    && mkdir -p /app/uploads \
    && chown -R tizim:tizim /app/uploads
USER tizim

EXPOSE 8000

# Healthcheck: baza bilan aloqa ham tekshiriladi (oddiy TCP emas) —
# app ko'tarilgan-u, bazaga ulanmayotgan holat eng chalg'ituvchisi.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["python", "-m", "app.main"]
