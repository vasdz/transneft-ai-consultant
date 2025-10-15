import whisper
import logging
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="whisper")

logger = logging.getLogger(__name__)


class SpeechToText:
    """Класс для распознавания речи с помощью Whisper (on-premise)."""

    def __init__(self, model_size: str = "base", device: str = "auto"):
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        self.device = device
        self.model_size = model_size

        logger.info(f"[STT] Загрузка OpenAI Whisper '{model_size}' на {device}...")
        self.model = whisper.load_model(model_size, device=device)
        logger.info(f"[STT] OpenAI Whisper '{model_size}' готова к работе (device={device})")

    def _is_garbage_text(self, text: str) -> bool:
        """Проверка на мусорный текст."""
        if not text or not text.strip():
            return True
        text = text.strip()

        # Только знаки препинания / повторяющиеся символы
        unique_chars = set(text.replace(" ", ""))
        if len(unique_chars) <= 2 and all(c in "!?.,:;-_()[]{}\"'`~" for c in unique_chars):
            logger.warning(f"[STT] Отброшено (только знаки): '{text[:50]}'")
            return True

        import re
        if re.search(r'(.)\1{10,}', text):
            logger.warning(f"[STT] Отброшено (повторы): '{text[:50]}'")
            return True

        return False

    def transcribe_file(self, audio_path: str, language: str = "ru", initial_prompt: str = None) -> dict:
        """
        Транскрибирует аудио файл. Фильтры Whisper ослаблены (без жёстких порогов),
        чтобы лучше работать с реальными зашумлёнными записями.
        """
        logger.info(f"[STT] Транскрибирование файла: {audio_path}")

        if initial_prompt is None and language == "ru":
            initial_prompt = (
                "ПАО Транснефть, нефтепровод, магистральный трубопровод, "
                "транспортировка нефти, нефтепродукты, трубопроводная система."
            )

        try:
            result = self.model.transcribe(
                audio_path,
                language=language,
                initial_prompt=initial_prompt,
                fp16=False,  # FP16 только для GPU
                verbose=False,
                temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
                compression_ratio_threshold=None,
                logprob_threshold=None,
                no_speech_threshold=0.9,
                condition_on_previous_text=False
            )

            full_text = (result.get("text") or "").strip()
            segments = result.get("segments", [])

            for i, seg in enumerate(segments[:10], 1):
                logger.info(f"[STT] Сегмент {i} [{seg['start']:.2f}s-{seg['end']:.2f}s]: '{seg['text'].strip()}'")

            if self._is_garbage_text(full_text):
                logger.warning(f"[STT] Итоговый текст отброшен как мусор: '{full_text[:100]}'")
                full_text = ""

            return {
                "text": full_text,
                "segments": [
                    {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
                    for seg in segments
                ],
                "language": result.get("language", language),
                "language_probability": 1.0,  # Whisper не возвращает вероятность
                "duration": segments[-1]["end"] if segments else 0.0,
            }

        except Exception as e:
            logger.error(f"[STT] Ошибка транскрибирования: {e}", exc_info=True)
            return {
                "text": "",
                "segments": [],
                "language": language,
                "language_probability": 0.0,
                "duration": 0.0,
                "error": str(e),
            }

_stt_instance = None

def get_stt_instance(model_size: str = "base", device: str = "auto") -> SpeechToText:
    """Получить глобальный экземпляр STT (singleton pattern)."""
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = SpeechToText(model_size=model_size, device=device)
    return _stt_instance