import json
from pathlib import Path

# Загружаем evaluation_results.json
results_path = Path("benchmarks/evaluation_results.json")
with open(results_path, "r", encoding="utf-8") as f:
    results = json.load(f)

# Извлекаем уникальные документы
doc_mapping = {}
for result in results:
    for doc in result["context_docs"]:
        doc_id = doc["metadata"]["section_id"]
        if doc_id not in doc_mapping:
            doc_mapping[doc_id] = {
                "content_preview": doc["context"][:200] + "...",  # Первые 200 символов
                "full_content": doc["context"],
                "found_in_questions": []
            }
        doc_mapping[doc_id]["found_in_questions"].append(result["question_id"])

# Сохраняем маппинг
output_path = Path("benchmarks/doc_id_mapping.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(doc_mapping, f, ensure_ascii=False, indent=2)

print(f"✅ Создан маппинг для {len(doc_mapping)} уникальных документов!")
print(f"📁 Сохранено в: {output_path}")
