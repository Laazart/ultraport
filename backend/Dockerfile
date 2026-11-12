FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ultraport/ .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py poblar_usuarios && gunicorn ultraport.wsgi:application --bind 0.0.0.0:8000 --workers 2"]