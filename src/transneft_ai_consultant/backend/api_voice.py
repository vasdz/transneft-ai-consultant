import tempfile
import logging
import base64
import numpy as np

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/voice", tags=["voice"])

# Временная директория для аудио файлов
TEMP_AUDIO_DIR = Path(tempfile.gettempdir()) / "transneft_audio"
TEMP_AUDIO_DIR.mkdir(exist_ok=True)

# Импорты для конвертации аудио
try:
    import soundfile as sf
    import librosa
    AUDIO_CONVERTER_AVAILABLE = True
    logger.info("[API_VOICE] soundfile/librosa доступны")
except ImportError as e:
    AUDIO_CONVERTER_AVAILABLE = False
    logger.warning(f"[API_VOICE] soundfile/librosa недоступны: {e}")

# Импорт шумоподавления (опционально)
try:
    import noisereduce as nr
    NOISE_REDUCE_AVAILABLE = True
    logger.info("[API_VOICE] noisereduce доступен")
except ImportError:
    NOISE_REDUCE_AVAILABLE = False
    logger.warning("[API_VOICE] noisereduce недоступен: установите pip install noisereduce")

# Импорты модулей STT/TTS/RAG
try:
    from .stt_tts.speech_to_text import get_stt_instance
    STT_AVAILABLE = True
    logger.info("[API_VOICE] STT модуль импортирован")
except ImportError as e:
    STT_AVAILABLE = False
    logger.warning(f"[API_VOICE] STT недоступен: {e}")

try:
    from .stt_tts.text_to_speech import get_tts_instance
    TTS_AVAILABLE = True
    logger.info("[API_VOICE] TTS модуль импортирован")
except ImportError as e:
    TTS_AVAILABLE = False
    logger.warning(f"[API_VOICE] TTS недоступен: {e}")

try:
    from .rag.pipeline import rag_answer
    RAG_AVAILABLE = True
except ImportError as e:
    RAG_AVAILABLE = False
    logger.warning(f"[API_VOICE] RAG недоступен: {e}")


def enhanced_preprocess(audio_data: np.ndarray, sr: int = 16000,
                        target_amp: float = 0.9, target_rms: float = 0.1,
                        denoise: bool = False) -> np.ndarray:
    """
    Та же предобработка, что в вашем test_audio.py:
      - амплификация до target_amp
      - RMS нормализация до target_rms
      - удаление DC offset
      - (опц.) шумоподавление
      - клиппинг в [-1, 1]
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    current_max = float(np.abs(audio_data).max() or 0.0)
    if current_max > 0 and current_max < 0.5:
        audio_data = audio_data / current_max * target_amp
        logger.info(f"[API_VOICE] Усилено до target_amp={target_amp}")

    current_rms = float(np.sqrt(np.mean(audio_data**2)) or 0.0)
    if current_rms > 0:
        audio_data = audio_data * (target_rms / current_rms)
        logger.info(f"[API_VOICE] RMS нормализация: {current_rms:.4f} -> {target_rms:.4f}")

    # Удаление DC offset
    audio_data = audio_data - float(np.mean(audio_data))

    # (опционально) шумоподавление
    if denoise and NOISE_REDUCE_AVAILABLE:
        audio_data = nr.reduce_noise(y=audio_data, sr=sr, stationary=True)
        logger.info("[API_VOICE] Шумоподавление применено (stationary=True)")
    elif denoise:
        logger.warning("[API_VOICE] denoise=true, но noisereduce не установлен")

    # Клиппинг в диапазон [-1, 1] перед PCM_16
    audio_data = np.clip(audio_data, -1.0, 1.0)
    return audio_data


@router.get("/status")
async def voice_status():
    return {
        "stt_available": STT_AVAILABLE,
        "tts_available": TTS_AVAILABLE,
        "rag_available": RAG_AVAILABLE,
        "audio_converter_available": AUDIO_CONVERTER_AVAILABLE,
        "noise_reduce_available": NOISE_REDUCE_AVAILABLE,
        "voice_chat_available": STT_AVAILABLE and TTS_AVAILABLE and RAG_AVAILABLE
    }


@router.post("/stt")
async def speech_to_text_endpoint(
    audio: UploadFile = File(...),
    enhanced: bool = Query(True, description="Включить улучшенную предобработку (как в тестовом скрипте)"),
    denoise: bool = Query(False, description="Шумоподавление (noisereduce)")
):
    """
    Speech-to-Text endpoint с конвертацией аудио в mono 16kHz и
    улучшенной предобработкой (по умолчанию включена).
    """
    if not STT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="STT модуль недоступен. Установите зависимости: pip install openai-whisper"
        )
    if not AUDIO_CONVERTER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Аудио конвертер недоступен. Установите: pip install soundfile librosa"
        )

    temp_input = None
    temp_wav = None
    try:
        temp_input = TEMP_AUDIO_DIR / f"input_{audio.filename}"
        with open(temp_input, "wb") as f:
            content = await audio.read()
            f.write(content)
        logger.info(f"[API_VOICE] STT: получен файл {temp_input} ({len(content)} bytes)")

        temp_wav = TEMP_AUDIO_DIR / f"converted_{audio.filename}.wav"
        audio_data, _ = librosa.load(str(temp_input), sr=16000, mono=True)

        # То же, что в test_audio.py
        if enhanced:
            audio_data = enhanced_preprocess(audio_data, 16000, target_amp=0.9, target_rms=0.1, denoise=denoise)
        else:
            # Базовая нормализация + клиппинг
            audio_data = librosa.util.normalize(audio_data)
            audio_data = np.clip(audio_data, -1.0, 1.0)

        sf.write(str(temp_wav), audio_data, 16000, subtype='PCM_16')
        logger.info(f"[API_VOICE] Аудио сконвертировано: {temp_wav} (len={len(audio_data)/16000:.2f}s)")

        stt = get_stt_instance(model_size="base")
        result = stt.transcribe_file(str(temp_wav), language="ru")
        text = (result.get("text") or "").strip()

        # Очистка
        temp_input.unlink(missing_ok=True)
        temp_wav.unlink(missing_ok=True)

        if not text:
            raise HTTPException(status_code=400, detail="Не удалось распознать речь.")
        return {
            "text": text,
            "language": result.get("language", "ru"),
            "segments": len(result.get("segments", []))
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API_VOICE] Ошибка STT: {e}", exc_info=True)
        if temp_input and temp_input.exists():
            temp_input.unlink(missing_ok=True)
        if temp_wav and temp_wav.exists():
            temp_wav.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts")
async def text_to_speech_endpoint(
    text: str = Query(..., description="Текст для синтеза"),
    speaker: str = Query("xenia", description="Голос: xenia, aidar, baya, irina, natasha, ruslan"),
    return_file: bool = Query(False, description="Вернуть файл или base64")
):
    if not TTS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="TTS недоступен. Установите: pip install torch soundfile"
        )
    try:
        logger.info(f"[API_VOICE] TTS: синтез текста ({len(text)} символов), голос={speaker}")
        tts = get_tts_instance(speaker=speaker)

        output_path = TEMP_AUDIO_DIR / f"output_{hash(text)}.wav"
        _ = tts.synthesize(text, output_path=str(output_path), preprocess=True)

        if return_file:
            return FileResponse(path=output_path, media_type="audio/wav", filename="response.wav")
        else:
            # Base64 вариант
            with open(output_path, "rb") as f:
                audio_bytes = f.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            output_path.unlink(missing_ok=True)
            return {"audio_base64": audio_base64, "sample_rate": tts.sample_rate, "speaker": speaker}

    except Exception as e:
        logger.error(f"[API_VOICE] Ошибка TTS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice-chat")
async def voice_chat_endpoint(
    audio: UploadFile = File(...),
    speaker: str = Query("xenia", description="Голос для ответа"),
    enhanced: bool = Query(True, description="Улучшенная предобработка (как в тесте)"),
    denoise: bool = Query(False, description="Шумоподавление")
):
    if not (STT_AVAILABLE and TTS_AVAILABLE and RAG_AVAILABLE):
        raise HTTPException(status_code=503, detail="Voice chat недоступен. Установите все модули.")
    if not AUDIO_CONVERTER_AVAILABLE:
        raise HTTPException(status_code=503, detail="Аудио конвертер недоступен. Установите: pip install soundfile librosa")

    temp_input = None
    temp_wav = None
    try:
        logger.info("[API_VOICE] Voice Chat: начало обработки")

        temp_input = TEMP_AUDIO_DIR / f"voice_input_{audio.filename}"
        with open(temp_input, "wb") as f:
            content = await audio.read()
            f.write(content)

        temp_wav = TEMP_AUDIO_DIR / f"voice_converted_{audio.filename}.wav"
        audio_data, _ = librosa.load(str(temp_input), sr=16000, mono=True)
        audio_data = enhanced_preprocess(audio_data, 16000, target_amp=0.9, target_rms=0.1, denoise=denoise) if enhanced \
            else np.clip(librosa.util.normalize(audio_data), -1.0, 1.0)
        sf.write(str(temp_wav), audio_data, 16000, subtype='PCM_16')

        # STT
        stt = get_stt_instance(model_size="base")
        stt_result = stt.transcribe_file(str(temp_wav), language="ru")
        question = (stt_result.get("text") or "").strip()

        temp_input.unlink(missing_ok=True)
        temp_wav.unlink(missing_ok=True)

        if not question:
            raise HTTPException(status_code=400, detail="Не удалось распознать речь.")

        logger.info(f"[API_VOICE] [1/3] STT: {question[:100]}...")

        # RAG → ответ
        rag_result = rag_answer(question, use_reranking=True, log_demo=False)
        answer = rag_result.get("answer", "")

        # TTS → голос
        tts = get_tts_instance(speaker=speaker)
        output_path = TEMP_AUDIO_DIR / f"voice_output_{hash(question)}.wav"
        tts.synthesize(answer, output_path=str(output_path))

        logger.info("[API_VOICE] Voice Chat: завершён")
        return FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename="answer.wav",
            headers={
                "X-Question-Text": question[:500],
                "X-Answer-Text": answer[:500]
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API_VOICE] Ошибка voice chat: {e}", exc_info=True)
        if temp_input and temp_input.exists():
            temp_input.unlink(missing_ok=True)
        if temp_wav and temp_wav.exists():
            temp_wav.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-stt-upload")
async def test_stt_upload(
    audio: UploadFile = File(...),
    enhanced: bool = Query(True),
    denoise: bool = Query(False)
):
    """
    Детальная диагностика STT: возвращает метрики аудио и первые сегменты.
    """
    temp_input = None
    temp_wav = None
    try:
        temp_input = TEMP_AUDIO_DIR / f"test_input_{audio.filename}"
        with open(temp_input, "wb") as f:
            content = await audio.read()
            f.write(content)
        logger.info(f"[TEST-STT] Файл загружен: {temp_input} ({len(content)} bytes)")

        temp_wav = TEMP_AUDIO_DIR / f"test_converted_{audio.filename}.wav"
        audio_data, _ = librosa.load(str(temp_input), sr=16000, mono=True)

        original_stats = {
            "duration": len(audio_data) / 16000,
            "samples": len(audio_data),
            "min": float(audio_data.min()),
            "max": float(audio_data.max()),
            "mean": float(audio_data.mean()),
            "rms": float((audio_data ** 2).mean() ** 0.5)
        }

        if enhanced:
            audio_data = enhanced_preprocess(audio_data, 16000, target_amp=0.9, target_rms=0.1, denoise=denoise)
        else:
            audio_data = np.clip(librosa.util.normalize(audio_data), -1.0, 1.0)

        processed_stats = {
            "min": float(audio_data.min()),
            "max": float(audio_data.max()),
            "mean": float(audio_data.mean()),
            "rms": float((audio_data ** 2).mean() ** 0.5)
        }

        sf.write(str(temp_wav), audio_data, 16000, subtype='PCM_16')

        stt = get_stt_instance(model_size="base")
        result = stt.transcribe_file(str(temp_wav), language="ru")
        text = (result.get("text") or "").strip()

        temp_input.unlink(missing_ok=True)
        temp_wav.unlink(missing_ok=True)

        return {
            "recognized_text": text,
            "is_empty": not text,
            "audio_stats": {"original": original_stats, "processed": processed_stats},
            "stt_result": {
                "language": result.get("language"),
                "confidence": result.get("language_probability"),
                "segments_count": len(result.get("segments", [])),
                "duration": result.get("duration")
            },
            "segments": [
                {"start": seg.get("start"), "end": seg.get("end"), "text": seg.get("text")}
                for seg in result.get("segments", [])[:10]
            ]
        }
    except Exception as e:
        logger.error(f"[TEST-STT] Ошибка: {e}", exc_info=True)
        if temp_input and temp_input.exists():
            temp_input.unlink(missing_ok=True)
        if temp_wav and temp_wav.exists():
            temp_wav.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-tts")
async def test_tts():
    if not TTS_AVAILABLE:
        return {"error": "TTS недоступен"}
    try:
        text = "Здравствуйте! Система голосового взаимодействия работает."
        tts = get_tts_instance(speaker="xenia")
        output_path = TEMP_AUDIO_DIR / "test_tts.wav"
        tts.synthesize(text, output_path=str(output_path))
        return FileResponse(path=output_path, media_type="audio/wav", filename="test.wav")
    except Exception as e:
        logger.error(f"[API_VOICE] Ошибка test-tts: {e}")
        return {"error": str(e)}