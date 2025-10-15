import json
import sys
import os

from pathlib import Path
from tqdm import tqdm

project_root = str(Path(__file__).parent.parent.absolute())
sys.path.append(project_root)

from src.transneft_ai_consultant.backend.rag.pipeline import rag_answer
from src.transneft_ai_consultant.backend.evaluation.metrics import calculate_bleurt, calculate_sas
from src.transneft_ai_consultant.backend.evaluation.rouge_ru import calculate_rouge_ru
from src.transneft_ai_consultant.backend.evaluation.metrics_ranking import (
    ndcg_mean_at_k, mrr_at_k, map_at_k
)
from src.transneft_ai_consultant.backend.rag.vector_store import query_documents
from src.transneft_ai_consultant.backend.evaluation.metrics_advanced import (
    calculate_bleurt_score,
    calculate_semantic_answer_similarity
)


BENCHMARK_FILE_PATH = os.path.join(project_root, "benchmark.json")
EVALUATION_RESULTS_FILE_PATH = os.path.join(project_root, "evaluation_results.json")


def evaluate_retriever(benchmark_data):


    """Оценка качества ретривера."""
    qid_to_truth = {}
    qid_to_retrieved = {}

    for i, item in enumerate(tqdm(benchmark_data, desc="Оценка ретривера")):
        qid = f"q{i}"
        question = item["question"]
        true_context = item["context"]

        # Получаем top-100 для MAP@100
        retrieved = query_documents(question, top_k=100)
        retrieved_ids = [doc.get("metadata", {}).get("section_id", f"doc_{j}")
                         for j, doc in enumerate(retrieved)]

        # Поиск истинного ID
        true_id = None
        for doc in retrieved:
            # Проверяем совпадение по тексту
            if true_context.strip() in doc["context"] or doc["context"].strip() in true_context:
                true_id = doc.get("metadata", {}).get("section_id")
                break

        if true_id:
            qid_to_truth[qid] = {true_id}
            qid_to_retrieved[qid] = retrieved_ids

    # Рассчитываем метрики только если есть данные
    if qid_to_truth and qid_to_retrieved:
        ndcg_10 = ndcg_mean_at_k(qid_to_truth, qid_to_retrieved, k=10)
        mrr_10 = mrr_at_k(qid_to_truth, qid_to_retrieved, k=10)
        map_100 = map_at_k(qid_to_truth, qid_to_retrieved, k=100)

        print("\n" + "=" * 50)
        print("--- Метрики ретривера ---")
        print(f"NDCG@10:  {ndcg_10:.4f}")
        print(f"MRR@10:   {mrr_10:.4f}")
        print(f"MAP@100:  {map_100:.4f}")
        print("=" * 50 + "\n")

        return {
            "ndcg@10": ndcg_10,
            "mrr@10": mrr_10,
            "map@100": map_100
        }
    else:
        print("\n⚠️ Не удалось найти соответствия для метрик ретривера")
        return {
            "ndcg@10": 0.0,
            "mrr@10": 0.0,
            "map@100": 0.0
        }


def main():
    # Загружаем бенчмарк
    try:
        with open(BENCHMARK_FILE_PATH, 'r', encoding='utf-8') as f:
            benchmark_file = json.load(f)

        # ИСПРАВЛЕНО: правильная структура бенчмарка
        if isinstance(benchmark_file, dict) and "benchmark" in benchmark_file:
            benchmark = benchmark_file["benchmark"]
            print(f"📊 Метаданные бенчмарка: {benchmark_file.get('metadata', {})}")
        else:
            benchmark = benchmark_file

    except FileNotFoundError:
        print(f"❌ Ошибка: Файл бенчмарка {BENCHMARK_FILE_PATH} не найден.")
        print("Сначала запустите: python scripts/create_benchmark.py")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка декодирования JSON: {e}")
        return

    print(f"✅ Загружено {len(benchmark)} вопросов из бенчмарка.\n")

    # Оценка ретривера
    print("=" * 50)
    print("ЭТАП 1: Оценка качества ретривера")
    print("=" * 50)
    retriever_metrics = evaluate_retriever(benchmark)

    # Оценка QA системы
    print("\n" + "=" * 50)
    print("ЭТАП 2: Оценка QA системы")
    print("=" * 50)

    evaluation_results = []

    for item in tqdm(benchmark, desc="Генерация ответов"):
        question = item["question"]
        ground_truth_answer = item["ground_truth"]

        try:
            rag_result = rag_answer(question, use_reranking=True, use_ensemble=True, use_compression=True, log_demo=False)
            generated_answer = rag_result["answer"]
            retrieved_contexts = rag_result["retrieved_contexts"]
        except Exception as e:
            print(f"\n⚠️ Ошибка при обработке вопроса: {question[:50]}...")
            print(f"   Причина: {e}")
            generated_answer = ""
            retrieved_contexts = []

        evaluation_results.append({
            "question": question,
            "ground_truth_answer": ground_truth_answer,
            "generated_answer": generated_answer,
            "retrieved_contexts": retrieved_contexts
        })

    # Сохраняем результаты
    with open(EVALUATION_RESULTS_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(evaluation_results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Результаты сохранены в {EVALUATION_RESULTS_FILE_PATH}")

    # Расчет метрик QA
    print("\n" + "=" * 50)
    print("ЭТАП 3: Расчет метрик качества")
    print("=" * 50)

    ground_truths = [res["ground_truth_answer"] for res in evaluation_results]
    generated_answers = [res["generated_answer"] for res in evaluation_results]

    print("Расчет BLEURT-20...")
    bleurt_score = calculate_bleurt(predictions=generated_answers, references=ground_truths)

    print("Расчет ROUGE-L для русского языка...")
    rouge_scores = calculate_rouge_ru(predictions=generated_answers, references=ground_truths)
    rouge_l_score = rouge_scores["rougeL"].fmeasure

    print("Расчет Semantic Answer Similarity...")
    sas_score = calculate_sas(predictions=generated_answers, references=ground_truths)

    # НОВОЕ: Расчет продвинутых метрик
    print("\nРасчет BLEURT-20 (BERTScore)...")
    bleurt_20_score = calculate_bleurt_score(predictions=generated_answers, references=ground_truths)

    print("Расчет Semantic Answer Similarity (BGE-M3)...")
    sas_bge_m3 = calculate_semantic_answer_similarity(predictions=generated_answers, references=ground_truths)

    # Итоговый отчет
    print("\n" + "=" * 70)
    print("📊 ИТОГОВЫЕ МЕТРИКИ")
    print("=" * 70)
    print("\n🔍 Метрики ретривера:")
    print(f"   NDCG@10:  {retriever_metrics['ndcg@10']:.4f}")
    print(f"   MRR@10:   {retriever_metrics['mrr@10']:.4f}")
    print(f"   MAP@100:  {retriever_metrics['map@100']:.4f}")
    print("\n💬 Метрики QA системы:")
    print(f"   BLEURT (старая версия): {bleurt_score:.4f}")
    print(f"   BLEURT-20 (BERTScore): {bleurt_20_score:.4f}")
    print(f"   ROUGE-L (F-score): {rouge_l_score:.4f}")
    print(f"   Semantic Similarity (старая): {sas_score:.4f}")
    print(f"   Semantic Answer Similarity (BGE-M3): {sas_bge_m3['average']:.4f}")
    print("=" * 70 + "\n")

    # Сохраняем финальные метрики
    final_metrics = {
        "retriever": retriever_metrics,
        "qa_system": {
            "bleurt_old": bleurt_score,
            "bleurt_20": bleurt_20_score,
            "rouge_l_fscore": rouge_l_score,
            "semantic_similarity_old": sas_score,
            "semantic_answer_similarity_bge_m3": sas_bge_m3['average']
        },
        "benchmark_size": len(benchmark),
        "timestamp": datetime.now().isoformat()
    }

    metrics_file = os.path.join(project_root, "final_metrics.json")
    with open(metrics_file, 'w', encoding='utf-8') as f:
        json.dump(final_metrics, f, ensure_ascii=False, indent=2)

    print(f"📁 Финальные метрики сохранены в {metrics_file}")

    def evaluate_hallucination_resistance(benchmark_data):
        '''Проверяет, говорит ли система "не знаю" на вопросы без ответа.'''

        negative_samples = [item for item in benchmark_data if item.get('type') == 'unanswerable']

        correct_rejections = 0
        for item in negative_samples:
            answer = rag_answer(item['question'])

            refusal_phrases = [
                'недостаточно информации',
                'нет данных',
                'не могу ответить',
                'информации об этом нет'
            ]

            if any(phrase in answer.lower() for phrase in refusal_phrases):
                correct_rejections += 1

        hallucination_resistance = correct_rejections / len(negative_samples) if negative_samples else 0
        return hallucination_resistance



if __name__ == "__main__":
    from datetime import datetime

    main()
