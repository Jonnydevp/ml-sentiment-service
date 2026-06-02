# Оптимизация сборок — кэширование слоёв + uv
FROM python:3.11-slim AS base

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# uv менеджмент зависимостей приложения
RUN pip install uv

WORKDIR /app

# Кэширование слоёв — сначала зависимости, потом код
COPY pyproject.toml .

RUN uv pip install --system --no-cache -r pyproject.toml

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
