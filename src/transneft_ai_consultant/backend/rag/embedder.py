import torch
import time
from sentence_transformers import SentenceTransformer
from typing import List

_model = None

def get_embedder():
    global _model
    if _model is None:
        print("Инициализация эмбеддера BGE-M3...")
        _model = SentenceTransformer('intfloat/multilingual-e5-large-instruct', device='cuda' if torch.cuda.is_available() else 'cpu')
        print("Эмбеддер инициализирован.")
    return _model

def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_embedder()
    print(f"Создание эмбеддингов для {len(texts)} текстов...")
    t0 = time.time()
    embeddings = model.encode(texts, normalize_embeddings=True)
    t1 = time.time()
    print(f"Эмбеддинги созданы за {t1 - t0:.2f} сек.")
    return embeddings.tolist()

# --- Для проверки ---
if __name__ == "__main__":
    test_texts = ["Это тестовое предложение.", "Это еще одно предложение для проверки."]
    embeddings = embed_texts(test_texts)
    print(f"Эмбеддинги созданы. Размерность: {len(embeddings[0])}")



