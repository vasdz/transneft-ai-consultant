# Инструкция по установке

## Требования
- ОС: Windows 10/11, Ubuntu 20.04+, macOS 11+
- Python: 3.10+
- RAM: 8 GB минимум (16 GB рекомендуется для локальной LLM)
- Диск: от 10 GB (локальная LLM требует больше)
- Браузер с поддержкой WebGL (для 3D)

## Шаги

1) Клонирование и окружение
git clone https://github.com/YOUR_USERNAME/transneft-ai-consultant.git
cd transneft-ai-consultant
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install --upgrade pip

2) Конфигурация
cp .env.example .env

Рекомендуемые поля:
LLM_MODEL=IlyaGusev/saiga_llama3_7b.Q4_K_M
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=cpu|cuda
CHROMA_PATH=db/chroma
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://localhost:8000,http://127.0.0.1:8000
TOP_K_RETRIEVER=5
HYBRID_SEARCH_ALPHA=0.5

3) Загрузка моделей
python scripts/download_models.py

локальная LLM (опц.):
python scripts/download_models.py --download-llm

4) Подготовка базы знаний
- Помести .docx/.pdf/.txt в:
src/transneft_ai_consultant/backend/data/.docs/

- Индексация:
python -m src.transneft_ai_consultant.backend.data_processing.populate_vector_store

5) Запуск backend
python -m src.transneft_ai_consultant.backend.api

http://127.0.0.1:8000

6) Запуск frontend
из папки src/transneft_ai_consultant/frontend/
python -m http.server 8080

http://127.0.0.1:8080

7) Настройка адреса API для фронта
- Добавь в `index.html` перед подключением скриптов:
<script>window.API_BASE_URL = 'http://127.0.0.1:8000';</script>

## Проверка

- Healthcheck:
curl http://127.0.0.1:8000/api/health

- Открой `http://127.0.0.1:8080` и задай вопрос в чате.

## Устранение проблем

- Нет пакета/конфликт:
pip install -r requirements.txt --force-reinstall

- Пустая ChromaDB:
ls src/transneft_ai_consultant/backend/data/.docs/
python -m src.transneft_ai_consu

- Кодировка входных документов:
python src/transneft_ai_consultant/backend/fix_encoding.py
python -m src.transneft_

- CORS при разных портах:
  - Проверь CORS_ORIGINS в `.env`.
  - Проверь `window.API_BASE_URL` в `index.html`.
- Микрофон не работает:
  - Разреши доступ в браузере, используй `https` в проде, проверь формат файла, что `voice.js` отправляет `multipart/form-data`.