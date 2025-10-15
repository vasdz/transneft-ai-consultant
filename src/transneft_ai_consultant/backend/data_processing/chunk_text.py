import re

try:
    import tiktoken

    has_tiktoken = True
except ImportError:
    has_tiktoken = False

_APPROX_TOKENS_PER_WORD = 1.3


def count_tokens(text: str, model_encoding: str = "cl100k_base") -> int:
    """Возвращает число токенов для текста."""
    if has_tiktoken:
        enc = tiktoken.get_encoding(model_encoding)
        return len(enc.encode(text))
    words = len(text.split())
    return max(1, int(words * _APPROX_TOKENS_PER_WORD))


def chunk_by_tokens(
        text: str,
        max_tokens: int = 512,
        overlap: int = 50,
        model_encoding: str = "cl100k_base"
) -> list:
    """
    Разбивает текст на чанки по количеству токенов с перекрытием.

    Args:
        text: текст для разбивки
        max_tokens: максимальное количество токенов в чанке
        overlap: количество токенов для перекрытия между чанками
        model_encoding: название кодировки tiktoken

    Returns:
        список текстовых чанков
    """
    if not text.strip():
        return []

    # Разбиваем текст на предложения для лучшего качества
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence, model_encoding)

        # Если одно предложение больше max_tokens, разбиваем его по словам
        if sentence_tokens > max_tokens:
            words = sentence.split()
            for word in words:
                word_tokens = count_tokens(word, model_encoding)

                if current_tokens + word_tokens > max_tokens:
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                        # Оставляем перекрытие по словам
                        overlap_size = min(overlap, len(current_chunk))
                        current_chunk = current_chunk[-overlap_size:] + [word]
                        current_tokens = count_tokens(" ".join(current_chunk), model_encoding)
                    else:
                        current_chunk = [word]
                        current_tokens = word_tokens
                else:
                    current_chunk.append(word)
                    current_tokens += word_tokens
        else:
            # Проверяем, поместится ли предложение
            if current_tokens + sentence_tokens > max_tokens:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens
                else:
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

    # Добавляем последний чанк
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def chunk_sections(sections: list, strategy: str = "smart") -> list:
    """
    Умная разбивка с сохранением контекста заголовков.

    Args:
        sections: список секций документа
        strategy: "simple" или "smart" (с сохранением заголовков)

    Returns:
        список чанков с метаданными
    """
    chunks = []

    for section in sections:
        title = section.get("title", "")
        content = section.get("content", "")

        if not content.strip():
            continue

        # Для коротких секций — не делим
        if count_tokens(content) <= 512:
            context = f"{title}\n\n{content}" if title and title != "ROOT" else content
            chunks.append({
                "context": context,
                "metadata": {
                    "section_title": title,
                    "source_file": section.get("source_file", "unknown"),
                    "section_id": section.get("section_id", "unknown"),
                    "chunk_index": 0,
                    "total_chunks": 1
                }
            })
            continue

        # Для длинных — умная разбивка
        text_chunks = chunk_by_tokens(content, max_tokens=400, overlap=80)

        for i, chunk_text in enumerate(text_chunks):
            if strategy == "smart" and title and title != "ROOT":
                full_chunk = f"Раздел: {title}\n\n{chunk_text}"
            else:
                full_chunk = chunk_text

            chunks.append({
                "context": full_chunk,
                "metadata": {
                    "section_title": title,
                    "source_file": section.get("source_file", "unknown"),
                    "section_id": section.get("section_id", "unknown"),
                    "chunk_index": i,
                    "total_chunks": len(text_chunks)
                }
            })

    return chunks
