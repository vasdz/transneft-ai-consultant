export class ChatService {
    constructor(messagesContainerId = 'messages-container', userInputId = 'text-input', sendButtonId = 'send-btn', avatarController = null, callbacks = {}) {
        console.log('[ChatService] Конструктор вызван');
        this.messagesContainer = document.getElementById(messagesContainerId);
        this.userInput = document.getElementById(userInputId);
        this.sendButton = document.getElementById(sendButtonId);
        this.avatarController = avatarController;
        this.onAssistantMessage = callbacks.onAssistantMessage || null;

        this.apiUrl = document.querySelector('meta[name="api-base"]')?.content || 'http://127.0.0.1:8000';
        if (this.apiUrl.endsWith('/')) {
            this.apiUrl = this.apiUrl.slice(0, -1);
        }

        this.isProcessing = false;
        this.messages = [];
        this.currentAudio = null;
        console.log('[ChatService] apiUrl:', this.apiUrl);
    }



    init() {
        console.log('=== ChatService.init() запущен ===');

        if (!this.messagesContainer || !this.userInput || !this.sendButton) {
            console.error('ChatService: необходимые DOM элементы не найдены');
            return;
        }

        console.log('ChatService: элементы чата найдены, API URL:', this.apiUrl);

        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    async sendMessage() {
        const message = this.userInput.value.trim();
        if (!message || this.isProcessing) return;

        this.isProcessing = true;
        this.sendButton.disabled = true;
        this.userInput.value = '';

        this.addMessageToChat('user', message);
        this.showTypingIndicator();
        try {
            const response = await this.callChatAPI(message);
            this.removeTypingIndicator();

            const answer = response?.answer || response?.text || 'Нет ответа';
const audioUrl = response?.audio_url || null;

// Получаем источники из ответа API
const sources = response?.retrieved_contexts?.map((ctx, idx) => ({
    context: ctx,
    similarity: response?.scores?.[idx] || 0
})) || [];

// Передаем источники
const messageData = {
    audioUrl: audioUrl,
    sources: sources
};

this.addMessageToChat('assistant', answer, messageData);

            console.log('[sendMessage] Получен ответ:', answer.substring(0, 50));
            console.log('[sendMessage] audioUrl:', audioUrl);

            //this.addMessageToChat('assistant', answer, audioUrl);

        } catch (error) {
            console.error('ChatService.sendMessage ошибка:', error);
            this.removeTypingIndicator();
            this.addMessageToChat('system', 'Произошла ошибка при обращении к серверу.');
        } finally {
            this.isProcessing = false;
            this.sendButton.disabled = false;
            this.userInput.focus();
        }
    }

    async callChatAPI(message) {
        const url = `${this.apiUrl}/api/chat`;
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: message })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    }

    addMessageToChat(role, content, messageData = null) {
        console.log('[addMessageToChat] ===== НАЧАЛО =====');
        console.log('[addMessageToChat] role:', role);
        console.log('[addMessageToChat] content:', content.substring(0, 100));
        console.log('[addMessageToChat] messageData:', messageData);
        console.log('[addMessageToChat] this.apiUrl:', this.apiUrl);

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? '👤' : '🤖';

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.style.position = 'relative';

        if (role === 'assistant' || role === 'system') {
    console.log('[addMessageToChat] Создаем сообщение ассистента');

    // Используем новую функцию для отображения с источниками
    if (typeof window.displayAnswerWithSources === 'function' && messageData && messageData.sources && messageData.sources.length > 0) {
        const advancedMessage = displayAnswerWithSources(content, messageData.sources);
        this.messagesContainer.appendChild(advancedMessage);
        this.scrollToBottom();
        this.messages.push({ role, content, messageData, timestamp: Date.now() });
        return; // Выходим
    }

    // Иначе обычное отображение
    const textP = document.createElement('p');
    textP.textContent = content;

            messageContent.appendChild(textP);
            console.log('[addMessageToChat] Текст добавлен');

            // КНОПКА АУДИО
            console.log('[addMessageToChat] Создаем кнопку аудио...');
            const playBtn = document.createElement('button');
            playBtn.className = 'play-audio-btn';
            playBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`;
            playBtn.title = 'Прослушать ответ';

            // ИНЛАЙН СТИЛИ для гарантии видимости
            playBtn.style.cssText = `
                position: absolute;
                bottom: 5px;
                right: 5px;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                border: none;
                background: #0056A6;
                color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
            `;

            console.log('[addMessageToChat] Кнопка создана, добавляем обработчик...');

            // Сохраняем контекст
            const savedApiUrl = this.apiUrl;
            const savedContent = content;

            // ТЕСТ: Добавляем onclick прямо в HTML
            playBtn.setAttribute('data-text', content.substring(0, 50));
            const audioUrl = messageData?.audioUrl || null;  // ✅ Определяем ДО использования
            playBtn.setAttribute('data-audiourl', audioUrl || 'null');

            playBtn.onclick = async function(event) {
    console.log('[TTS] Кнопка нажата!');

    if (this.currentAudio && !this.currentAudio.paused) {
        this.currentAudio.pause();
    }

    try {
        playBtn.disabled = true;
        playBtn.style.opacity = '0.5';

        // ❌ УДАЛИ: if (audioUrl) { ... }
        // ✅ ВСЕГДА используй TTS (audioUrl почти всегда null)

        console.log('[TTS] Генерируем аудио через TTS...');
        const ttsUrl = `${this.apiUrl}/api/voice/tts?text=${encodeURIComponent(content)}&speaker=xenia&return_file=true`;

        const response = await fetch(ttsUrl, {
            method: 'POST',
            headers: {'Accept': 'audio/wav'}
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('[TTS] Ошибка:', errorText);
            throw new Error(`HTTP ${response.status}`);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        this.currentAudio = new Audio(url);
        this.currentAudio.onended = () => {
            console.log('[TTS] Воспроизведение завершено');
            URL.revokeObjectURL(url);
            playBtn.disabled = false;
            playBtn.style.opacity = '1';
            this.currentAudio = null;
        };

        await this.currentAudio.play();
        console.log('[TTS] Аудио воспроизводится');

    } catch (error) {
        console.error('[TTS] Ошибка:', error);
        alert(`Ошибка озвучивания: ${error.message}`);
        playBtn.disabled = false;
        playBtn.style.opacity = '1';
    }
}.bind(this);

            console.log('[addMessageToChat] Обработчик добавлен');
            messageContent.appendChild(playBtn);
            console.log('[addMessageToChat] Кнопка добавлена в DOM');

        } else {
            const textP = document.createElement('p');
            textP.textContent = content;
            messageContent.appendChild(textP);
        }

        const time = document.createElement('span');
        time.className = 'message-time';
        time.textContent = new Date().toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        });
        messageContent.appendChild(time);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();

        this.messages.push({ role, content, messageData, timestamp: Date.now() });

        console.log('[addMessageToChat] ===== КОНЕЦ =====');
        console.log('[addMessageToChat] Сообщение добавлено в DOM');

        // ТЕСТ: Проверяем что кнопка реально в DOM
        if (role === 'assistant' || role === 'system') {
            setTimeout(() => {
                const buttons = document.querySelectorAll('.play-audio-btn');
                console.log('[TEST] Найдено кнопок в DOM:', buttons.length);
                buttons.forEach((btn, idx) => {
                    console.log(`[TEST] Кнопка ${idx}:`, btn, 'onclick:', typeof btn.onclick);
                });
            }, 100);
        }
    }



    showTypingIndicator() {
        if (document.getElementById('typing-indicator')) return;

        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'typing-indicator';
        typingDiv.style.cssText = 'display: flex; gap: 5px; padding: 15px 20px;';

        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dot.style.cssText = 'width: 8px; height: 8px; border-radius: 50%; background: #0056A6; animation: typing 1.4s infinite;';
            dot.style.animationDelay = `${i * 0.2}s`;
            typingDiv.appendChild(dot);
        }

        this.messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    getMessageHistory() {
        return this.messages;
    }

    clearHistory() {
        this.messages = [];
        this.messagesContainer.innerHTML = '';
    }
}

function displayAnswerWithSources(answer, sources) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';

    // Аватар
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🤖';
    messageDiv.appendChild(avatar);

    // Контент
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.style.position = 'relative';  // ✅ ДОБАВЬ для абсолютного позиционирования кнопки

    // Основной ответ
    const answerText = document.createElement('p');
    answerText.innerHTML = answer;
    messageContent.appendChild(answerText);

    // ✅ ДОБАВЬ КНОПКУ TTS ЗДЕСЬ (ДО источников)
    console.log('[displayAnswerWithSources] Создаем кнопку TTS...');
    const playBtn = document.createElement('button');
    playBtn.className = 'play-audio-btn';
    playBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`;
    playBtn.title = 'Прослушать ответ';

    playBtn.style.cssText = `
        position: absolute;
        bottom: 5px;
        right: 5px;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        border: none;
        background: #0056A6;
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    // ✅ ОБРАБОТЧИК КЛИКА (используй window.chatService для доступа к apiUrl)
    playBtn.onclick = async function(event) {
        console.log('[TTS] Кнопка нажата в displayAnswerWithSources!');

        try {
            playBtn.disabled = true;
            playBtn.style.opacity = '0.5';

            // ✅ Получаем apiUrl из глобального chatService
            const apiUrl = window.chatServiceInstance?.apiUrl || 'http://127.0.0.1:8000';
            console.log('[TTS] Генерируем аудио через TTS...');

            const ttsUrl = `${apiUrl}/api/voice/tts?text=${encodeURIComponent(answer)}&speaker=xenia&return_file=true`;

            const response = await fetch(ttsUrl, {
                method: 'POST',
                headers: {'Accept': 'audio/wav'}
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[TTS] Ошибка:', errorText);
                throw new Error(`HTTP ${response.status}`);
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);

            const audio = new Audio(url);
            audio.onended = () => {
                console.log('[TTS] Воспроизведение завершено');
                URL.revokeObjectURL(url);
                playBtn.disabled = false;
                playBtn.style.opacity = '1';
            };

            await audio.play();
            console.log('[TTS] Аудио воспроизводится');

        } catch (error) {
            console.error('[TTS] Ошибка:', error);
            alert(`Ошибка озвучивания: ${error.message}`);
            playBtn.disabled = false;
            playBtn.style.opacity = '1';
        }
    };

    messageContent.appendChild(playBtn);
    console.log('[displayAnswerWithSources] Кнопка TTS добавлена');
    // ✅ КОНЕЦ БЛОКА TTS

    // Источники (ниже кнопки)
    if (sources && sources.length > 0) {
        const sourcesContainer = document.createElement('div');
        sourcesContainer.className = 'sources-container';
        sourcesContainer.style.cssText = `
            margin-top: 15px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 8px;
            border-left: 3px solid #0056A6;
        `;

        const sourcesTitle = document.createElement('h4');
        sourcesTitle.textContent = '📚 Источники:';
        sourcesTitle.style.cssText = 'margin: 0 0 10px 0; color: #0056A6; font-size: 14px;';
        sourcesContainer.appendChild(sourcesTitle);

        sources.forEach((src, idx) => {
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'source-item';
            sourceDiv.style.cssText = `
                margin-bottom: 10px;
                padding: 8px;
                background: white;
                border-radius: 5px;
                position: relative;
            `;

            const sourceNumber = document.createElement('span');
            sourceNumber.textContent = `[${idx + 1}]`;
            sourceNumber.style.cssText = 'font-weight: bold; color: #0056A6; margin-right: 8px;';

            const sourceText = document.createElement('span');
            sourceText.textContent = src.context.substring(0, 100) + '...';
            sourceText.style.cssText = 'font-size: 12px; color: #666; display: inline-block; max-width: 70%;';

            const relevanceContainer = document.createElement('div');
            relevanceContainer.style.cssText = 'width: 100%; height: 4px; background: #e0e0e0; border-radius: 2px; margin-top: 5px; overflow: hidden;';

            const relevanceBar = document.createElement('div');
            const similarity = src.similarity || src.score || 0;
            relevanceBar.style.cssText = `width: ${similarity * 100}%; height: 100%; background: linear-gradient(90deg, #4CAF50, #8BC34A);`;
            relevanceContainer.appendChild(relevanceBar);

            const relevanceScore = document.createElement('span');
            relevanceScore.textContent = `${(similarity * 100).toFixed(1)}%`;
            relevanceScore.style.cssText = 'position: absolute; right: 8px; top: 8px; font-size: 11px; color: #4CAF50; font-weight: bold;';

            sourceDiv.appendChild(sourceNumber);
            sourceDiv.appendChild(sourceText);
            sourceDiv.appendChild(relevanceContainer);
            sourceDiv.appendChild(relevanceScore);

            sourcesContainer.appendChild(sourceDiv);
        });

        messageContent.appendChild(sourcesContainer);
    }

    // Время
    const time = document.createElement('span');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    messageContent.appendChild(time);

    messageDiv.appendChild(messageContent);
    return messageDiv;
}

// Делаем функцию глобально доступной
window.displayAnswerWithSources = displayAnswerWithSources;