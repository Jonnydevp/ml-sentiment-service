# Sentiment Analysis ML Service

ML-сервис для анализа тональности текста (POSITIVE / NEGATIVE) на основе модели
DistilBERT (`distilbert-base-uncased-finetuned-sst-2-english`, HuggingFace)

Проект демонстрирует продакшн-архитектуру ML-сервиса: асинхронный API, очередь
задач, реверс-прокси, БД с миграциями, мониторинг здоровья и отказоустойчивость -
все в Docker Compose, запуск одной командой.

## Архитектура

```
Пользователь → Nginx (:80)  — единая точка входа, rate limiting
                 ├── /          → Streamlit (:8501)   — веб-интерфейс
                 └── /api/*      → FastAPI (:8000)     — REST API
                                     ├── PostgreSQL    — хранение результатов (ORM + Alembic)
                                     ├── Redis         — брокер очереди + backend результатов
                                     └── Celery Worker — асинхронный ML-инференс
```

**Сервисы:**
- **Nginx** — reverse proxy, маршрутизация `/api/*` → backend, `/` → UI, rate limiting (5 req/min).
- **FastAPI** — REST API, валидация Pydantic, ORM SQLAlchemy 2.0 (async), lifespan-загрузка модели.
- **Celery Worker** — обработка тяжёлых задач в отдельном процессе с моделью.
- **Streamlit** — интерфейс: анализ, история, дашборд с графиками (Plotly).
- **PostgreSQL** — хранение результатов анализа.
- **Redis** — брокер сообщений Celery и backend результатов.

**Сети (изоляция):**
- `frontend_net` — Nginx ↔ Streamlit ↔ FastAPI.
- `backend_net` — FastAPI ↔ Redis ↔ PostgreSQL ↔ Worker.
- UI и Nginx **не имеют** доступа к Redis/PostgreSQL.

## Запуск

```bash
# 1. Создать .env из примера
cp .env.example .env

# 2. Поднять все сервисы одной командой
docker compose up --build -d

# 3. Открыть в браузере
#   UI:      http://localhost
#   Swagger: http://localhost/api/docs
#   Health:  http://localhost/api/health
```

> **Первый запуск:** при старте backend и worker один раз скачивают веса модели
> DistilBERT (~270 МБ) с HuggingFace. Нужен доступ в интернет. Веса кэшируются в
> Docker volume `model_cache`, поэтому при последующих запусках сеть не требуется.
> Пока модель грузится, `/api/health` возвращает `503` — это нормально (~30–60 сек).

## API Эндпоинты

### Синхронный анализ
```bash
curl -X POST http://localhost/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this product!", "confidence_threshold": 0.5}'
```

### Асинхронный анализ (Celery)
```bash
# Поставить задачу в очередь → вернётся task_id (HTTP 202)
curl -X POST http://localhost/api/analyze/async \
  -H "Content-Type: application/json" \
  -d '{"text": "This is terrible!"}'

# Проверить статус задачи (polling)
curl http://localhost/api/task/<task_id>
```

### Батч-анализ
```bash
curl -X POST http://localhost/api/analyze/batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Great!", "Awful!", "It is okay"]}'
```

### История и статистика
```bash
curl "http://localhost/api/history?page=1&per_page=20"
curl http://localhost/api/stats
```

### Health Check
```bash
curl http://localhost/api/health
# {"status":"healthy","db":"ok","redis":"ok","model":"ok"}
```

## Технологический стек

| Компонент | Технология |
|-----------|-----------|
| Backend API | FastAPI, Pydantic, uvicorn |
| ML-модель | HuggingFace transformers, PyTorch (CPU) |
| ORM | SQLAlchemy 2.0 (async, asyncpg) |
| Миграции | Alembic |
| Очередь задач | Celery + Redis |
| Frontend | Streamlit, Plotly |
| Reverse Proxy | Nginx |
| БД | PostgreSQL 16 |
| Кэш / Брокер | Redis 7 |
| Контейнеризация | Docker, Docker Compose |
| Менеджер зависимостей | uv |

## Соответствие критериям оценивания

Каждый пункт помечен в коде комментарием (`# Логирование`, `# Валидация данных` и т.д.).

| Тема | Реализация | Где смотреть |
|------|-----------|--------------|
| 1. API Backend | lifespan, Pydantic, обработка ошибок, Celery | `app/main.py`, `app/schemas.py`, `app/errors.py`, `app/routers/analysis.py` |
| 2. ML Service | изоляция класса, батчинг, `max_length`, логирование | `app/services/ml_service.py` |
| 3. Frontend | 3 страницы, 3+ эндпоинта, спиннеры, обработка сбоев | `frontend/app/pages/` |
| 4. Reverse Proxy | единая точка входа, маршрутизация, rate limiting | `nginx/nginx.conf` |
| 5. Данные/Alembic | ORM без сырого SQL, миграции | `app/models.py`, `app/database.py`, `alembic/` |
| 6. Docker Compose | uv, кэш слоёв, сети, volumes, depends_on | `docker-compose.yml`, `*/Dockerfile` |
| 7. High Availability | stateless, graceful shutdown | `app/main.py`, `docker-compose.yml` |
| 8. Health Checks | `/api/health`, compose healthcheck, `service_healthy` | `app/routers/health.py`, `docker-compose.yml` |

## Структура проекта

```
ml-sentiment-service/
├── docker-compose.yml          # Оркестрация: сети, volumes, healthchecks
├── .env.example                # Шаблон переменных окружения
├── nginx/nginx.conf            # Reverse proxy + rate limiting
├── backend/
│   ├── Dockerfile              # uv + кэш слоёв + torch CPU
│   ├── pyproject.toml
│   ├── entrypoint.sh           # Миграции → запуск uvicorn
│   ├── alembic/                # Миграции БД
│   └── app/
│       ├── main.py             # FastAPI + lifespan
│       ├── config.py           # Настройки из окружения
│       ├── database.py         # Async SQLAlchemy
│       ├── models.py           # ORM-модели
│       ├── schemas.py          # Pydantic Request/Response
│       ├── errors.py           # Кастомные обработчики ошибок
│       ├── routers/            # analyze / history / health
│       ├── services/           # Изолированная ML-логика
│       └── workers/            # Celery: app + tasks
└── frontend/
    ├── Dockerfile
    ├── pyproject.toml
    └── app/
        ├── app.py              # Навигация
        └── pages/              # Анализ / История / Дашборд
```
