# backend/data_processing/populate_vector_store.py
from .chunk_text import chunk_by_tokens, count_tokens
import uuid


def index_sections_to_chroma(sections, chroma_client, collection_name="transneft_docs"):
    """
    Индексирует секции документов в ChromaDB.

    Args:
        sections: список секций из parse_docx
        chroma_client: клиент ChromaDB
        collection_name: название коллекции
    """
    collection = chroma_client.get_or_create_collection(collection_name)

    docs = []
    metadatas = []
    ids = []

    for sec_idx, sec in enumerate(sections):
        content = sec.get("content", "")

        if not content.strip():
            continue

        # Разбиваем на чанки
        chunks = chunk_by_tokens(content, max_tokens=512, overlap=64)

        for ci, chunk in enumerate(chunks):
            doc_id = f"{sec.get('section_id', uuid.uuid4().hex)}_{ci}"
            token_count = count_tokens(chunk)

            docs.append(chunk)
            metadatas.append({
                "source_file": sec.get("source_file", "unknown.docx"),
                "section_title": sec.get("title", ""),
                "section_id": sec.get("section_id", uuid.uuid4().hex),
                "section_index": sec_idx,
                "chunk_index": ci,
                "token_count": token_count
            })
            ids.append(doc_id)

    # Bulk add to chroma
    if docs:
        collection.add(
            documents=docs,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ Проиндексировано {len(docs)} чанков в ChromaDB")
    else:
        print("⚠️ Нет данных для индексации")

    return len(docs)
