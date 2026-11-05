# Catalog importer

## Назначение

`catalog-importer` — отдельный one-shot CLI/job внутри монорепозитория. Он подготавливает локальный индекс YML и обогащает только явно выбранные товары. Importer не имеет HTTP API, портов, фонового daemon-режима и зависимости от backend/frontend.

Целевая структура:

```text
catalog-importer/
├── src/catalog_importer/
├── tests/
├── requirements.txt
└── Dockerfile
```

## Команды

- `index`: потоково читает весь YML и пишет базовые offer в JSONL.
- `search`: локально ищет по offer ID, названию, типу, производителю и vendor code.
- `enrich --offer-id ...`: находит выбранные offer, загружает только соответствующие страницы и формирует нормализованные JSON.
- `prepare-examples`: детерминированно готовит два полных fixtures и один partial fixture.

## Данные

Полный индекс содержит offer ID, название, тип, производителя, vendor code и технический URL, необходимый importer для enrichment. Индекс и сетевой cache являются локальными артефактами, добавляются в `.gitignore` и не выдаются UI/backend.

В коммит попадают только нормализованные fixtures без цены, наличия, изображений, отзывов и URL.

## Ограничения

- Один YML-запрос допустим для полного индекса.
- Массовый обход страниц всех товаров запрещён.
- Enrichment выполняется только для переданных offer ID с ограниченной последовательностью запросов, timeout и понятной ошибкой.
- Произвольный URL из UI/API importer не принимает.
- Ошибка одного выбранного товара отражается в отчёте и не создаёт частично достоверный fixture.

## Интеграция

Importer выдаёт JSON по входному контракту генератора, но не импортирует backend package. Контракт проверяется интеграционным тестом: каждый committed fixture должен успешно валидироваться backend-схемой.

## Выбор других товаров

```powershell
docker compose --profile tools run --rm catalog-importer index --output /data/catalog.jsonl
docker compose --profile tools run --rm catalog-importer search --index /data/catalog.jsonl --query "манометр Testo" --limit 20
docker compose --profile tools run --rm catalog-importer enrich --offer-id 58444 --output-dir /workspace/examples/inputs
```

`search` не обращается к сети. Оператор выбирает `offer_id` из результатов и только затем явно запускает enrichment нужных страниц.

