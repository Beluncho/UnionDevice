# Локальный запуск и Docker

## Локальная разработка

- Python 3.12, виртуальное окружение `.venv`.
- Node.js 22 и npm lockfile.
- Backend: FastAPI/Uvicorn на `localhost:8000`.
- Frontend dev server: `localhost:5173` с proxy `/api` на backend.

Корневой `requirements.txt` агрегирует runtime-зависимости backend и catalog-importer для общей локальной `.venv`. Каждый Python-компонент также имеет собственный `requirements.txt` для изолированной сборки контейнера. `requirements-dev.txt` добавляет pytest/Ruff/test tooling. Пакеты глобально не устанавливаются.

## Конфигурация

Backend читает:

- `APP_ENV`, `LOG_LEVEL`;
- `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`;
- необязательный `LLM_HTTP_PROXY_URL`;
- `LLM_TIMEOUT_SECONDS`, `CORS_ORIGINS`.

`LLM_BASE_URL` включает API-префикс, например `/v1`; adapter добавляет `/chat/completions`. URL с embedded credentials отклоняются. Proxy URL не логируется.

## Docker Compose

- `backend`: Python slim image, non-root user, порт `8000`, healthcheck `/api/v1/health`.
- `frontend`: multi-stage Node build и nginx, порт `8080`, `/api` проксируется в backend.
- `catalog-importer`: отдельный one-shot image без портов и healthcheck; доступен только через Compose profile `tools`, `restart: "no"`.
- БД, Redis и persistent volumes отсутствуют.

Host-порты задаются `BACKEND_PORT` и `FRONTEND_PORT`; defaults — `8000` и `8080`.

Для agent-run проверок используется только `.env.example` или отдельное тестовое окружение с фиктивным ключом. Реальный `docker compose up` с `.env` запускает пользователь.

Примеры запуска importer:

```powershell
docker compose --profile tools run --rm catalog-importer index --output /data/catalog.jsonl
docker compose --profile tools run --rm catalog-importer search --index /data/catalog.jsonl --query "манометр" --limit 20
docker compose --profile tools run --rm catalog-importer enrich --offer-id 58444 --offer-id 64423 --output-dir /workspace/examples/inputs
docker compose --profile tools run --rm catalog-importer prepare-examples
```

Если в Windows установлен standalone Compose без v2 plugin, в этих командах используется эквивалентная форма `docker-compose`.

Для importer монтируются только каталоги локального индекса/cache и `examples/inputs`. Backend container эти каталоги не изменяет.

При запуске Windows Compose через TCP/socat к WSL Docker Engine задайте `HOST_PROJECT_PATH=/mnt/c/.../UnionDevice`, чтобы Linux daemon получил корректный bind path. При обычном запуске из WSL или Docker Desktop используется default `.`.

## Политика логов

- Успешные health-check не пишутся в application log.
- Uvicorn access-log отключён, чтобы не дублировать application middleware.
- Nginx не логирует UI/static assets и `/healthz`.
- API-запросы nginx сохраняются в коротком формате: метод, путь, status, bytes и duration; Referrer/User-Agent исключены.
- Backend пишет request ID, status, duration и безопасный error code без prompt, входного описания и upstream body.

## Готовность

- Backend health не вызывает LLM.
- UI открывается без ключа; генерация возвращает контролируемую ошибку конфигурации/провайдера.
- Остановка контейнеров не уничтожает пользовательские данные, потому что runtime ничего не хранит.

