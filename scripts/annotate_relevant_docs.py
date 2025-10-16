import json
from pathlib import Path

# Путь к файлам
ROOT = Path(__file__).parent.parent
BENCHMARK_PATH = ROOT / "benchmarks" / "benchmark.json"
MAPPING_PATH = ROOT / "benchmarks" / "doc_id_mapping.json"
OUTPUT_PATH = ROOT / "benchmarks" / "benchmark_annotated.json"

# Загрузка данных
with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
    benchmark = json.load(f)

with open(MAPPING_PATH, "r", encoding="utf-8") as f:
    doc_mapping = json.load(f)

# Преобразуем в удобный формат: {question_id: [doc_ids]}
# Логика: берём топ-1 документ для каждого вопроса как эталон
qid_to_docs = {}

for doc_id, info in doc_mapping.items():
    for qid in info["found_in_questions"]:
        if qid not in qid_to_docs:
            qid_to_docs[qid] = []
        qid_to_docs[qid].append(doc_id)

print("=" * 70)
print("📋 АВТОМАТИЧЕСКАЯ РАЗМЕТКА relevant_docs")
print("=" * 70)

if isinstance(benchmark, dict) and "questions" in benchmark:
    questions = benchmark["questions"]
else:
    questions = benchmark

annotated = []
for q in questions:
    qid = q.get("question_id", "")

    # Берём ПЕРВЫЙ найденный документ как релевантный (можно доработать логику)
    relevant = qid_to_docs.get(qid, [])[:1]  # Топ-1 документ

    q["relevant_docs"] = relevant
    annotated.append(q)

    print(f"\n{qid}: {q['question'][:60]}...")
    print(f"   ✅ Размечено: {relevant}")

# Сохранение
output_data = {"questions": annotated} if isinstance(benchmark, dict) and "questions" in benchmark else annotated

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 70)
print(f"✅ Сохранено: {OUTPUT_PATH}")
print("=" * 70)
print("\n⚠️ ВАЖНО: Это автоматическая разметка (топ-1 документ)!")
print("Проверьте вручную соответствие каждого документа эталонному ответу!")
print(f"\nДля проверки откройте:\n  - {OUTPUT_PATH}\n  - {MAPPING_PATH}")
