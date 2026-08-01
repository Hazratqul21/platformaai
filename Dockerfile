FROM python:3.12-slim

# psycopg[binary] uchun tizim kutubxonasi shart emas, lekin reportlab/openpyxl
# uchun kerak bo'lishi mumkin — minimal to'plam
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY tests ./tests

RUN mkdir -p /app/uploads

EXPOSE 8000
CMD ["python", "-m", "app.main"]
