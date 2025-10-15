class VoiceInterface {
    constructor(apiBaseUrl = 'http://localhost:8000/api/voice') {
        this.apiBaseUrl = apiBaseUrl;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
    }

    /**
     * Запрос разрешения на использование микрофона
     */
    async requestMicrophoneAccess() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                }
            });
            console.log('✅ Доступ к микрофону получен');
            return this.stream;
        } catch (error) {
            console.error('❌ Ошибка доступа к микрофону:', error);
            alert('Необходим доступ к микрофону для голосового ввода');
            throw error;
        }
    }
    async startRecording() {
        if (this.isRecording) {
            console.warn('Запись уже идет');
            return;
        }

        const stream = await this.requestMicrophoneAccess();

        // Проверяем поддержку MIME типов
        const mimeType = MediaRecorder.isTypeSupported('audio/webm')
            ? 'audio/webm'
            : 'audio/ogg';

        this.mediaRecorder = new MediaRecorder(stream, { mimeType });
        this.audioChunks = [];

        this.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                this.audioChunks.push(event.data);
            }
        };

        this.mediaRecorder.start();
        this.isRecording = true;

        console.log(`🎤 Запись начата (${mimeType})`);
    }

    /**
     * Остановить запись и получить Blob
     */
    async stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) {
            console.warn('Запись не была начата');
            return null;
        }

        return new Promise((resolve, reject) => {
            this.mediaRecorder.onstop = () => {
                const mimeType = this.mediaRecorder.mimeType;
                const audioBlob = new Blob(this.audioChunks, { type: mimeType });
                this.isRecording = false;

                // Останавливаем все треки
                if (this.stream) {
                    this.stream.getTracks().forEach(track => track.stop());
                }

                console.log(`🛑 Запись остановлена: ${audioBlob.size} bytes`);

                if (audioBlob.size === 0) {
                    reject(new Error('Запись пуста'));
                } else {
                    resolve(audioBlob);
                }
            };

            this.mediaRecorder.stop();
        });
    }

    /**
     * Распознать речь из аудио (STT)
     */
    async speechToText(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');

        try {
            const response = await fetch(`${this.apiBaseUrl}/stt`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `STT failed: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('📝 Распознанный текст:', result.text);
            return result.text;
        } catch (error) {
            console.error('❌ Ошибка STT:', error);
            throw error;
        }
    }

    /**
     * Синтезировать речь из текста (TTS)
     */
    async textToSpeech(text, speaker = 'xenia') {
        try {
            const params = new URLSearchParams({
                text: text,
                speaker: speaker,
                return_file: 'false'
            });

            const response = await fetch(`${this.apiBaseUrl}/tts?${params}`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`TTS failed: ${response.statusText}`);
            }

            const result = await response.json();

            // Декодируем base64 в audio
            const audioData = atob(result.audio_base64);
            const arrayBuffer = new ArrayBuffer(audioData.length);
            const view = new Uint8Array(arrayBuffer);

            for (let i = 0; i < audioData.length; i++) {
                view[i] = audioData.charCodeAt(i);
            }

            const audioBlob = new Blob([arrayBuffer], { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);

            console.log('🔊 Аудио синтезировано');
            return audioUrl;
        } catch (error) {
            console.error('❌ Ошибка TTS:', error);
            throw error;
        }
    }

    /**
     * Полный цикл: голосовой вопрос -> голосовой ответ
     */
    async voiceChat(audioBlob, speaker = 'xenia') {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'question.wav');

        try {
            const params = new URLSearchParams({ speaker });
            const response = await fetch(`${this.apiBaseUrl}/voice-chat?${params}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `Voice chat failed: ${response.statusText}`);
            }

            // Получаем текстовые версии из заголовков
            const question = decodeURIComponent(
                response.headers.get('X-Question-Text') || 'Не удалось распознать'
            );
            const answer = decodeURIComponent(
                response.headers.get('X-Answer-Text') || ''
            );

            // Получаем аудио ответ
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);

            console.log('💬 Голосовой чат завершен');

            return {
                question,
                answer,
                audioUrl
            };
        } catch (error) {
            console.error('❌ Ошибка voice chat:', error);
            throw error;
        }
    }

    /**
     * Воспроизвести аудио
     */
    playAudio(audioUrl) {
        const audio = new Audio(audioUrl);
        audio.play();
        return audio;
    }


}

window.VoiceInterface = VoiceInterface;

// Создаем глобальный экземпляр для использования во всем приложении
const voiceInterface = new VoiceInterface();
window.voiceInterface = voiceInterface;

console.log('✅ VoiceInterface доступен глобально');
