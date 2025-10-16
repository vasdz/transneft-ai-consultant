import torch
import numpy as np

from typing import List, Tuple
from sentence_transformers import SentenceTransformer, util

_bleurt_model = None


def get_bleurt_model():
    """Загружает BLEURT-20 модель """
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