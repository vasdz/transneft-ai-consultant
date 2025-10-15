import torch
import numpy as np

from typing import List, Tuple
from sentence_transformers import SentenceTransformer, util

_bleurt_model = None


def get_bleurt_model():
    """Загружает BLEURT-20 модель (или альтернативу)"""
    global _bleurt_model
    if _bleurt_model is None:
        try:
            print("Загрузка BLEURT-подобной модели (BERTScore)...")
            from bert_score import BERTScorer
            _bleurt_model = BERTScorer(
                model_type="DeepPavlov/rubert-base-cased",
                lang="ru",
                rescale_with_baseline=True
            )
            print("✅ BLEURT-подобная модель загружена")
        except Exception as e:
            print(f"⚠️ Не удалось загрузить BLEURT: {e}")
            _bleurt_model = None
    return _bleurt_model


def calculate_bleurt_score(predictions: List[str], references: List[str]) -> float:
    """Вычисляет BLEURT-20 score (или BERTScore как альтернативу)"""
    model = get_bleurt_model()

    if model is None:
        print("⚠️ BLEURT недоступен, возвращаем 0")
        return 0.0

    try:
        # BERTScore возвращает precision, recall, F1
        P, R, F1 = model.score(predictions, references)
        return float(F1.mean())
    except Exception as e:
        print(f"⚠️ Ошибка при расчете BLEURT: {e}")
        return 0.0

_bge_model = None


def get_bge_model():
    """Загружает BGE-M3 модель для semantic similarity"""
    global _bge_model
    if _bge_model is None:
        print("Загрузка BGE-M3 модели для SemanticAnswerSimilarity...")
        _bge_model = SentenceTransformer(
            'BAAI/bge-m3',
            device='cuda' if torch.cuda.is_available() else 'cpu'
        )
        print("✅ BGE-M3 модель загружена")
    return _bge_model


def calculate_semantic_similarity(
        predictions: List[str],
        references: List[str]
) -> Tuple[float, List[float]]:
    """Вычисляет семантическую схожесть используя BGE-M3"""
    model = get_bge_model()

    pred_embeddings = model.encode(
        predictions,
        normalize_embeddings=True,
        show_progress_bar=False
    )
    ref_embeddings = model.encode(
        references,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    similarities = []
    for pred_emb, ref_emb in zip(pred_embeddings, ref_embeddings):
        sim = util.cos_sim(pred_emb, ref_emb).item()
        similarities.append(sim)

    return float(np.mean(similarities)), similarities


def calculate_semantic_answer_similarity(
        predictions: List[str],
        references: List[str]
) -> dict:
    """Полная метрика SemanticAnswerSimilarity"""
    avg_sim, similarities = calculate_semantic_similarity(predictions, references)

    return {
        'average': avg_sim,
        'min': float(np.min(similarities)),
        'max': float(np.max(similarities)),
        'std': float(np.std(similarities)),
        'scores': similarities
    }
