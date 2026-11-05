# Архитектура системы

## Компоненты

```text
Browser
  → React UI
  → FastAPI HTTP layer
  → ProductCardService
     ├─ Input completeness analyzer
     ├─ Prompt builder
     ├─ LLMProvider interface
     │  └─ OpenAICompatibleProvider (httpx)
     ├─ Output/grounding validator
     └─ Markdown renderer

Operator / CI
  → catalog-importer CLI (one-shot job)
     ├─ YML indexer → ignored JSONL catalog
     └─ Selected product enricher → committed fixtures
```

`catalog-importer` — отдельный компонент монорепозитория и отдельный Compose service в профиле `tools`. Это не HTTP-сервис и не постоянно работающий процесс. Он не участвует в runtime-потоке UI/backend.

## Поток генерации

1. HTTP-слой нормализует и валидирует вход.
2. Анализатор определяет `missing_fields`; полностью пустой источник фактов отклоняется до LLM.
3. Prompt builder сериализует товар как недоверенный JSON и добавляет требуемую внутреннюю схему ответа.
4. Провайдер выполняет OpenAI-compatible запрос.
5. Валидатор проверяет JSON, размеры полей, количество запросов и происхождение технических литералов.
6. При исправимой ошибке выполняется одна корректирующая попытка.
7. Сервис выбирает характеристики только по ключам из `specs`, подставляет исходные значения и строит Markdown.

## Границы зависимостей

- Доменная/application логика знает интерфейс `LLMProvider`, но не знает `httpx`, FastAPI и переменные окружения.
- HTTP-слой не формирует prompt и не разбирает ответ модели.
- Frontend зависит только от публичного API.
- `catalog-importer` не импортируется backend-приложением и не вызывает его внутренние модули.
- Backend и importer связывает только задокументированный JSON-формат fixtures; интеграционный тест загружает результат importer через публичную Pydantic-схему backend.

## Нефункциональные требования

- Stateless runtime; горизонтальное масштабирование не требует общей БД.
- Ограниченные размеры строк и количества характеристик защищают API и prompt.
- Request ID, длительность и код результата логируются без содержимого карточки и секретов.
- HTML от модели не исполняется; UI отображает текст средствами React.

