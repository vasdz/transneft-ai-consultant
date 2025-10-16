import json
import chromadb
import random
import sys

from pathlib import Path
from tqdm import tqdm

project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

try:
    from backend.rag.llm import ask_llm
except ImportError:
    from src.transneft_ai_consultant.backend.rag.llm import ask_llm

NUM_QUESTIONS_TO_GENERATE = 30
NUM_NEGATIVE_SAMPLES = 10


# ===============================================
# ГЕНЕРАЦИЯ ПОЗИТИВНЫХ ВОПРОСОВ (С ОТВЕТАМИ)
# ===============================================

def generate_qa_from_context(context: str, difficulty: str = "base") -> dict | None:
    """Генерирует пару вопрос-ответ с контролем сложности."""

    # Разные промпты для разных типов вопросов
    prompts = {
        "factual": """На основе текста создай ФАКТИЧЕСКИЙ вопрос, требующий точного ответа (дата, число, название).
Текст: {context}

Формат:
Вопрос: [конкретный вопрос]
Ответ: [точный ответ из текста]""",

        "explanatory": """На основе текста создай вопрос, требующий ОБЪЯСНЕНИЯ или описания процесса.
Текст: {context}

Формат:
Вопрос: [вопрос "Как", "Почему", "Что представляет собой"]
Ответ: [развернутый ответ из текста]""",

        "comparative": """На основе текста создай вопрос для СРАВНЕНИЯ или перечисления.
Текст: {context}

Формат:
Вопрос: [вопрос с "Какие", "Перечислите"]
Ответ: [список или сравнение из текста]"""
    }

    question_type = random.choice(list(prompts.keys()))
    prompt = prompts[question_type].format(context=context)

    try:
        response = ask_llm(prompt, max_tokens=400, temperature=0.4)

        if "Вопрос:" in response and "Ответ:" in response:
            question = response.split("Вопрос:")[1].split("Ответ:")[0].strip()
            answer = response.split("Ответ:")[1].strip()

            # ВАЛИДАЦИЯ качества
            if (len(question.split()) >= 5 and len(answer.split()) >= 10 and
                    question.endswith("?") and len(answer) < 500):
                return {
                    "question": question,
                    "ground_truth": answer,
                    "type": question_type,
                    "difficulty": difficulty
                }
    except Exception as e:
        print(f"[WARN] Ошибка генерации: {e}")

    return None


# ===============================================
# ГЕНЕРАЦИЯ НЕГАТИВНЫХ ПРИМЕРОВ (БЕЗ ОТВЕТОВ)
# ===============================================

def generate_negative_samples(num_samples: int = 20) -> list:
    """Генерирует вопросы, на которые НЕТ ответа в базе знаний."""

    negative_questions = [
        # Unanswerable (информация отсутствует)
        {
            'question': 'Какова средняя зарплата сотрудников Транснефть?',
            'expected_answer': 'NO_ANSWER',
            'type': 'unanswerable',
            'reason': 'Информация о зарплатах не предоставлена в документации'
        },
        {
            'question': 'Сколько акций Транснефть принадлежит иностранным инвесторам?',
            'expected_answer': 'NO_ANSWER',
            'type': 'unanswerable',
            'reason': 'Документ указывает только, что 100% акций в федеральной собственности'
        },
        {
            'question': 'Какой размер дивидендов на одну акцию Транснефти был в 2023 году?',
            'expected_answer': 'NO_ANSWER',
            'type': 'unanswerable',
            'reason': 'Финансовая информация о дивидендах не включена'
        },
        {
            'question': 'Сколько сотрудников работает в офисе Транснефти в Нью-Йорке?',
            'expected_answer': 'NO_ANSWER',
            'type': 'unanswerable',
            'reason': 'Информация о зарубежных офисах отсутствует'
        },
        {
            'question': 'Какой процент акций Транснефти принадлежит частным инвесторам?',
            'expected_answer': 'NO_ANSWER',
            'type': 'unanswerable',
            'reason': '100% акций в федеральной собственности'
        },
        {
            'question': 'Какие курорты использует руководство Транснефти для отдыха?',
            'expected_answer': 'NO_ANSWER',
            'type': 'unanswerable',
            'reason': 'Личная информация руководства не предоставляется'
        },
        {
            'question': 'Какой самый популярный бренд автомобилей у сотрудников Транснефти?',
            'expected_answer': 'NO_ANSWER',
            'type': 'unanswerable',
            'reason': 'Личные предпочтения сотрудников не документируются'
        },
        {
            'question': 'Сколько денег Транснефть потратила на рекламу в 2022 году?',
            'expected_answer': 'NO_ANSWER',
            'type': 'unanswerable',
            'reason': 'Маркетинговый бюджет не раскрывается'
        },
        {
            'question': 'Какие меры принимает Транснефть для снижения углеродного следа?',
            'expected_answer': 'NO_ANSWER',
            'type': 'unanswerable',
            'reason': 'Экологические инициативы упомянуты, но конкретные меры не детализированы'
        },
        {
            'question': 'Какая средняя скорость течения нефти в трубопроводе ВСТО?',
            'expected_answer': 'NO_ANSWER',
            'type': 'unanswerable',
            'reason': 'Технические параметры скорости течения не указаны'
        },

        {
            'question': 'Какие планы у Транснефть на 2030 год?',
            'expected_answer': 'NO_ANSWER',
            'type': 'future_prediction',
            'reason': 'Долгосрочные планы на 2030 не детализированы'
        },
        {
            'question': 'Какие планы Транснефти по строительству трубопровода в Африку?',
            'expected_answer': 'NO_ANSWER',
            'type': 'future_prediction',
            'reason': 'Проекты за пределами России/СНГ не упоминаются'
        },
        {
            'question': 'Будет ли Транснефть открывать новые офисы в Азии?',
            'expected_answer': 'NO_ANSWER',
            'type': 'future_prediction',
            'reason': 'Планы расширения офисов не раскрываются'
        },
        {
            'question': 'Когда Транснефть планирует выйти на IPO?',
            'expected_answer': 'NO_ANSWER',
            'type': 'future_prediction',
            'reason': '100% акций в государственной собственности, IPO не планируется'
        },
        {
            'question': 'Какие новые технологии Транснефть внедрит в 2026 году?',
            'expected_answer': 'NO_ANSWER',
            'type': 'future_prediction',
            'reason': 'Конкретные планы внедрения технологий на 2026 год не описаны'
        },

        {
            'question': 'Какова история создания компании Газпром?',
            'expected_answer': 'NO_ANSWER',
            'type': 'out_of_scope',
            'reason': 'Вопрос касается другой компании'
        },
        {
            'question': 'Какой самый длинный газопровод в мире?',
            'expected_answer': 'NO_ANSWER',
            'type': 'out_of_scope',
            'reason': 'Вопрос о газопроводах, не о нефтепроводах'
        },
        {
            'question': 'Сколько нефти добывает Роснефть ежегодно?',
            'expected_answer': 'NO_ANSWER',
            'type': 'out_of_scope',
            'reason': 'Вопрос о другой компании'
        },
        {
            'question': 'Какова цена на нефть марки Brent сегодня?',
            'expected_answer': 'NO_ANSWER',
            'type': 'out_of_scope',
            'reason': 'Вопрос о рыночных ценах, а не о Транснефти'
        },
        {
            'question': 'Кто является президентом России?',
            'expected_answer': 'NO_ANSWER',
            'type': 'out_of_scope',
            'reason': 'Общий политический вопрос, не связанный с компанией'
        }
    ]

    return negative_questions[:num_samples]


# ===============================================
# ГЛАВНАЯ ФУНКЦИЯ
# ===============================================

def main():
    print("=" * 60)
    print("📊 СОЗДАНИЕ РАСШИРЕННОГО БЕНЧМАРКА")
    print("=" * 60)

    # === 1. ПОДКЛЮЧЕНИЕ К БД ===
    print("\n[1/4] Подключение к ChromaDB...")
    BASE_DIR = Path(__file__).parent.parent  # корень проекта
    client = chromadb.PersistentClient(path=str(BASE_DIR / "db"))
    try:
        collection = client.get_collection(name="transneft_docs")
    except chromadb.errors.NotFoundError:
        print("⚠️ Коллекция не найдена — используйте существующий benchmark.json")
        import sys
        sys.exit(1)

    all_docs = collection.get(include=["documents", "metadatas"])
    contexts = all_docs["documents"]
    metadatas = all_docs["metadatas"]

    print(f"✅ Загружено {len(contexts)} документов из базы")

    # Сортируем по длине для разнообразия
    context_data = list(zip(contexts, metadatas))
    context_data.sort(key=lambda x: len(x[0]), reverse=True)

    # === 2. ГЕНЕРАЦИЯ ПОЗИТИВНЫХ ВОПРОСОВ ===
    print(f"\n[2/4] Генерация {NUM_QUESTIONS_TO_GENERATE} вопросов с ответами...")
    benchmark_data = []
    attempts = 0
    max_attempts = len(contexts) * 2

    with tqdm(total=NUM_QUESTIONS_TO_GENERATE, desc="Генерация QA") as pbar:
        while len(benchmark_data) < NUM_QUESTIONS_TO_GENERATE and attempts < max_attempts:
            idx = attempts % len(context_data)
            context, metadata = context_data[idx]

            # Пропускаем слишком короткие или длинные
            if not (50 <= len(context.split()) <= 300):
                attempts += 1
                continue

            triplet = generate_qa_from_context(context)

            if triplet:
                triplet["context"] = context
                triplet["metadata"] = metadata
                benchmark_data.append(triplet)
                pbar.update(1)

            attempts += 1

    # === 3. ДОБАВЛЕНИЕ НЕГАТИВНЫХ ПРИМЕРОВ ===
    print(f"\n[3/4] Генерация {NUM_NEGATIVE_SAMPLES} негативных примеров...")
    negative_samples = generate_negative_samples(NUM_NEGATIVE_SAMPLES)

    Path("benchmarks").mkdir(exist_ok=True)

    # Сохраняем негативные примеры отдельно
    with open("benchmarks/negative_samples.json", "w", encoding="utf-8") as f:
        json.dump(negative_samples, f, ensure_ascii=False, indent=2)

    print(f"✅ Создано {len(negative_samples)} негативных примеров")

    # === 4. СТАТИСТИКА И СОХРАНЕНИЕ ===
    print(f"\n[4/4] Сохранение benchmark.json...")

    # Добавляем статистику
    stats = {
        "total_questions": len(benchmark_data),
        "question_types": {},
        "difficulty_levels": {},
        "avg_question_length": sum(len(q["question"].split()) for q in benchmark_data) / len(
            benchmark_data) if benchmark_data else 0,
        "avg_answer_length": sum(len(q["ground_truth"].split()) for q in benchmark_data) / len(
            benchmark_data) if benchmark_data else 0,
        "negative_samples_count": len(negative_samples)
    }

    for item in benchmark_data:
        qtype = item.get("type", "unknown")
        stats["question_types"][qtype] = stats["question_types"].get(qtype, 0) + 1

        difficulty = item.get("difficulty", "base")
        stats["difficulty_levels"][difficulty] = stats["difficulty_levels"].get(difficulty, 0) + 1

    output = {
        "metadata": stats,
        "benchmark": benchmark_data
    }

    # Сохранение в benchmarks/
    Path("benchmarks").mkdir(exist_ok=True)
    with open("benchmarks/benchmark.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # === ФИНАЛЬНЫЙ ОТЧЁТ ===
    print(f"\n{'=' * 60}")
    print(f"✅ БЕНЧМАРК СОЗДАН УСПЕШНО!")
    print(f"{'=' * 60}")
    print(f"📊 Позитивные вопросы: {len(benchmark_data)}")
    print(f"❌ Негативные примеры: {len(negative_samples)}")
    print(f"\n📈 Типы вопросов:")
    for qtype, count in stats['question_types'].items():
        print(f"  • {qtype}: {count}")
    print(f"\n📏 Средняя длина:")
    print(f"  • Вопрос: {stats['avg_question_length']:.1f} слов")
    print(f"  • Ответ: {stats['avg_answer_length']:.1f} слов")
    print(f"\n💾 Файлы сохранены:")
    print(f"  • benchmarks/benchmark.json")
    print(f"  • benchmarks/negative_samples.json")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
