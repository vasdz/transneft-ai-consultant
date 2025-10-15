from rank_bm25 import BM25Okapi
from typing import List
import numpy as np
from .vector_store import query_documents, collection

# Глобальные переменные для BM25 индекса
_bm25_index = None
_bm25_corpus = None
_doc_ids = None


def build_bm25_index():
    """Строит BM25 индекс из всех документов в ChromaDB."""
    global _bm25_index, _bm25_corpus, _doc_ids

    if _bm25_index is not None:
        print("[BM25] Индекс уже построен")
        return

    print("[BM25] Строим BM25 индекс...")

    # Получаем все документы из коллекции
    all_results = collection.get()

    if not all_results or not all_results.get('documents'):
        print("[BM25] ⚠️ Коллекция пуста")
        return

    documents = all_results['documents']
    _doc_ids = all_results['ids']

    # Токенизация для BM25
    _bm25_corpus = [doc.lower().split() for doc in documents]

    # Создаём BM25 индекс
    _bm25_index = BM25Okapi(_bm25_corpus)

    print(f"[BM25] ✅ Индекс построен для {len(documents)} документов")


def hybrid_search(question: str, top_k: int = 10, alpha: float = 0.7) -> list:
    """
    Комбинирует векторный поиск (Dense) и BM25 (Sparse).

    Args:
        question: Поисковый запрос
        top_k: Количество результатов
        alpha: Вес dense search (0.7 = 70% векторный, 30% BM25)
    """

    # 1. Строим BM25 индекс если нужно
    if _bm25_index is None:
        build_bm25_index()

    if _bm25_index is None:
        print("[HYBRID] BM25 недоступен, используем только векторный поиск")
        return query_documents(question, top_k=top_k)

    # 2. Dense retrieval (векторный поиск)
    dense_results = query_documents(question, top_k=top_k * 2)

    # 3. BM25 sparse retrieval
    tokenized_query = question.lower().split()
    bm25_scores = _bm25_index.get_scores(tokenized_query)

    # 4. Создаём маппинг doc_id -> scores
    dense_score_map = {}
    for doc in dense_results:
        doc_id = doc.get('id') or doc.get('metadata', {}).get('id')
        if doc_id:
            dense_score_map[doc_id] = doc.get('similarity', 0)

    # Нормализуем BM25 scores к [0, 1]
    max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 else 1.0
    min_bm25 = min(bm25_scores) if len(bm25_scores) > 0 else 0.0
    bm25_range = max_bm25 - min_bm25 if max_bm25 > min_bm25 else 1.0

    bm25_score_map = {}
    for i, score in enumerate(bm25_scores):
        if i < len(_doc_ids):
            normalized_score = (score - min_bm25) / bm25_range
            bm25_score_map[_doc_ids[i]] = normalized_score

    # 5. Комбинируем скоры
    combined_scores = {}
    all_doc_ids = set(dense_score_map.keys()) | set(bm25_score_map.keys())

    for doc_id in all_doc_ids:
        dense_score = dense_score_map.get(doc_id, 0.0)
        bm25_score = bm25_score_map.get(doc_id, 0.0)
        combined_scores[doc_id] = alpha * dense_score + (1 - alpha) * bm25_score

    # 6. Сортируем и берём top_k
    sorted_docs = sorted(
        combined_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )[:top_k]

    # 7. Формируем результаты
    result_docs = []
    doc_map = {}
    for doc in dense_results:
        doc_id = doc.get('id') or doc.get('metadata', {}).get('id')
        if doc_id:
            doc_map[doc_id] = doc

    for doc_id, score in sorted_docs:
        if doc_id in doc_map:
            doc = doc_map[doc_id].copy()
            doc['hybrid_score'] = score
            doc['dense_score'] = dense_score_map.get(doc_id, 0.0)
            doc['bm25_score'] = bm25_score_map.get(doc_id, 0.0)
            result_docs.append(doc)
        else:
            # Документ только из BM25
            all_data = collection.get(ids=[doc_id])
            if all_data and all_data['documents']:
                doc = {
                    'id': doc_id,
                    'context': all_data['documents'][0],
                    'metadata': all_data['metadatas'][0] if all_data['metadatas'] else {},
                    'hybrid_score': score,
                    'dense_score': 0.0,
                    'bm25_score': bm25_score_map.get(doc_id, 0.0)
                }
                result_docs.append(doc)

    print(f"[HYBRID] Возвращено {len(result_docs)} документов (alpha={alpha})")
    return result_docs


def init_hybrid_search():
    """Инициализация при старте приложения."""
    build_bm25_index()