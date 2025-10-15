# API Документация

Базовый URL:
http://127.0.0.1:8000

text

## Health
GET `/api/health`
curl http://127.0.0.1:8000/api/health

text
Ответ:
{ "status": "ok", "llm_model": "IlyaGusev/saiga_llama3_8b", "chroma_docs": 156, "version": "1.0.0" }

text

## Вопрос‑ответ (RAG)
POST `/api/ask`
Тело:
{ "question": "Какова протяженность трубопроводов Транснефть?", "top_k": 5, "return_sources": true }

text
Пример:
curl -X POST http://127.0.0.1:8000/api/ask
-H "Content-Type: application/json"
-d '{"question":"Какова протяженность трубопроводов Транснефть?","top_k":5,"return_sources":true}'

text
Ответ:
{
"answer": "Совокупная длина ... более 67 000 км.",
"sources": [
{ "context": "...",
"metadata": { "source": "PAO-Transneft-reestr.pdf", "page": 8 },
"similarity": 0.94 }
],
"response_time": 1.23
}

text

## STT: распознавание речи
POST `/api/voice/stt`
Форма:
- `audio`: файл WAV/MP3/OGG
curl -X POST http://127.0.0.1:8000/api/voice/stt -F "audio=@recording.wav"

text
Ответ:
{ "text": "Какова протяженность трубопроводов Транснефть?", "confidence": 0.95, "duration": 3.2 }

text

## TTS: синтез речи
POST `/api/voice/tts`
Query:
- `text`: строка
- `speaker`: xenia|aidar|baya|kseniya (опц.)
curl -X POST "http://127.0.0.1:8000/api/voice/tts?text=Привет&speaker=xenia" --output speech.wav

text
Ответ: WAV.

## Документы (список)
GET `/api/documents`
curl http://127.0.0.1:8000/api/documents

text
Ответ:
{
"total_chunks": 156,
"documents": [
{ "source": "PAO-Transneft-reestr.pdf", "chunks": 87 },
{ "source": "company-info.docx", "chunks": 69 }
]
}

text

## CORS
Если фронтенд и бэкенд на разных портах/доменных именах, укажи домены в `.env`:
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080

text

## Коды ошибок
- 200 — успех
- 400 — неверный запрос (например, отсутствует `question`)
- 500 — внутренняя ошибка
Дополнение к .env.example (рекомендуемая правка CORS)

Замени строку на:

text
CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://localhost:8000,http://127.0.0.1:8000