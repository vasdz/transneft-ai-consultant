from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent.parent.absolute()

SRC_DIR = ROOT_DIR / "src"
BACKEND_DIR = SRC_DIR / "transneft_ai_consultant" / "backend"
FRONTEND_DIR = SRC_DIR / "transneft_ai_consultant" / "frontend"

DATA_DIR = BACKEND_DIR / "data"
DOCX_PATH = DATA_DIR / "PAO_Transneft_reestr.docx"

DB_DIR = ROOT_DIR / "db"
MODELS_DIR = ROOT_DIR / "models"
BENCHMARK_PATH = ROOT_DIR / "benchmark.json"
EVAL_RESULTS_PATH = ROOT_DIR / "evaluation_results.json"
FINAL_METRICS_PATH = ROOT_DIR / "final_metrics.json"

# --- Модели ---
LLM_MODEL_PATH = MODELS_DIR / "saiga_mistral_7b.Q4_K_M.gguf"
EMBEDDER_MODEL_NAME = 'BAAI/bge-m3'
RERANKER_MODEL_NAME = 'cross-encoder/ms-marco-MiniLM-L-6-v2'

# --- RAG ---
COLLECTION_NAME = "transneft_docs"
TOP_K_RETRIEVER = 3
INITIAL_TOP_K = 10
MIN_SIMILARITY_THRESHOLD = 0.3
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80

# --- API ---
CORS_ORIGINS = ["*"]

# --- LLM ---
LLM_N_CTX = 4096
LLM_N_THREADS = 8
LLM_N_GPU_LAYERS = 32
LLM_MAX_TOKENS = 512
LLM_TEMPERATURE = 0.1

# --- Бенчмарк ---
NUM_BENCHMARK_QUESTIONS = 100
BENCHMARK_MAX_ATTEMPTS_MULTIPLIER = 2

# --- Проверка критических путей при импорте ---
if __name__ != "__main__":
    print(f"[Config] ROOT_DIR: {ROOT_DIR}")
    print(f"[Config] FRONTEND_DIR: {FRONTEND_DIR}")
    print(f"[Config] DOCX_PATH: {DOCX_PATH}")
    print(f"[Config] DB_DIR: {DB_DIR}")
