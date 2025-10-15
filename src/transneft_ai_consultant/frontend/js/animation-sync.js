console.log('🎯 Advanced Animation-Sync модуль загружен');

class AvatarAnimationManager {
    constructor() {
        this.avatar = null;
        this.isInitialized = false;
        this.currentState = 'idle';
        this.idleReturnTimeout = null;

        this.animationPriorities = {
            'idle': 1,
            'engagement': 2,
            'greeting': 6,
            'farewell': 5
        };
    }

    async init() {
        console.log('[🎯 AnimationManager] Инициализация...');
        let attempts = 0;
        while (!window.avatarController && attempts < 30) {
            await new Promise(resolve => setTimeout(resolve, 500));
            attempts++;
        }
        if (!window.avatarController) {
            console.error('[❌ AnimationManager] AvatarController не найден');
            return;
        }
        this.avatar = window.avatarController;
        this.isInitialized = true;
        console.log('[✅ AnimationManager] Инициализирован успешно');
        this.setupEventListeners();
    }

    setupEventListeners() {
        const textInput = document.getElementById('text-input');
        const messagesContainer = document.getElementById('messages-container');

        if (textInput) {
            textInput.addEventListener('focus', () => {
                console.log('[🎯] Пользователь сфокусировался → engagement');
                this.clearIdleReturn();
                this.playAnimationWithPriority('engagement');
            });
            
            textInput.addEventListener('input', () => {
                this.clearIdleReturn();
            });
        }

        if (messagesContainer) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    if (mutation.addedNodes.length) {
                        mutation.addedNodes.forEach(node => {
                            if (node.nodeType === 1 && node.classList.contains('message')) {
                                this.handleNewMessage(node);
                            }
                        });
                    }
                });
            });
            observer.observe(messagesContainer, { childList: true, subtree: true });
            console.log('[✅] MutationObserver активирован');
        }

        this.setupGlobalEvents();
    }

    handleNewMessage(messageNode) {
        if (messageNode.classList.contains('user') || (messageNode.classList.contains('assistant') && !messageNode.classList.contains('welcome-message'))) {
            console.log('[🎯] Новое сообщение → engagement');
            this.playAnimationWithPriority('engagement');
            this.scheduleIdleReturn(5000);
        }
    }

    setupGlobalEvents() {
        // Таймер для глобальной неактивности
        let inactivityTimer;
        const resetInactivityTimer = () => {
            clearTimeout(inactivityTimer);
            inactivityTimer = setTimeout(() => {
                if (this.currentState !== 'engagement') {
                    console.log('[🎯] Долгая неактивность → idle');
                    this.playAnimationWithPriority('idle');
                }
            }, 20000);
        };
        document.addEventListener('mousemove', resetInactivityTimer);
        document.addEventListener('keypress', resetInactivityTimer);
        document.addEventListener('click', resetInactivityTimer);
        resetInactivityTimer();

        let farewellTriggered = false;

        document.addEventListener('mouseout', (e) => {
            // Проверяем, что курсор ушел за пределы страницы вверх
            if (!farewellTriggered && e.clientY <= 0) {
                console.log('[🎯] Пользователь движется к закрытию окна → farewell');
                farewellTriggered = true;
                this.playAnimationWithPriority('farewell');
                
                // Сбрасываем флаг через 3 секунды, если пользователь передумал
                setTimeout(() => {
                    farewellTriggered = false;
                }, 3000);
            }
        });

        // Также сохраняем обработчик beforeunload для реального закрытия
        window.addEventListener('beforeunload', () => {
            console.log('[🎯] Закрытие страницы → farewell');
            this.playAnimationWithPriority('farewell');
        });
    }

    playAnimationWithPriority(animationName) {
        if (!this.isInitialized || !this.avatar || !this.avatar.isLoaded) return;

        const newPriority = this.animationPriorities[animationName] || 0;
        const currentPriority = this.animationPriorities[this.currentState] || 0;

        if (newPriority < currentPriority && this.currentState !== 'idle') {
            console.log(`[🎯] Анимация "${animationName}" отклонена: низкий приоритет (${newPriority} < ${currentPriority})`);
            return;
        }

        this.clearIdleReturn();

        console.log(`[🎯] ▶️ Воспроизведение: ${this.currentState} → ${animationName}`);
        try {
            this.avatar.playAnimation(animationName);
            this.currentState = animationName;
        } catch (error) {
            console.error(`[❌] Ошибка воспроизведения анимации: ${animationName}`, error);
            if (animationName !== 'idle') this.playAnimationWithPriority('idle');
        }
    }
    
    scheduleIdleReturn(delay = 3000) {
        this.clearIdleReturn();
        this.idleReturnTimeout = setTimeout(() => {
            console.log(`[🎯] Возврат в idle после ${delay}ms неактивности.`);
            this.playAnimationWithPriority('idle');
        }, delay);
    }

    clearIdleReturn() {
        if (this.idleReturnTimeout) {
            clearTimeout(this.idleReturnTimeout);
            this.idleReturnTimeout = null;
        }
    }
}

const animationManager = new AvatarAnimationManager();
window.avatarAnimationManager = animationManager;
window.addEventListener('load', () => setTimeout(() => animationManager.init(), 1000));
