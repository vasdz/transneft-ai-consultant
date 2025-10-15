import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))


def download_whisper_models():
    """Загрузка моделей Faster-Whisper."""
    from faster_whisper import WhisperModel

    print("=" * 70)
    print("ЗАГРУЗКА FASTER-WHISPER МОДЕЛЕЙ")
    print("=" * 70)

    # Загружаем несколько размеров для выбора
    models_to_download = [
        ("base", "cpu", "int8"),  # Быстрая, для тестов
        ("medium", "cpu", "int8"),  # Рекомендуемая для production
    ]

    for model_size, device, compute_type in models_to_download:
        print(f"\n📥 Загрузка модели: {model_size} ({device}/{compute_type})")

        try:
            model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=None  # Сохранит в ~/.cache/huggingface/hub
            )
            print(f"✅ Модель {model_size} успешно загружена")

            # Тестируем
            print(f"   Тестирование...")
            import numpy as np
            test_audio = np.zeros(16000, dtype=np.float32)  # 1 секунда тишины
            segments, info = model.transcribe(test_audio, language="ru")
            list(segments)  # Проверяем что работает
            print(f"   ✅ Тест пройден")

        except Exception as e:
            print(f"❌ Ошибка загрузки {model_size}: {e}")


def download_silero_models():
    """Загрузка моделей Silero TTS."""
    import torch

    print("\n" + "=" * 70)
    print("ЗАГРУЗКА SILERO TTS МОДЕЛЕЙ")
    print("=" * 70)

    try:
        print("\n📥 Загрузка Silero TTS для русского языка...")

        model, symbols, sample_rate, example_text, apply_tts = torch.hub.load(
            repo_or_dir='snakers4/silero-models',
            model='silero_tts',
            language='ru',
            speaker='xenia'
        )

        print(f"✅ Silero TTS загружена")
        print(f"   Частота дискретизации: {sample_rate} Hz")

        # Тестируем
        print(f"   Тестирование синтеза...")
        audio = apply_tts(
            texts=["Тест"],
            model=model,
            sample_rate=sample_rate,
            symbols=symbols,
            device="cpu"
        )
        print(f"   ✅ Тест пройден: сгенерировано {len(audio)} сэмплов")

    except Exception as e:
        print(f"❌ Ошибка загрузки Silero: {e}")


def main():
    print("\n🎯 ПРЕДЗАГРУЗКА МОДЕЛЕЙ ДЛЯ ON-PREMISE РАБОТЫ\n")
    print("Эти модели будут загружены ОДИН РАЗ и закэшированы локально.")
    print("После этого система будет работать полностью OFFLINE.\n")

    input("Нажмите Enter для начала загрузки (требуется интернет)...")

    try:
        download_whisper_models()
        download_silero_models()

        print("\n" + "=" * 70)
        print("✅ ВСЕ МОДЕЛИ УСПЕШНО ЗАГРУЖЕНЫ")
        print("=" * 70)
        print("\n📦 Модели сохранены в ~/.cache/huggingface/hub и ~/.cache/torch/")
        print("🔒 Теперь система может работать полностью OFFLINE")
        print("\n💡 Для работы без интернета просто запустите:")
        print("   uvicorn src.transneft_ai_consultant.backend.main:app --host 0.0.0.0 --port 8000")

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("\nПроверьте подключение к интернету и повторите попытку.")
        sys.exit(1)


if __name__ == "__main__":
    main()