import chromadb
import hashlib

from typing import List
from src.transneft_ai_consultant.backend.rag.embedder import embed_texts
from tqdm import tqdm
from functools import lru_cache

@lru_cache(maxsize=1000)
def query_documents_cached(question_hash: str, top_k: int):
    """Кэшированная версия поиска."""
    # Восстанавливаем вопрос из хэша невозможно,
    # поэтому лучше использовать другой подход
    pass

# Лучше использовать простой dict-кэш
_query_cache = {}

# Клиент будет сохранять данные в папку db/chroma
client = chromadb.PersistentClient(path="db/chroma")

# Получаем или создаем коллекцию. Имя соответствует вашему плану.
collection = client.get_or_create_collection(
    name="transneft_docs",
    metadata={"hnsw:space": "cosine"}  # Указываем косинусное расстояние
)


def add_documents(chunks: List[dict]):
    """Добавляет документы в ChromaDB батчами."""
    batch_size = 100
    print(f"Добавление {len(chunks)} чанков в ChromaDB...")
    for i in tqdm(range(0, len(chunks), batch_size)):
        batch_chunks = chunks[i:i + batch_size]

        ids = [f"doc_{i + j}" for j in range(len(batch_chunks))]
        contexts = [c["context"] for c in batch_chunks]

        # Создаем эмбеддинги только для текущего батча
        embeddings = embed_texts(contexts)
        metadatas = [c["metadata"] for c in batch_chunks]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contexts,
            metadatas=metadatas
        )
    print("Документы успешно добавлены в векторную базу.")


def query_documents(query: str, top_k=3) -> list:
    """Поиск с кэшированием."""

    cache_key = hashlib.md5(f"{query}_{top_k}".encode()).hexdigest()

    if cache_key in _query_cache:
        print(f"[CACHE HIT] Результат из кэша")
        return _query_cache[cache_key]

    # Оригинальный код поиска...
    query_emb = embed_texts([query])[0]
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k
    )

    output = [
        {"context": doc, "metadata": meta}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]

    _query_cache[cache_key] = output
    return output


def get_collection_size() -> int:
    """Возвращает количество документов в коллекции."""
    return collection.count()

