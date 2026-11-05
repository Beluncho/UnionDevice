# Шаг 05: Docker Compose

Статус: completed; backend/frontend health и tools profile проверены через WSL Docker Engine.

## Цель

Сделать проверку результата одной воспроизводимой командой без локальной настройки toolchain.

## Действия

- Создать backend Dockerfile с non-root runtime.
- Создать multi-stage frontend image и nginx proxy.
- Создать отдельный catalog-importer image и one-shot Compose service в профиле `tools`.
- Создать `compose.yaml`, healthchecks и безопасную конфигурацию окружения.
- Проверить build/start с `.env.example` без LLM-вызова.

## Критерии выхода

- UI доступен на `localhost:8080`, API/OpenAPI — на `localhost:8000`.
- `/api/v1/health` не требует ключа.
- Контейнеры становятся healthy.
- `catalog-importer` не стартует при обычном `docker compose up`, не открывает портов и завершается после команды.
- Команды `index`, `enrich` и `prepare-examples` запускаются через Compose profile `tools`.
- В образах и build logs нет секретов.

