from llama_cpp import Llama
import torch
import time

LLM = None

def get_llm():
    global LLM
    if LLM is None:
        print("Инициализация LLM (Saiga)...")

        use_cuda = torch.cuda.is_available()
        n_gpu_layers = 12 if use_cuda else 0
        print(f"Используем CUDA: {use_cuda}, n_gpu_layers={n_gpu_layers}")

        LLM = Llama(
            model_path="src/transneft_ai_consultant/backend/models/saiga_mistral_7b.Q4_K_M.gguf",
            n_ctx=4096,
            n_threads=8,           # CPU threads
            n_gpu_layers=n_gpu_layers,
            verbose=False
        )
        print("LLM инициализирована.")
    return LLM


def ask_llm(prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> str:
    llm = get_llm()

    # КРИТИЧНО: правильное форматирование для Saiga
    formatted_prompt = f"""<s>system
Ты - официальный AI-консультант ПАО «Транснефть». Отвечай кратко и по делу.</s>
<s>user
{prompt}</s>
<s>bot
"""

    try:
        response = llm(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["</s>", "<s>"],  # ДОБАВЛЕНО
            echo=False
        )

        answer = response['choices'][0]['text'].strip()

        # Проверка на пустой ответ
        if not answer or len(answer) < 10:
            return "Извините, не могу найти информацию. Переформулируйте запрос."

        return answer
    except Exception as e:
        return "Ошибка при генерации ответа."





