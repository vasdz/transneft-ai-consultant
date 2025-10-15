import { AvatarController } from './avatar.js';
import { ChatService } from './chat.js';

console.log('🚀 Инициализация Транснефть AI Консультант');

let avatar = null;
let chatService = null;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Инициализация аватара
        avatar = new AvatarController('avatar-container');
        await avatar.init();
        console.log('✅ Аватар инициализирован');

        // Делаем avatar глобальным для animation-sync.js
        window.avatarController = avatar;

        // Инициализация чата
        const chatService = new ChatService(
        'messages-container',
        'text-input',
        'send-btn',
        avatarController,
        { onAssistantMessage: (msg) => console.log('[MAIN] Assistant:', msg) }
        );
        window.chatServiceInstance = chatService;
        chatService.init();
        console.log('✅ ChatService инициализирован');

        // ========== ГОЛОСОВОЙ ВВОД ==========
        const voiceBtn = document.getElementById('voice-btn');
        const voiceStatus = document.getElementById('voice-status');
        const voiceTimer = document.getElementById('voice-timer');

        if (voiceBtn && window.voiceInterface) {
            let recordingStartTime = null;
            let timerInterval = null;

            voiceBtn.addEventListener('click', async () => {
                if (!window.voiceInterface.isRecording) {
                    // ========== НАЧАЛО ЗАПИСИ ==========
                    try {
                        await window.voiceInterface.startRecording();
                        voiceBtn.classList.add('recording');
                        if (voiceStatus) voiceStatus.textContent = 'Говорите...';

                        // Запускаем таймер
                        recordingStartTime = Date.now();
                        timerInterval = setInterval(() => {
                            const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
                            const minutes = Math.floor(elapsed / 60);
                            const seconds = elapsed % 60;
                            if (voiceTimer) {
                                voiceTimer.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                            }
                        }, 1000);

                        console.log('🎤 Запись голоса начата');
                    } catch (error) {
                        console.error('❌ Ошибка начала записи:', error);
                        alert('Не удалось начать запись. Проверьте разрешение на доступ к микрофону.');
                    }
                } else {
                    // ========== ОСТАНОВКА ЗАПИСИ ==========
                    try {
                        const audioBlob = await window.voiceInterface.stopRecording();
                        voiceBtn.classList.remove('recording');
                        if (voiceStatus) voiceStatus.textContent = 'Обработка...';

                        // Останавливаем таймер
                        clearInterval(timerInterval);
                        if (voiceTimer) voiceTimer.textContent = '0:00';

                        console.log('🛑 Запись остановлена, обрабатываем...');

                        // Отправляем на распознавание
                        const recognizedText = await window.voiceInterface.speechToText(audioBlob);

                        if (recognizedText && recognizedText.trim()) {
                            // Вставляем текст в поле ввода
                            const textInput = document.getElementById('text-input');
                            if (textInput) {
                                textInput.value = recognizedText;
                                console.log('📝 Текст распознан:', recognizedText);
                            }

                            // Автоматически отправляем сообщение
                            if (chatService) {
                                await chatService.sendMessage();
                            }
                        } else {
                            alert('Не удалось распознать речь. Попробуйте снова.');
                        }

                        if (voiceStatus) voiceStatus.textContent = '';
                    } catch (error) {
                        console.error('❌ Ошибка обработки записи:', error);
                        alert('Ошибка при обработке голоса: ' + error.message);
                        voiceBtn.classList.remove('recording');
                        if (voiceStatus) voiceStatus.textContent = '';
                        if (voiceTimer) voiceTimer.textContent = '0:00';
                        clearInterval(timerInterval);
                    }
                }
            });

            console.log('✅ Голосовой ввод подключен');
        } else {
            console.warn('⚠️ Кнопка микрофона или VoiceInterface не найдены');
        }

        // ========== КНОПКА ПРИВЕТСТВИЯ ==========
        const welcomeBtn = document.getElementById('welcome-audio-btn');
        if (welcomeBtn) {
            const welcomeMessageElement = welcomeBtn.closest('.message-content')?.querySelector('p');
            const welcomeText = welcomeMessageElement ? welcomeMessageElement.textContent.trim() : '';
            const apiUrl = chatService.apiUrl;

            if (welcomeText && apiUrl) {
                welcomeBtn.addEventListener('click', async () => {
                    console.log('🔊 Клик по кнопке приветствия. Текст:', welcomeText);
                    try {
                        welcomeBtn.disabled = true;
                        welcomeBtn.style.opacity = '0.5';
                        const ttsUrl = `${apiUrl}/api/voice/tts?text=${encodeURIComponent(welcomeText)}&speaker=xenia&return_file=true`;
                        const response = await fetch(ttsUrl, {
                            method: 'POST',
                            headers: { 'Accept': 'audio/wav' }
                        });
                        if (!response.ok) throw new Error(`Ошибка TTS: ${response.status}`);

                        const blob = await response.blob();
                        const audioUrl = URL.createObjectURL(blob);
                        const audio = new Audio(audioUrl);

                        audio.onended = () => {
                            URL.revokeObjectURL(audioUrl);
                            welcomeBtn.disabled = false;
                            welcomeBtn.style.opacity = '1';
                        };
                        await audio.play();

                    } catch (error) {
                        console.error('❌ Ошибка озвучивания приветствия:', error);
                        alert('Не удалось озвучить приветствие. ' + error.message);
                        welcomeBtn.disabled = false;
                        welcomeBtn.style.opacity = '1';
                    }
                });
                console.log('✅ Обработчик для кнопки приветствия успешно добавлен.');
            }
        }

        // Обработчик изменения размера окна
        window.addEventListener('resize', () => {
            if (avatar) avatar.resize();
        });

        console.log('✅ Инициализация завершена');
    } catch (error) {
        console.error('❌ Ошибка инициализации:', error);
    }
});
