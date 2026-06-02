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

# torch CPU-only (без CUDA — образ легче и не требует GPU)
RUN uv pip install --system --no-cache torch --index-url https://download.pytorch.org/whl/cpu

# Остальные зависимости
RUN uv pip install --system --no-cache -r pyproject.toml

# Код приложения копируется после установки зависимостей (кэш слоёв)
COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
