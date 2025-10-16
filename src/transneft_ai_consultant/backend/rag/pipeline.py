import logging
import json
import hashlib

from .vector_store import query_documents
from .llm import ask_llm
from .prompts import get_rag_prompt
from ..config import TOP_K_RETRIEVER
from sentence_transformers import CrossEncoder
from .hybrid_search import hybrid_search
from .question_filter import is_question_relevant_advanced, get_rejection_message_advanced
from datetime import datetime

_reranker = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_demo.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def get_reranker():
    """Ленивая загрузка reranker модели."""
    global _reranker
    if _reranker is None:
        print("Загрузка reranker модели...")
        _reranker = CrossEncoder('DiTy/cross-encoder-russian-msmarco')
    return _reranker


def rerank_contexts(question: str, contexts: list, top_k: int = 3):
    """Ре-ранжирование контекстов с помощью CrossEncoder."""
    if len(contexts) <= top_k:
        return contexts

    reranker = get_reranker()


    # Формируем пары (вопрос, контекст)
    pairs = [[question, ctx["context"]] for ctx in contexts]

    # Получаем скоры
    scores = reranker.predict(pairs)

    # Сортируем по скору
    for i, ctx in enumerate(contexts):
        ctx["rerank_score"] = float(scores[i])

    contexts.sort(key=lambda x: x["rerank_score"], reverse=True)

    return contexts[:top_k]


def answer_question(question: str) -> tuple[str, list]:
    """
    Генерация ответа на вопрос через RAG с постоянными ID документов.

    Args:
        question: Вопрос пользователя

    Returns:
        Tuple из (ответ, список найденных документов с metadata)
    """
    result = rag_answer(question, use_reranking=True, log_demo=False)

    context_docs = []
    for i, ctx in enumerate(result.get("retrieved_contexts", [])):
        # ✅ Создаём постоянный ID на основе хэша контента
        doc_id = "doc_" + hashlib.md5(ctx.encode('utf-8')).hexdigest()[:8]

        context_docs.append({
            "context": ctx,
            "metadata": {
                "section_id": doc_id,  # ← Постоянный хэш-ID
                "score": result["scores"][i] if i < len(result["scores"]) else 0.0
            }
        })

    return result["answer"], context_docs

def deduplicate_contexts(contexts: list, similarity_threshold: float = 0.6):
    """Удаляет дублирующиеся контексты."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    if len(contexts) <= 1:
        return contexts

    texts = [ctx["context"] for ctx in contexts]

    vectorizer = TfidfVectorizer().fit(texts)
    tfidf_matrix = vectorizer.transform(texts)
    cosine_sim = cosine_similarity(tfidf_matrix)

    # Оставляем только уникальные
    keep = [True] * len(contexts)
    for i in range(len(contexts)):
        if not keep[i]:
            continue
        for j in range(i + 1, len(contexts)):
            if cosine_sim[i, j] > similarity_threshold:
                keep[j] = False

    return [ctx for i, ctx in enumerate(contexts) if keep[i]]


def adaptive_retrieval(question: str) -> int:
    '''Динамически выбирает top_k в зависимости от типа вопроса.'''
    # Для фактических вопросов нужно меньше контекста
    factual_keywords = ['когда', 'где', 'сколько', 'кто', 'дата']
    if any(kw in question.lower() for kw in factual_keywords):
        return 8

    # Для сложных объяснений нужно больше
    explanation_keywords = ['почему', 'как работает', 'объясни', 'опиши']
    if any(kw in question.lower() for kw in explanation_keywords):
        return 12

    return 10  # По умолчанию

def decompose_query(question: str) -> list:
    '''Разбивает сложный вопрос на простые под-вопросы.'''

    decomposition_prompt = f"""Разбей этот сложный вопрос на 2-3 простых под-вопроса, на которые можно ответить независимо.

Вопрос: {question}

Под-вопросы:
1."""

    response = ask_llm(decomposition_prompt, max_tokens=512, temperature=0.1)

    # Парсим под-вопросы
    subquestions = []
    for line in response.split('\n'):
        if line.strip() and any(line.startswith(str(i)) for i in range(1, 10)):
            subq = line.split('.', 1)[1].strip() if '.' in line else line.strip()
            subquestions.append(subq)

    return subquestions if subquestions else [question]

def rag_answer(question: str, use_reranking: bool = True, log_demo: bool = True) -> dict:
    """Улучшенный RAG pipeline с reranking и фильтрацией."""

    # 0. Фильтр релевантности
    is_relevant, details = is_question_relevant_advanced(question, use_semantic=True)
    if not is_relevant:
        rejection_msg = get_rejection_message_advanced(details)
        print(f"⚠️ Вопрос нерелевантен: {details}")
        return {
            "answer": rejection_msg,
            "retrieved_contexts": [],
            "scores": [],
            "confidence": 0.0,
            "is_relevant": False
        }

    if log_demo:
        logger.info(f"{'=' * 80}")
        logger.info(f"НОВЫЙ ЗАПРОС: {question}")
        print(f"\n{'=' * 60}")
        print(f"Вопрос: {question}")
        print(f"{'=' * 60}")

    # 1. Первичный поиск
    if use_reranking:
        initial_top_k = adaptive_retrieval(question)
    else:
        initial_top_k = TOP_K_RETRIEVER

    retrieved_docs = hybrid_search(question, top_k=initial_top_k, alpha=0.5)
    print(f"[1/5] Получено документов из векторной БД: {len(retrieved_docs)}")

    # 2. Фильтрация
    filtered_docs = []
    for doc in retrieved_docs:
        distance = doc.get("distance", 0)
        similarity = 1 - distance
        if similarity >= 0.15:
            doc["similarity"] = similarity
            filtered_docs.append(doc)
    print(f"[2/5] После фильтрации: {len(filtered_docs)} документов")

    # 3. Дедупликация
    unique_docs = deduplicate_contexts(filtered_docs)
    print(f"[3/5] После дедупликации: {len(unique_docs)} уникальных")

    # 4. Reranking
    if use_reranking and len(unique_docs) > TOP_K_RETRIEVER:
        reranked_docs = rerank_contexts(question, unique_docs, top_k=TOP_K_RETRIEVER)
        if reranked_docs:
            best_score = reranked_docs[0].get('rerank_score', 0)
            if best_score < -0.5:
                rejection_msg = get_rejection_message_advanced({
                    "reason": "low_relevance",
                    "severity": "medium"
                })
                print(f"⚠️ Все документы нерелевантны (лучший скор: {best_score:.4f})")
                return {
                    "answer": rejection_msg,
                    "retrieved_contexts": [],
                    "scores": [],
                    "confidence": 0.0,
                    "is_relevant": False
                }
    else:
        reranked_docs = unique_docs[:TOP_K_RETRIEVER]

    print(f"[4/5] После reranking: {len(reranked_docs)} документов")

    # 5. Формирование промпта
    contexts = [d["context"] for d in reranked_docs]
    prompt = get_rag_prompt(contexts, question)
    print(f"[5/5] Промпт сформирован: {len(prompt)} символов")

    # 6. Генерация ответа
    print(f"\nГенерация ответа LLM...")
    answer = ask_llm(prompt, max_tokens=512, temperature=0.3)
    print(f"Ответ получен: {len(answer)} символов")
    print(f"{'=' * 60}\n")

    result = {
        "answer": answer,
        "retrieved_contexts": contexts,
        "scores": [d.get("rerank_score", d.get("similarity", 0)) for d in reranked_docs]
    }

    # Логирование
    if log_demo:
        demo_data = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "retrieved_docs": len(contexts),
            "answer_length": len(answer),
            "contexts_preview": [ctx[:100] + "..." for ctx in contexts]
        }
        logger.info(f"РЕЗУЛЬТАТ: {json.dumps(demo_data, ensure_ascii=False, indent=2)}")

    return result