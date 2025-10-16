# Транснефть AI Консультант

Интерактивный цифровой помощник с 3D‑аватаром, анимациями и RAG‑чат‑ботом, разработанный в соответствии с ТЗ ПАО «Транснефть».

## Состав

- Frontend: `index.html`, `css/main.css`, `css/animations.css`, `js/avatar.js`, `js/animation-sync.js`, `js/chat.js`, `js/voice.js`, `js/main.js`, `assets/models/*.glb`, `assets/images/*`.
- Backend: FastAPI (`api.py`, `api_voice.py`), RAG (`rag/*`), индексация (`data_processing/*`), метрики (`evaluation/*`), STT/TTS (`stt_tts/*`).
- Хранилище: ChromaDB (`db/chroma`), embeddings BGE‑m3.
- Скрипты: `scripts/*` для загрузки моделей, бенчмарка и оценки.

## Быстрый старт

1) Окружение и зависимости
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate

2) Конфигурация
cp .env.example .env

рекомендуемые правки:
LLM_MODEL=IlyaGusev/saiga_llama3_7b.Q4_K_M
EMBEDDING_DEVICE=cpu|cuda
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://localhost:8000,http://127.0.0.1:8000

3) Загрузка моделей
python scripts/download_models.py

опционально локальная LLM:
python scripts/download_models.py --download-llm

4) Подготовка базы знаний
помести .docx/.pdf/.txt в src/transneft_ai_consultant/backend/data/.docs/
python -m src.transneft_ai_consultant.backend.data_processing.populate_vector_store

5) Запуск backend и frontend 
python -m uvicorn transneft_ai_consultant.backend.api:app --host 127.0.0.1 --port 8000

API доступен на http://127.0.0.1:8000

6) Запуск frontend (вариант для разработки)
из папки src/transneft_ai_consultant/frontend/
python -m http.server 8080

открой http://127.0.0.1:8080

7) Связка фронта и API
- В `index.html` перед подключением скриптов добавь:
window.API_BASE_URL = 'http://127.0.0.1:8000';

- Убедись, что `chat.js` и `voice.js` читают `window.API_BASE_URL` для запросов `/api/*`.
- Если фронт и бэкенд на разных портах, проверь CORS_ORIGINS в `.env`.

## Фронтенд

- `avatar.js` — загрузка 3D‑модели (.glb) и инициализация сцены.
- `animation-sync.js` — синхронизация анимаций: приветствие, ожидание, вовлечение, завершение.
- `chat.js` — логика чата, вызовы `/api/ask`, показ источников.
- `voice.js` — запись микрофона и вызовы `/api/voice/stt` и `/api/voice/tts`.
- `main.js` — инициализация UI, события кнопок, связывание модулей.
- `css/main.css`, `css/animations.css` — базовые стили и анимации.

Расположи 3D‑модели в `src/transneft_ai_consultant/frontend/assets/models/` и укажи корректные пути в `avatar.js`.

## Дополнительные утилиты

- `check_installation.py` — проверка и установка зависимостей  
- `fix_encoding.py` — корректировка кодировки исходных документов  
- `question_filter.py` — фильтрация «неответимых» вопросов  
- `prepare_data.py` — вспомогательная загрузка и предобработка данных
- `extract_doc_ids.py` — создает словарь всех уникальных документов, которые были найдены системой
- `annotate_relevant_docs.py` — определяет, какие документы являются релевантными
- Метрики: `metrics.py`, `metrics_advanced.py`, `metrics_ranking.py`, `rouge_ru.py`, `pipeline.py`

## Бенчмарк и оценка

- Генерация:
python scripts/create_benchmark.py

- Оценка:
python scripts/run_evaluation.py

Результаты: `benchmarks/*.json`, `results/*.json`.

## Картинки проекта:
<img width="1280" height="774" alt="image" src="https://github.com/user-attachments/assets/ab4ed75e-8f65-4cd4-9460-bcda90d54ec4" />
<img width="1280" height="803" alt="image" src="https://github.com/user-attachments/assets/1f936298-847a-4190-800f-7ddcf8b16437" />
<img width="1280" height="747" alt="image" src="https://github.com/user-attachments/assets/7b1f0eee-fe15-4a4e-bd34-969e09ac729f" />
<img width="1280" height="759" alt="image" src="https://github.com/user-attachments/assets/b755f549-03e5-4746-88d2-180516dfe914" />


## Лицензия

MIT (см. LICENSE).
