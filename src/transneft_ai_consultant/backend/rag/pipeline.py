import logging
import json

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

def deduplicate_contexts(contexts: list, similarity_threshold: float = 0.85):
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


def compress_contexts(question: str, contexts: list, compression_ratio: float = 0.6) -> list:
    '''Сжимает контексты, оставляя только релевантные части.'''

    compressed = []

    for ctx in contexts:
        # Простая эвристика: извлекаем предложения, содержащие ключевые слова из вопроса
        question_keywords = set(question.lower().split())

        sentences = ctx['context'].split('.')
        relevant_sentences = []

        for sent in sentences:
            sent_words = set(sent.lower().split())
            # Если есть пересечение с ключевыми словами вопроса
            if len(question_keywords & sent_words) > 0:
                relevant_sentences.append(sent)

        if relevant_sentences:
            compressed_context = '. '.join(relevant_sentences)
            ctx_copy = ctx.copy()
            ctx_copy['context'] = compressed_context
            ctx_copy['compressed'] = True
            compressed.append(ctx_copy)
        else:
            compressed.append(ctx)  # Если ничего не нашли, оставляем как есть

    return compressed

def adaptive_retrieval(question: str) -> int:
    '''Динамически выбирает top_k в зависимости от типа вопроса.'''
    # Для фактических вопросов нужно меньше контекста
    factual_keywords = ['когда', 'где', 'сколько', 'кто', 'дата']
    if any(kw in question.lower() for kw in factual_keywords):
        return 5

    # Для сложных объяснений нужно больше
    explanation_keywords = ['почему', 'как работает', 'объясни', 'опиши']
    if any(kw in question.lower() for kw in explanation_keywords):
        return 15

    return 10  # По умолчанию


def ensemble_answer(question: str, contexts: list, n_samples: int = 3) -> str:
    '''Генерирует несколько ответов и выбирает наиболее согласованный.'''
    import re

    answers = []
    temperatures = [0.1, 0.3, 0.5]  # Разные температуры для разнообразия

    prompt = get_rag_prompt(contexts, question)

    for temp in temperatures[:n_samples]:
        answer = ask_llm(prompt, max_tokens=512, temperature=temp)
        answers.append(answer)

    # Если ответы очень похожи - берём первый
    if len(set(answers)) == 1:
        return answers[0]

    # Иначе используем voting по ключевым фактам
    # Извлекаем числа, даты, ключевые термины
    def extract_facts(text):
        numbers = re.findall(r'\d+[.,]?\d*', text)
        dates = re.findall(r'\d{4}|\d{2}\.\d{2}\.\d{4}', text)
        return set(numbers + dates)

    # Выбираем ответ с фактами, которые встречаются чаще всего
    fact_votes = {}
    for i, ans in enumerate(answers):
        facts = extract_facts(ans)
        fact_votes[i] = len(facts)

    # Возвращаем самый "фактологичный" ответ
    best_idx = max(fact_votes, key=fact_votes.get)
    return answers[best_idx]


def decompose_query(question: str) -> list:
    '''Разбивает сложный вопрос на простые под-вопросы.'''

    decomposition_prompt = f"""Разбей этот сложный вопрос на 2-3 простых под-вопроса, на которые можно ответить независимо.

Вопрос: {question}

Под-вопросы:
1."""

    response = ask_llm(decomposition_prompt, max_tokens=256, temperature=0.2)

    # Парсим под-вопросы
    subquestions = []
    for line in response.split('\n'):
        if line.strip() and any(line.startswith(str(i)) for i in range(1, 10)):
            subq = line.split('.', 1)[1].strip() if '.' in line else line.strip()
            subquestions.append(subq)

    return subquestions if subquestions else [question]


def multi_hop_rag(question: str) -> str:
    '''RAG с поддержкой multi-hop reasoning.'''

    # 1. Разбиваем на под-вопросы
    subquestions = decompose_query(question)

    # 2. Отвечаем на каждый под-вопрос
    sub_answers = []

    for subq in subquestions:
        contexts = query_documents(subq, top_k=5)
        prompt = get_rag_prompt(contexts, subq)
        answer = ask_llm(prompt, max_tokens=256, temperature=0.3)
        sub_answers.append(answer)

    # 3. Синтезируем финальный ответ
    synthesis_prompt = f"""На основе ответов на под-вопросы дай полный ответ на исходный вопрос.

Исходный вопрос: {question}

Под-ответы:
{chr(10).join(f'{i + 1}. {ans}' for i, ans in enumerate(sub_answers))}

Итоговый ответ:"""

    final = ask_llm(synthesis_prompt, max_tokens=512, temperature=0.3)
    return final


def answer_with_confidence(question: str, contexts: list) -> dict:
    '''Генерирует ответ с оценкой уверенности.'''

    # 1. Генерируем ответ
    prompt = get_rag_prompt(contexts, question)
    answer = ask_llm(prompt, max_tokens=1024, temperature=0.3)

    # 2. Оцениваем уверенность
    confidence_prompt = f"""Оцени, насколько уверенно можно ответить на этот вопрос на основе предоставленных документов.

Вопрос: {question}

Ответ: {answer}

Оценка уверенности (0-10, где 10 - полная уверенность):
Объяснение:"""

    confidence_response = ask_llm(confidence_prompt, max_tokens=128, temperature=0.1)

    # Извлекаем оценку
    import re
    score_match = re.search(r'(\d+)', confidence_response)
    confidence_score = int(score_match.group(1)) if score_match else 5

    # 3. Решаем, отдавать ли ответ
    if confidence_score < 6:
        return {
            'answer': 'К сожалению, в предоставленных документах недостаточно информации для уверенного ответа на этот вопрос.',
            'confidence': confidence_score / 10,
            'original_answer': answer
        }

    return {
        'answer': answer,
        'confidence': confidence_score / 10,
        'explanation': confidence_response
    }

def rag_answer(question: str, use_reranking: bool = True, use_ensemble: bool = False, use_compression: bool = True, log_demo: bool = True) -> dict:
    """Улучшенный RAG pipeline с reranking и фильтрацией."""

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

    # 1. Первичный поиск с большим top_k
    initial_top_k = adaptive_retrieval(question) if use_reranking else TOP_K_RETRIEVER
    retrieved_docs = hybrid_search(question, top_k=initial_top_k, alpha=0.5)

    print(f"[1/5] Получено документов из векторной БД: {len(retrieved_docs)}")

    # 2. Фильтрация по минимальному порогу релевантности
    filtered_docs = []
    for doc in retrieved_docs:
        distance = doc.get("distance", 0)
        similarity = 1 - distance  # косинусное расстояние

        if similarity >= 0.15:  # Минимальный порог
            doc["similarity"] = similarity
            filtered_docs.append(doc)

    print(f"[2/5] После фильтрации: {len(filtered_docs)} документов")

    # 3. Дедупликация
    unique_docs = deduplicate_contexts(filtered_docs)
    print(f"[3/5] После дедупликации: {len(unique_docs)} уникальных")

    # 4. Reranking (если включен)
    if use_reranking and len(unique_docs) > TOP_K_RETRIEVER:
        reranked_docs = rerank_contexts(question, unique_docs, top_k=TOP_K_RETRIEVER)
        if reranked_docs:
            best_score = reranked_docs[0].get('rerank_score', 0)
            if best_score < -0.5:  # Порог 0.5%
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
        print(f"[4/5] Reranking пропущен")

        if use_compression:
            compressed_docs = compress_contexts(question, reranked_docs)
            print(f"[5/7] Compression: {len([d for d in compressed_docs if d.get('compressed')])} документов сжато")
            final_docs = compressed_docs
        else:
            print(f"[5/7] Compression отключено")
            final_docs = reranked_docs

        # 6. Формирование контекстов
        contexts = [d["context"] for d in final_docs]
        prompt = get_rag_prompt(contexts, question)

        # 7. НОВОЕ: Генерация ответа (с Ensemble если включено)
        if use_ensemble:
            print("      Используем Self-Consistency Ensemble (3 ответа)...")
            answer = ensemble_answer(question, contexts, n_samples=3)
        else:
            answer = ask_llm(prompt, max_tokens=512, temperature=0.3)

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

    # Логирование для демонстрации
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
