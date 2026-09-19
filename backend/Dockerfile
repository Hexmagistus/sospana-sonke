FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 8000 is the default; most hosts (Koyeb, Render, etc.) inject a real PORT env
# var at runtime and this respects it, falling back to 8000 for local/docker-compose
# use where no PORT is set (EXPOSE below is documentation only, not enforced).
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
