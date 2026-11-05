# ADR-0002: OpenAI-compatible HTTP adapter

Статус: accepted.

## Контекст

Решение должно работать как с прямым OpenAI API, так и с совместимым gateway вроде proxyapi.ru, а также через исходящий сетевой proxy.

## Решение

Определить внутренний `LLMProvider` и первую реализацию на async `httpx`. Adapter выполняет Bearer-authenticated запрос к `{base_url}/chat/completions`; base URL, model, timeout и proxy задаются окружением.

Не использовать provider-specific SDK и не требовать `response_format`: JSON обеспечивается prompt, parser и валидацией. Конкретная модель не зашивается в код.

## Последствия

- Один прозрачный HTTP-контракт проще диагностировать и проксировать.
- Совместимость ограничена провайдерами с Chat Completions shape.
- Новый нативный провайдер добавляется отдельным adapter без изменения application service.

## Отклонено

- Несколько SDK в MVP: лишние зависимости и ветвление поведения.
- Прямая зависимость service от `httpx`: ухудшает тестируемость.

