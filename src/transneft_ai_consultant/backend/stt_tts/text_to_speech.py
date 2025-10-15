# backend/stt_tts/text_to_speech.py
"""
Text-to-Speech модуль на основе Silero TTS.
100% on-premise, работает offline.
"""

import torch
import re
from num2words import num2words
import logging
import os

logger = logging.getLogger(__name__)

SPEAKER_MAPPING = {
    "xenia": "kseniya",
    "kseniya": "kseniya",
    "aidar": "aidar",
    "baya": "baya",
    "irina": "irina",
    "natasha": "natasha",
    "ruslan": "ruslan",
    "eugene": "ruslan",
}


class TextToSpeech:
    """Класс для синтеза речи с помощью Silero TTS."""

    def __init__(
            self,
            language: str = "ru",
            speaker: str = "kseniya",
            device: str = None
    ):
        """
        Args:
            language: язык ('ru', 'en', 'de', 'es', 'fr')
            speaker: голос для русского:
                - 'kseniya' (женский) - РЕКОМЕНДУЕТСЯ
                - 'aidar' (мужской)
                - 'baya' (женский)
                - 'irina' (женский)
                - 'natasha' (женский)
                - 'ruslan' (мужской)
            device: 'cuda' или 'cpu'
        """
        self.language = language

        # Конвертируем имя
        if speaker in SPEAKER_MAPPING:
            self.speaker = SPEAKER_MAPPING[speaker]
            logger.info(f"Конвертация: {speaker} -> {self.speaker}")
        else:
            self.speaker = speaker

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        logger.info(f"🔊 Загрузка Silero TTS ({language}, speaker={self.speaker})...")

        try:
            # ИСПРАВЛЕНО: Используем прямую загрузку модели через torch.package
            # Ссылки на модели: https://models.silero.ai/models/tts/
            model_urls = {
                'ru': 'https://models.silero.ai/models/tts/ru/v4_ru.pt',
                'en': 'https://models.silero.ai/models/tts/en/v3_en.pt',
                'de': 'https://models.silero.ai/models/tts/de/v3_de.pt',
                'es': 'https://models.silero.ai/models/tts/es/v3_es.pt',
                'fr': 'https://models.silero.ai/models/tts/fr/v3_fr.pt',
            }

            if language not in model_urls:
                raise ValueError(f"Язык '{language}' не поддерживается. Доступны: {list(model_urls.keys())}")

            # Путь для кэширования модели
            cache_dir = os.path.expanduser('~/.cache/silero_tts')
            os.makedirs(cache_dir, exist_ok=True)

            model_path = os.path.join(cache_dir, f'v4_{language}.pt')

            # Скачиваем модель если её нет
            if not os.path.isfile(model_path):
                logger.info(f"Скачивание модели {language} (~100MB)...")
                torch.hub.download_url_to_file(model_urls[language], model_path)
                logger.info("✅ Модель скачана")
            else:
                logger.info("✅ Используется кэшированная модель")

            # Загружаем модель через torch.package
            self.model = torch.package.PackageImporter(model_path).load_pickle("tts_models", "model")
            self.model.to(self.device)

            self.sample_rate = 48000

            logger.info(f"✅ Silero TTS загружена: {language}/{self.speaker} на {self.device}")
            logger.info(f"   Частота дискретизации: {self.sample_rate} Hz")
            logger.info(f"   Тип модели: {type(self.model)}")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки Silero TTS: {e}")
            raise

    def preprocess_text(self, text: str) -> str:
        """Предобработка текста."""
        if not text:
            return ""

        if self.language == "ru":
            def replace_number(match):
                num = match.group(0)
                try:
                    return num2words(int(num), lang='ru')
                except:
                    return num

            text = re.sub(r'\b\d+\b', replace_number, text)

            abbreviations = {
                "ПАО": "публичное акционерное общество",
                "АО": "акционерное общество",
                "ООО": "общество с ограниченной ответственностью",
                "км": "километров",
                "м³": "кубических метров",
                "тыс.": "тысяч",
                "млн": "миллионов",
                "млрд": "миллиардов",
                "т.": "тонн",
            }

            for abbr, full in abbreviations.items():
                text = re.sub(r'\b' + re.escape(abbr) + r'\b', full, text, flags=re.IGNORECASE)

        return text

    def synthesize(
            self,
            text: str,
            output_path: str = None,
            preprocess: bool = True
    ) -> torch.Tensor:
        """Синтезирует речь из текста."""
        if not text or not text.strip():
            logger.warning("Пустой текст для синтеза")
            return torch.tensor([])

        if preprocess:
            text = self.preprocess_text(text)

        logger.info(f"🔊 Синтез речи: {text[:100]}...")

        try:
            # Вызов модели
            audio = self.model.apply_tts(
                text=text,
                speaker=self.speaker,
                sample_rate=self.sample_rate
            )

            # Конвертируем в tensor
            if not isinstance(audio, torch.Tensor):
                import numpy as np
                if isinstance(audio, np.ndarray):
                    audio = torch.from_numpy(audio)

            # Сохраняем в файл
            if output_path and len(audio) > 0:
                import soundfile as sf

                audio_np = audio.cpu().numpy() if isinstance(audio, torch.Tensor) else audio

                # Нормализация
                if abs(audio_np).max() > 1.0:
                    audio_np = audio_np / abs(audio_np).max()

                sf.write(output_path, audio_np, self.sample_rate)
                logger.info(f"✅ Аудио сохранено: {output_path} ({os.path.getsize(output_path)} bytes)")

            logger.info(f"✅ Синтез завершен: {len(audio)} сэмплов")

            return audio

        except Exception as e:
            logger.error(f"❌ Ошибка синтеза: {e}", exc_info=True)
            raise


# Singleton
_tts_instance = None


def get_tts_instance(speaker: str = "xenia", language: str = "ru") -> TextToSpeech:
    """Получить глобальный экземпляр TTS."""
    global _tts_instance

    real_speaker = SPEAKER_MAPPING.get(speaker, speaker)

    if _tts_instance is not None:
        if _tts_instance.speaker == real_speaker and _tts_instance.language == language:
            return _tts_instance

    _tts_instance = TextToSpeech(language=language, speaker=speaker)
    return _tts_instance


def list_available_speakers() -> dict:
    """Список доступных голосов."""
    return {
        "ru": [
            {"name": "xenia", "real_name": "kseniya", "gender": "female", "recommended": True},
            {"name": "kseniya", "real_name": "kseniya", "gender": "female", "recommended": True},
            {"name": "aidar", "real_name": "aidar", "gender": "male", "recommended": True},
            {"name": "baya", "real_name": "baya", "gender": "female", "recommended": False},
            {"name": "irina", "real_name": "irina", "gender": "female", "recommended": False},
            {"name": "natasha", "real_name": "natasha", "gender": "female", "recommended": False},
            {"name": "ruslan", "real_name": "ruslan", "gender": "male", "recommended": False},
        ]
    }


# Тест
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n🧪 ТЕСТИРОВАНИЕ TEXT-TO-SPEECH\n")

    try:
        tts = get_tts_instance(speaker="xenia")
        print(f"✅ Модель загружена: {type(tts.model)}")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    test_texts = [
        "Здравствуйте! Я цифровой консультант ПАО Транснефть.",
        "Тест работы синтеза речи.",
    ]

    for i, text in enumerate(test_texts, 1):
        print(f"\nТест {i}: {text}")
        output_file = f"test_tts_{i}.wav"

        try:
            audio = tts.synthesize(text, output_path=output_file, preprocess=True)
            print(f"✅ Сохранено: {output_file} ({len(audio)} сэмплов)")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback

            traceback.print_exc()

    print("\n✅ Тестирование завершено! Воспроизведите WAV файлы.\n")
