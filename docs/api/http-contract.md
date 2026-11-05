# HTTP API contract

Префикс API: `/api/v1`. Content type: `application/json; charset=utf-8`.

## POST `/product-cards/generate`

Запрос:

```json
{
  "name": "testo 510",
  "manufacturer": "Testo",
  "specs": {
    "Диапазон измерений": "0 ... 100 гПа",
    "Класс защиты": "IP40"
  },
  "description": "Прибор предназначен для измерения..."
}
```

Ограничения: имя до 200 символов, описание до 20 000 символов, до 100 характеристик; ключ и значение характеристики — до 500 символов.

Успешный ответ `200`:

```json
{
  "status": "draft_ready",
  "draft": {
    "seo_title": "...",
    "seo_description": "...",
    "key_characteristics": [
      {"name": "Диапазон измерений", "value": "0 ... 100 гПа"}
    ],
    "search_queries": ["...", "...", "..."],
    "commercial_block": "...",
    "markdown": "..."
  },
  "missing_fields": [],
  "warnings": [],
  "quality": {"grounded": true, "retry_count": 0},
  "request_id": "uuid"
}
```

`status` принимает только `draft_ready` или `needs_clarification`. `key_characteristics[].value` равен исходному значению из `specs`.

Для неполного товара, по которому LLM не смогла сформировать проверенный ответ после коррекции, `status` равен `needs_clarification`, а `draft` равен `null`. Ответ остаётся `200`, содержит `missing_fields`, предупреждения и `quality.grounded=false`. Непроверенный LLM-текст не возвращается.

## GET `/examples`

Возвращает список трёх демонстрационных payload: два полных товара и partial-вариант. URL источников в ответ не входят.

## GET `/health`

Возвращает `200 {"status":"ok"}` без проверки LLM и без расходования токенов.

## Ошибки

```json
{
  "error": {
    "code": "insufficient_product_data",
    "message": "Недостаточно данных для генерации черновика",
    "details": {"missing_fields": ["specs", "description"]},
    "request_id": "uuid"
  }
}
```

- `422 validation_error` — неверные типы, пределы или JSON.
- `422 insufficient_product_data` — нет имени или источника фактов.
- `502 provider_error` — upstream отклонил запрос либо вернул невалидный ответ после коррекции.
- `504 provider_timeout` — исчерпан таймаут.

Текст upstream-ответа, prompt и секреты наружу не возвращаются.

