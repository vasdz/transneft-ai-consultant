import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)

from src.transneft_ai_consultant.backend.data_processing.parse_docx import read_docx_sections
from src.transneft_ai_consultant.backend.data_processing.chunk_text import chunk_sections
from src.transneft_ai_consultant.backend.rag.vector_store import add_documents, get_collection_size
from src.transneft_ai_consultant.backend.config import DOCX_PATH

def main():
    print("Запуск процесса индексации документов...")

    # Шаг 1: Парсинг документа
    print(f"1/3: Парсинг {DOCX_PATH}...")
    sections = read_docx_sections(str(DOCX_PATH))
    if not sections:
        print("Ошибка: не удалось извлечь секции.")
        return
    print(f"Найдено {len(sections)} секций.")

    # Шаг 2: Разбивка на чанки
    print("2/3: Разбивка текста на чанки...")
    chunks = chunk_sections(sections, strategy="smart")
    print(f"Создано {len(chunks)} чанков.")

    # Шаг 3: Добавление в векторную базу
    print("3/3: Создание эмбеддингов и сохранение в ChromaDB...")
    add_documents(chunks)

    print("\n✅ Индексация завершена!")
    print(f"Всего добавлено: {get_collection_size()} документов.")


if __name__ == "__main__":
    main()
