# BI-GPT: Natural Language → SQL Agent

## Deployment: https://bi-gpt-drimtim.vercel.app/

## Описание

### BI-GPT — это AI-агент, который позволяет руководителям и сотрудникам формулировать запросы на естественном языке (русский/английский) и получать готовые BI-метрики напрямую из базы данных.

#### Мультиагент граф:

- преобразует NL-запросы в SQL с учётом бизнес-глоссария и правил,

- валидирует запросы (защита PII, лимиты, запрет SELECT *),

- исполняет их через безопасный SQL-MCP,

- возвращает агрегированные результаты с пояснением,

- умеет «болтать» с пользователем в дружелюбном режиме, если вопрос не про данные.

- умеет рисовать графики на своё усмотрение.

## Возможности

- Поддержка запросов на естественном языке (RU/EN).

- Автоматическая генерация SQL, учитывающая:  разрешённые таблицы и функции, запрещённые поля (PII), join-граф, бизнес-глоссарий (метрики и формулы).

- Валидация SQL через SQLGlot: запрет * и COUNT(*), проверка PII-полей, разрешённые функции, лимиты на строки, cost, bytes scanned.

- SQL-MCP (FastMCP, FastAPI + psycopg) для безопасного исполнения.

- Чат-режим (chitchat) для запросов не требуюших обращения в БД.

- Классификатор запросов (sql_query / other).

- RAG-подобная подгрузка контекста: schema, policies, enums (перечислимые значения).

- Память по сессии, последовательный анализ выгруженных данных.

- Легкая интеграция новых агентов и узлов графовой системы.

- Визуализация данных в виде графиков (pie, hist, line, scatter), понятный API для рисования графиков в UI

## Компоненты:

- sql-mcp: API/MCP: /exec, /explain, /getPolicies, /getMetaInfo.  Policy Manager (YAML): правила, бизнес-глоссарий, формулы

- bi-gpt: LangChain Agent: Мультиагентный граф, MCP инструменты, генерация SQL + ответы пользователю

- dataloader: набор util скриптов для предобработки данных и заполенния БД

- bi-gpt-chat: UI проект, работает с API bi-gpt

## Политики и бизнес-глоссарий

#### Пример policies.yaml:
```yaml
allow_tables: [clients, transactions, transfers]
deny_columns: [iin, phoneNum, client_code, name]
allow_functions: [sum, count, avg, min, max, nullif, coalesce, date_trunc, extract, to_char]
limits:
  max_rows: 50000
  statement_timeout_ms: 30000
glossary:
  "средний баланс":
    metric: avg_balance
    formula: "AVG(avg_monthly_balance_KZT)"
    tables: [clients]
    grain: [status, city, month]
  "общий оборот":
    metric: total_turnover
    formula: "SUM(amount)"
    tables: [transactions, transfers]
    grain: [client_code, date, category, type]
```
