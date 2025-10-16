import razdel
import pymorphy2

from sentence_transformers import SentenceTransformer, util
from rouge_score import rouge_scorer
from evaluate import load
from typing import List

# --- Инициализация моделей и метрик ---
print("Инициализация метрик...")
_bleurt = load("bleurt", "BLEURT-20")
_sas_model = SentenceTransformer('BAAI/bge-m3')
# Инициализируем морфологический анализатор для русского языка
print("Метрики инициализированы (pymorphy2 будет инициализирован при первом использовании).")
_morph_instance = None

def get_morph():
    """Ленивая инициализация pymorphy2 с обработкой ошибок."""
    global _morph_instance
    if _morph_instance is None:
        try:
            import inspect
            # Патч для Python 3.11+
            if not hasattr(inspect, 'getargspec'):
                inspect.getargspec = inspect.getfullargspec
            _morph_instance = pymorphy2.MorphAnalyzer()
        except Exception as e:
            print(f"⚠️ pymorphy2 недоступен: {e}. Используется простая токенизация.")
            _morph_instance = None
    return _morph_instance


def stem_text_russian(text: str) -> str:
    """Токенизирует текст и приводит слова к нормальной форме (лемматизация)."""
    tokens = [token.text for token in razdel.tokenize(text.lower())]

    morph = get_morph()
    if morph:
        lemmas = [morph.parse(token)[0].normal_form for token in tokens]
    else:
        # Фоллбэк без морфологии
        lemmas = tokens

    return " ".join(lemmas)


def calculate_bleurt(predictions: List[str], references: List[str]) -> float:
    """Расчет BLEURT."""
    if not predictions or not references: return 0.0
    results = _bleurt.compute(predictions=predictions, references=references)
    return sum(results['scores']) / len(results['scores'])


def initialize_metrics():
    """Инициализация всех метрик (уже происходит при импорте)."""
    print("✅ Метрики инициализированы")


def calculate_all_metrics(references: List[str], predictions: List[str]) -> dict:
    """Расчёт всех метрик генерации."""
    print("Расчет BLEURT...")
    bleurt_score = calculate_bleurt(predictions, references)

    print("Расчет ROUGE-L...")
    rouge_score = calculate_rouge_l_russian(predictions, references)

    print("Расчет Semantic Similarity...")
    sas_score = calculate_sas(predictions, references)

    return {
        "bleurt": round(bleurt_score, 4),
        "rouge_l": round(rouge_score, 4),
        "sas": round(sas_score, 4)
    }


def calculate_rouge_l_russian(predictions: List[str], references: List[str]) -> float:
    if not predictions or not references:
        return 0.0

    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=False)
    total_f_score = 0.0

    for pred, ref in zip(predictions, references):
        pred_lemmatized = stem_text_russian(pred)
        ref_lemmatized = stem_text_russian(ref)

        score = scorer.score(ref_lemmatized, pred_lemmatized)['rougeL'].fmeasure
        total_f_score += score

    return total_f_score / len(predictions)


def calculate_sas(predictions: List[str], references: List[str]) -> float:
    """Расчет Semantic Answer Similarity."""
    if not predictions or not references: return 0.0

    pred_embeddings = _sas_model.encode(predictions, convert_to_tensor=True, normalize_embeddings=True)
    ref_embeddings = _sas_model.encode(references, convert_to_tensor=True, normalize_embeddings=True)

    cosine_scores = util.cos_sim(pred_embeddings, ref_embeddings)
    return cosine_scores.diag().mean().item()