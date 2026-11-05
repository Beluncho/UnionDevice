# Стратегия тестирования

## Backend

- Полный товар → `draft_ready`, валидные длины и исходные значения характеристик.
- Partial-товар → `needs_clarification`, `description` в missing fields.
- Невалидный LLM-ответ для partial после коррекции → `200`, `draft: null`, без утечки непроверенного текста.
- Нет имени либо одновременно `specs` и `description` → `422` до provider call.
- Неверный JSON модели → одна коррекция; повторная ошибка → `502`.
- Новый технический литерал → grounding failure и коррекция.
- Timeout, 401, 429 и 5xx → стабильные публичные ошибки без upstream body.
- Proxy/base URL корректно передаются HTTP-клиенту.
- Markdown соответствует проверенной публичной модели.

Provider тестируется через `httpx.MockTransport` или эквивалент; настоящая сеть не используется.

## Catalog importer

Минимальные сохранённые XML/HTML samples проверяют потоковый `index`, локальный `search`, выбор offer, извлечение описания/таблицы, очистку разметки и генерацию partial fixture. Тесты не обращаются к внешнему сайту.

Интеграционный тест загружает каждый committed fixture через публичную backend-схему. Отдельно проверяется, что `enrich` требует offer ID и не имеет режима массового обхода страниц.

## Frontend

- Переключение форма/JSON без потери корректного состояния.
- Динамические характеристики и локальная валидация.
- Загрузка всех примеров.
- Отображение `draft_ready`, `needs_clarification` и API-ошибки.
- Копирование JSON/Markdown с mock clipboard.

## Инструменты

- Backend: pytest, pytest-asyncio, coverage, Ruff.
- Frontend: TypeScript, ESLint, Vitest, Testing Library, production build.
- Docker: build, healthcheck и HTTP smoke без LLM-вызова.

## Ручной live smoke

Пользователь запускает контейнеры со своим `.env`, затем Python smoke-клиент отправляет два полных и один partial fixture. Проверяются факты, длины, статусы и отсутствие новых технических значений.

