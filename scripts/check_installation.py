import sys

from pathlib import Path

project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

def check_import(module_name, package_name=None):
    """Проверяет импорт модуля."""
    package_name = package_name or module_name
    try:
        __import__(module_name)
        print(f"✅ {package_name}")
        return True
    except ImportError as e:
        print(f"❌ {package_name}: {e}")
        return False


def main():
    print("=" * 60)
    print("ПРОВЕРКА ЗАВИСИМОСТЕЙ TRANSNEFT AI CONSULTANT")
    print("=" * 60)

    print("\n📦 Базовые зависимости:")
    base_deps = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("docx", "python-docx"),
        ("chromadb", "chromadb"),
        ("sklearn", "scikit-learn"),
        ("tiktoken", "tiktoken"),
        ("razdel", "razdel"),
        ("pymorphy2", "pymorphy2"),
        ("rouge_score", "rouge-score"),
    ]

    base_ok = sum(check_import(mod, pkg) for mod, pkg in base_deps)

    print(f"\n📦 Тяжелые зависимости (optional):")
    heavy_deps = [
        ("sentence_transformers", "sentence-transformers"),
        ("transformers", "transformers"),
        ("torch", "torch"),
        ("evaluate", "evaluate"),
    ]

    heavy_ok = sum(check_import(mod, pkg) for mod, pkg in heavy_deps)

    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТ: {base_ok}/{len(base_deps)} базовых, "
          f"{heavy_ok}/{len(heavy_deps)} тяжелых")
    print("=" * 60)

    if base_ok < len(base_deps):
        print("\n⚠️ Установите недостающие зависимости: pip install -e .")

    if heavy_ok < len(heavy_deps):
        print("\n⚠️ Для полной функциональности: pip install -e \".[heavy]\"")

    # Проверка config
    print("\n🔧 Проверка конфигурации...")
    try:
        from src.transneft_ai_consultant.backend.config import (
            ROOT_DIR, DOCX_PATH, DB_DIR, LLM_MODEL_PATH
        )
        print(f"✅ Config загружен")
        print(f"   ROOT_DIR: {ROOT_DIR}")
        print(f"   DOCX_PATH: {DOCX_PATH} (exists: {DOCX_PATH.exists()})")
        print(f"   DB_DIR: {DB_DIR} (exists: {DB_DIR.exists()})")
        print(f"   LLM_MODEL_PATH: {LLM_MODEL_PATH} (exists: {LLM_MODEL_PATH.exists()})")
    except Exception as e:
        print(f"❌ Ошибка config: {e}")

    print("\n✅ Проверка завершена!")


if __name__ == "__main__":
    main()