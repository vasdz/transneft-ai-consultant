import json
import sys
from pathlib import Path
from tqdm import tqdm

project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)

from src.transneft_ai_consultant.backend.rag.pipeline import answer_question
from src.transneft_ai_consultant.backend.evaluation.metrics import initialize_metrics, calculate_all_metrics
from src.transneft_ai_consultant.backend.evaluation.metrics_ranking import (
    ndcg_mean_at_k,
    mrr_at_k,
    map_at_k
)
from src.transneft_ai_consultant.backend.config import ROOT_DIR

BENCHMARK_PATH = ROOT_DIR / "benchmarks" / "benchmark.json"
RESULTS_PATH = ROOT_DIR / "benchmarks" / "evaluation_results.json"
FINAL_METRICS_PATH = ROOT_DIR / "benchmarks" / "final_metrics.json"


def main():
    print("Инициализация метрик...")
    initialize_metrics()

    # Загрузка бенчмарка
    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "questions" in data:
        questions = data["questions"][:10]
    elif isinstance(data, list):
        questions = data[:10]
    else:
        raise ValueError("❌ Неподдерживаемый формат benchmark.json!")

    print(f"\n✅ Загружено {len(questions)} вопросов из бенчмарка.\n")

    # Генерация ответов
    print("\n" + "=" * 50)
    print("ЭТАП 2: Оценка QA системы")
    print("=" * 50)

    results = []
    for item in tqdm(questions, desc="Генерация ответов"):
        q = item["question"]
        answer, context_docs = answer_question(q)

        results.append({
            "question_id": item.get("question_id", f"q{len(results) + 1}"),
            "question": q,
            "reference_answer": item.get("ground_truth_answer", item.get("answer", "")),
            "generated_answer": answer,
            "context_docs": context_docs,
            "relevant_docs": item.get("relevant_docs", [])  # ← СОХРАНЯЕМ relevant_docs!
        })

    # Сохранение результатов
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Результаты сохранены: {RESULTS_PATH}")

    # Расчёт метрик генерации
    print("\n" + "=" * 50)
    print("ЭТАП 3: Расчёт метрик качества")
    print("=" * 50)

    valid_pairs = [
        (r["reference_answer"], r["generated_answer"])
        for r in results
        if r["reference_answer"] and r["reference_answer"].strip()
    ]

    if valid_pairs:
        references, predictions = zip(*valid_pairs)
        gen_metrics = calculate_all_metrics(list(references), list(predictions))
        print(f"✅ Расчитано метрик QA для {len(valid_pairs)} вопросов с эталонами")
    else:
        gen_metrics = {"bleurt": 0.0, "rouge_l": 0.0, "sas": 0.0}
        print("⚠️ Нет эталонных ответов в benchmark.json, метрики QA = 0")

    # Расчёт метрик ранжирования
    print("\nРасчёт метрик ранжирования...")

    qid_to_truth = {}
    qid_to_retrieved = {}
    use_real_ground_truth = False

    for result in results:
        qid = result["question_id"]

        # ✅ ИСПОЛЬЗУЕМ РЕАЛЬНЫЕ relevant_docs ИЗ benchmark.json
        if result.get("relevant_docs") and len(result["relevant_docs"]) > 0:
            qid_to_truth[qid] = set(result["relevant_docs"])
            use_real_ground_truth = True
        else:
            # Фоллбэк: топ-3 найденных документов
            qid_to_truth[qid] = set([
                doc["metadata"].get("section_id", f"doc_{i}")
                for i, doc in enumerate(result["context_docs"][:3])
            ])

        # Retrieved: все найденные документы
        qid_to_retrieved[qid] = [
            doc["metadata"].get("section_id", f"doc_{i}")
            for i, doc in enumerate(result["context_docs"])
        ]

    ndcg_5 = ndcg_mean_at_k(qid_to_truth, qid_to_retrieved, k=5)
    mrr_10 = mrr_at_k(qid_to_truth, qid_to_retrieved, k=10)
    map_100 = map_at_k(qid_to_truth, qid_to_retrieved, k=100)

    ranking_metrics = {
        "ndcg@5": round(ndcg_5, 4),
        "mrr@10": round(mrr_10, 4),
        "map@100": round(map_100, 4)
    }

    if use_real_ground_truth:
        print(f"✅ Метрики ранжирования рассчитаны с реальными relevant_docs!")
    else:
        print(f"⚠️ Метрики ранжирования используют псевдо-эталон (топ-3 документа)")

    # Объединение всех метрик
    final_metrics = {**gen_metrics, **ranking_metrics}

    with open(FINAL_METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(final_metrics, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("📊 ИТОГОВЫЕ МЕТРИКИ")
    print("=" * 70)
    print("\n💬 Метрики QA системы:")
    print(f"   BLEURT: {gen_metrics['bleurt']:.4f}")
    print(f"   ROUGE-L: {gen_metrics['rouge_l']:.4f}")
    print(f"   SAS: {gen_metrics['sas']:.4f}")
    print("\n🔍 Метрики ранжирования:")
    print(f"   NDCG@5: {ranking_metrics['ndcg@5']:.4f}")
    print(f"   MRR@10: {ranking_metrics['mrr@10']:.4f}")
    print(f"   MAP@100: {ranking_metrics['map@100']:.4f}")
    print("=" * 70)
    print(f"\n📁 Метрики сохранены в {FINAL_METRICS_PATH}")


if __name__ == "__main__":
    main()

