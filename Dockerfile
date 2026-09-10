FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production \
    APP_ENV=production \
    DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/lead_intelligence

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
