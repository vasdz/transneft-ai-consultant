from transneft_ai_consultant.backend.data_processing.parse_docx import read_docx_sections
from transneft_ai_consultant.backend.data_processing.chunk_text import chunk_sections
from transneft_ai_consultant.backend.rag.vector_store import add_documents, get_collection_size
from transneft_ai_consultant.backend.config import DOCX_PATH

def main():
    print("Запуск процесса индексации документов...")

    if get_collection_size() > 0:
        print(f"В базе данных уже есть {get_collection_size()} документов. Индексация отменена.")
        print("Если вы хотите переиндексировать данные, удалите папку /db/chroma.")
        return

    # Шаг 1: Парсинг документа
    # Используем путь из config.py
    print(f"1/3: Парсинг файла {DOCX_PATH}...")
    sections = read_docx_sections(DOCX_PATH)
    if not sections:
        print("Ошибка: не удалось извлечь секции из документа.")
        return
    print(f"Найдено {len(sections)} секций.")

    # Шаг 2: Разбивка на чанки
    print("2/3: Разбивка текста на чанки...")
    chunks = chunk_sections(sections)
    print(f"Создано {len(chunks)} чанков.")

    # Шаг 3: Добавление в векторную базу
    print("3/3: Создание эмбеддингов и сохранение в ChromaDB...")
    add_documents(chunks)

    print("\nИндексация успешно завершена!")
    print(f"Всего добавлено в базу: {get_collection_size()} документов.")


if __name__ == "__main__":
    main()