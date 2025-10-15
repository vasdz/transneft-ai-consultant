from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .rag.hybrid_search import hybrid_search, init_hybrid_search
from typing import Optional

import uvicorn
import mimetypes
import logging

from .config import ROOT_DIR, CORS_ORIGINS, FRONTEND_DIR
from .rag.pipeline import rag_answer
from .api_voice import router as voice_router

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Добавляем MIME типы для 3D моделей
mimetypes.add_type('model/gltf-binary', '.glb')
mimetypes.add_type('model/gltf+json', '.gltf')

# Инициализация FastAPI
app = FastAPI(
    title="Transneft AI Assistant API",
    description="API для чат-бота с голосовым взаимодействием",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str = Field(None, description="Вопрос пользователя")
    message: str = Field(None, description="Альтернативное поле для вопроса")

    def get_question(self):
        """Получить вопрос из любого доступного поля"""
        return self.question or self.message or ""


class ChatResponse(BaseModel):
    answer: str
    retrieved_contexts: list = []
    scores: list = []
    audioUrl: Optional[str] = None

app.include_router(voice_router)

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Текстовый чат endpoint."""
    question = request.question
    logger.info(f"Получен вопрос: {question[:100]}...")

    try:
        result = rag_answer(question, use_reranking=True, log_demo=False)

        if not result or "answer" not in result:
            logger.warning("RAG вернул пустой ответ")
            result = {
                "answer": "Извините, не удалось сформировать ответ. Попробуйте переформулировать вопрос.",
                "retrieved_contexts": []
            }

        logger.info(f"Ответ сгенерирован: {len(result['answer'])} символов")

        return ChatResponse(
            answer=result["answer"],
            retrieved_contexts=result.get("retrieved_contexts", []),
            scores=result.get("scores", []),
            audioUrl=None  # ✅ ДОБАВЬ (null = кнопка сгенерирует TTS)
        )

    except Exception as e:
        logger.error(f"Ошибка в chat_endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки запроса: {str(e)}"
        )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Transneft AI Assistant",
        "features": ["rag", "text_chat"]  # ВРЕМЕННО без голоса
    }


# === СТАТИЧЕСКИЕ ФАЙЛЫ ===

if FRONTEND_DIR.exists():
    logger.info(f"Mounting static from: {FRONTEND_DIR}")

    # Монтируем CSS
    css_dir = FRONTEND_DIR / "css"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
        logger.info(f"  OK CSS: {css_dir}")

    # Монтируем JS
    js_dir = FRONTEND_DIR / "js"
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
        logger.info(f"  OK JS: {js_dir}")

    # Монтируем Assets
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        logger.info(f"  OK Assets: {assets_dir}")

    # Монтируем Models
    models_dir = FRONTEND_DIR / "models"
    if models_dir.exists():
        app.mount("/models", StaticFiles(directory=str(models_dir)), name="models")
        logger.info(f"  OK Models: {models_dir}")

    # Альтернатива: монтируем всю папку /static
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static_all")
    logger.info(f"  OK Static (all): /static/*")

    @app.get("/")
    async def serve_index():
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            logger.info(f"Serving index.html from: {index_path}")
            return FileResponse(index_path)
        else:
            logger.error(f"index.html not found: {index_path}")
            return {"error": "index.html not found", "path": str(index_path)}

    @app.get("/favicon.ico")
    async def favicon():
        favicon_paths = [
            FRONTEND_DIR / "assets" / "images" / "favicon.ico",
            FRONTEND_DIR / "favicon.ico"
        ]

        for favicon_path in favicon_paths:
            if favicon_path.exists():
                return FileResponse(favicon_path)

        return {"status": "no favicon"}

else:
    logger.error(f"Frontend directory NOT FOUND: {FRONTEND_DIR}")


    @app.on_event("startup")
    async def startup_event():
        '''Инициализация при старте приложения.'''
        print("🔍 Инициализация гибридного поиска...")
        init_hybrid_search()
        print("✅ Гибридный поиск готов")


if __name__ == "__main__":
    print(f"\n{'=' * 60}")
    print(f"Starting Transneft AI Assistant")
    print(f"{'=' * 60}")
    print(f"ROOT_DIR: {ROOT_DIR}")
    print(f"FRONTEND_DIR: {FRONTEND_DIR}")
    print(f"{'=' * 60}\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)