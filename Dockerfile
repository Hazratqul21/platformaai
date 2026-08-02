FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# KIRILL SHRIFTI — PDF hujjatlar uchun MAJBURIY.
# `python:3.12-slim` da umuman shrift yo'q, shuning uchun reportlab
# Helvetica'ga qaytadi va u kirill harflarini chiza olmaydi: akt va
# nakladnoy kvadratchalar bilan chiqadi. Sinovda fayl 41 KB o'rniga
# 2 KB bo'lib qolgani shundan bilindi.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY tests ./tests

RUN mkdir -p /app/uploads

EXPOSE 8000
CMD ["python", "-m", "app.main"]
