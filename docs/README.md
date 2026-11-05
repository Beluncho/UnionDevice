# Карта документации

Статус: **реализация завершена; ожидаются Docker/live smoke в пользовательском окружении**.

Документы описывают поведение и критерии приёмки, а не повторяют будущий код.

| Раздел | Назначение |
|---|---|
| `product/requirements.md` | Пользовательские сценарии и границы MVP |
| `architecture/system.md` | Компоненты, поток данных и зависимости |
| `backend/service.md` | Правила application/backend слоя |
| `catalog-importer/service.md` | Отдельный CLI/job для индекса YML и выбранных товаров |
| `frontend/ui.md` | Состояния формы и результата |
| `api/http-contract.md` | Публичный HTTP-контракт |
| `llm/prompting-and-validation.md` | Prompt, grounding и повторная попытка |
| `data/example-products.md` | Подготовка двух товаров и partial-сценария |
| `operations/local-and-docker.md` | Окружение и контейнерный запуск |
| `quality/test-strategy.md` | Автоматические и ручные проверки |
| `quality/first-live-run.md` | Выводы и изменения после первого реального LLM-запуска |
| `security/secrets.md` | Секреты, логи и недоверенные данные |
| `submission.md` | Короткое сопроводительное сообщение для сдачи |
| `adr/` | Принятые архитектурные решения, включая границу importer/runtime |
| `plan/` | Последовательные этапы реализации |

Фактический статус этапов отражён в `docs/plan/01...06`.

