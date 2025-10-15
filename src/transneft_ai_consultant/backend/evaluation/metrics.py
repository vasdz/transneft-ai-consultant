from sentence_transformers import SentenceTransformer, util
from rouge_score import rouge_scorer
from evaluate import load
from typing import List
import razdel
import pymorphy2

# --- Инициализация моделей и метрик ---
print("Инициализация метрик...")
_bleurt = load("bleurt", "BLEURT-20")
_sas_model = SentenceTransformer('BAAI/bge-m3')
# Инициализируем морфологический анализатор для русского языка
morph = pymorphy2.MorphAnalyzer()
print("Метрики инициализированы.")


def stem_text_russian(text: str) -> str:
    """Токенизирует текст и приводит слова к нормальной форме (лемматизация)."""
    tokens = [token.text for token in razdel.tokenize(text.lower())]
    # ИСПРАВЛЕНО: используем объект morph, а не библиотеку pymorphy2
    lemmas = [morph.parse(token)[0].normal_form for token in tokens]
    return " ".join(lemmas)


def calculate_bleurt(predictions: List[str], references: List[str]) -> float:
    """Расчет BLEURT."""
    if not predictions or not references: return 0.0
    results = _bleurt.compute(predictions=predictions, references=references)
    return sum(results['scores']) / len(results['scores'])


def calculate_rouge_l_russian(predictions: List[str], references: List[str]) -> float:
    """Расчет ROUGE-L с лемматизацией для русского языка."""
    if not predictions or not references: return 0.0

    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=False)
    total_f_score = 0.0

    for pred, ref in zip(predictions, references):
        pred_lemmatized = stem_text_russian(pred)
        ref_lemmatized = stem_text_russian(ref)

        scores = scorer._score_lcs(ref_lemmatized.split(), pred_lemmatized.split())
        total_f_score += scores.fmeasure

    return total_f_score / len(predictions)


def calculate_sas(predictions: List[str], references: List[str]) -> float:
    """Расчет Semantic Answer Similarity."""
    if not predictions or not references: return 0.0

    pred_embeddings = _sas_model.encode(predictions, convert_to_tensor=True, normalize_embeddings=True)
    ref_embeddings = _sas_model.encode(references, convert_to_tensor=True, normalize_embeddings=True)

    cosine_scores = util.cos_sim(pred_embeddings, ref_embeddings)
    return cosine_scores.diag().mean().item()