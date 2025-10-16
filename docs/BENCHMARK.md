# Бенчмарк и метрики

## Цели
- Оценить retriever (качество ранжирования).
- Оценить reader (качество ответов).

## Датасеты
Позитивные (100 шт):
{
"question": "Когда было основано ПАО «Транснефть»?",
"ground_truth": "ПАО «Транснефть» было основано 26.08.1993.",
"context": "Дата государственной регистрации ПАО «Транснефть» — 26.08.1993 ...",
"type": "factual",
"difficulty": "base",
"metadata": { "source": "PAO-Transneft-reestr.pdf", "page": 1 }
}

Негативные (20 шт):
{
"question": "Какова средняя зарплата сотрудников Транснефть?",
"expected_answer": "NO_ANSWER",
"type": "unanswerable",
"reason": "Информация отсутствует в предоставленных документах"
}

## Генерация и оценка
- Генерация:
python scripts/create_benchmark.py

- Оценка:
python scripts/run_evaluation.py
- 
Результаты: `benchmarks/*.json`, `results/*.json`.

## Метрики
- Retriever: NDCG@10, MRR@10, MAP@100.
- Reader: BLEURT‑20, SAS (BGE‑m3), RougeL (со стеммингом).

Ориентиры:
- NDCG@10 ≥ 0.85, MRR@10 ≥ 0.80, MAP@100 ≥ 0.75.
- BLEURT ≥ 0.65, SAS ≥ 0.80, RougeL ≥ 0.60.

## Обработка «неответимых» (NO_ANSWER)
- Перед генерацией ответов используется `rag/question_filter.py` для фильтрации out‑of‑scope/unanswerable вопросов. При срабатывании возвращается `NO_ANSWER` вместо галлюцинации.
- Рекомендуется считать precision/recall по классу `NO_ANSWER`.

**Что создаётся:**
- `benchmarks/evaluation_results.json` — детальные результаты для каждого вопроса
- `benchmarks/final_metrics.json` — итоговые метрики QA и ранжирования

**Структура `evaluation_results.json`:**
[
{
"question": "Когда было основано ПАО «Транснефть»?",
"ground_truth": "ПАО «Транснефть» было основано 26.08.1993.",
"generated_answer": "Компания была зарегистрирована 26.08.1993 года.",
"retrieved_docs": ["chunk_12", "chunk_45", "chunk_78"],
"relevant_docs": ["chunk_12", "chunk_45"],
"bleurt_score": 0.85,
"rouge_l_score": 0.72,
"sas_score": 0.88,
"ndcg_at_5": 0.95,
"mrr_at_10": 1.0,
"map_at_100": 0.92
},
...
]

text

**Структура `final_metrics.json`:**
{
"qa_metrics": {
"bleurt": 0.7182,
"rouge_l": 0.4429,
"sas": 0.8256
},
"ranking_metrics": {
"ndcg_at_5": 0.6601,
"mrr_at_10": 0.6333,
"map_at_100": 0.6000
}
}

## Улучшение показателей
- Retriever:
  - Увеличить `TOP_K_RETRIEVER` в `.env`.
  - Подобрать `HYBRID_SEARCH_ALPHA`.
  - Уменьшить размер чанка в `data_processing/chunk_text.py`.
- Reader:
  - Улучшить промпты в `rag/prompts.py`.
  - Увеличить число контекстов в `rag/pipeline.py`.
  - Использовать более сильную LLM (если доступно).