import * as THREE from 'three';
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.158.0/examples/jsm/loaders/GLTFLoader.js';

export class AvatarController {
    constructor(containerId) {
        console.log('AvatarController: инициализация');
        this.container = document.getElementById(containerId);
        if (!this.container) throw new Error(`Container with id "${containerId}" not found`);

        this.clock = new THREE.Clock();
        this.state = 'idle';
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.model = null;
        this.mixer = null;
        this.isLoaded = false;
        this.animations = {};
        this.currentAction = null;
        this.lights = {};
        this.gltfAnimations = null;
    }

    async init() {
        console.log('AvatarController.init() запущен');

        while (this.container.firstChild) this.container.removeChild(this.container.firstChild);

        // Сцена и камера
        this.scene = new THREE.Scene();
        this.scene.background = null;

        const width = this.container.clientWidth || 400;
        const height = this.container.clientHeight || 600;
        this.camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
        this.camera.position.set(0, 2.7, 2.2);
        this.camera.lookAt(0, 2, 0);
        this.camera.updateProjectionMatrix();
        console.log('📸 Камера зафиксирована');

        // Рендерер
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance'
        });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;
        this.container.appendChild(this.renderer.domElement);

        // Свет
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
        this.scene.add(ambientLight);
        const mainLight = new THREE.DirectionalLight(0xffffff, 1.0);
        mainLight.position.set(3, 4, 3);
        this.scene.add(mainLight);

        // Загрузка модели
        await this.loadModel();

        // Рендеринг
        console.log('🚀 Запуск рендеринга');
        this.renderer.setAnimationLoop(() => this.animate());

        // Анимация
        this.playAnimation('greeting');
    }

    async loadModel() {
        const loader = new GLTFLoader();
        return new Promise((resolve) => {
            loader.load(
                '/static/assets/models/Bynary.glb',
                (gltf) => {
                    console.log('✅ Модель загружена успешно');
                    this.gltfAnimations = gltf.animations;
                    this.model = gltf.scene;
                    this.model.position.set(0, -0.8, -2.3);
                    this.model.scale.set(1.9, 1.9, 1.9);

                    this.scene.add(this.model);
                    this.mixer = new THREE.AnimationMixer(this.model);
                    this.loadNLAAnimations();
                    this.isLoaded = true;

                    // 👁️ Запускаем моргание через материал
                    this.startTextureBlinking();

                    resolve();
                },
                undefined,
                (error) => {
                    console.error('❌ Ошибка загрузки модели:', error);
                    resolve();
                }
            );
        });
    }

    loadNLAAnimations() {
        console.log('\n🎬 ========== ЗАГРУЗКА NLA АНИМАЦИЙ ==========');
        if (!this.gltfAnimations || this.gltfAnimations.length === 0) {
            console.error('❌ Анимации не найдены в GLB!');
            return;
        }

        const wanted = {
            greeting: ['greet', 'hello'],
            idle: ['idle'],
            engagement: ['engage', 'offer', 'ask'],
            farewell: ['fare', 'bye', 'goodbye']
        };

        const found = {};
        this.gltfAnimations.forEach(clip => {
            const lname = clip.name.toLowerCase();
            for (const [short, keys] of Object.entries(wanted)) {
                if (found[short]) continue;
                for (const k of keys) {
                    if (lname.includes(k)) {
                        this.animations[short] = clip;
                        found[short] = clip.name;
                        console.log(`✅ ${short} → "${clip.name}" (${clip.duration.toFixed(2)}s)`);
                        break;
                    }
                }
            }
        });

        console.log('✅ Загружено анимаций:', Object.keys(this.animations).join(', '));
    }

    /**
     * 👁️ Моргание через затемнение материала глаз
     */
    startTextureBlinking() {
        const eyes = [];

        // Находим меши глаз
        this.model.traverse((child) => {
            if (child.isMesh && /eye/i.test(child.name)) {
                eyes.push(child);
                console.log('👁️ Найден глаз:', child.name);
            }
        });

        if (eyes.length === 0) {
            console.warn('⚠️ Не найдены глаза в модели для моргания.');
            return;
        }

        console.log('✅ Моргаем глазами через материал.');

        // Сохраняем оригинальные цвета
        eyes.forEach(eye => {
            if (!eye.userData.originalColor)
                eye.userData.originalColor = eye.material.color.clone();
        });

        const blink = () => {
            // Затемняем
            eyes.forEach(eye => {
                if (eye.material && eye.material.color) {
                    eye.material.color.multiplyScalar(0.1);
                }
            });

            // Возвращаем цвет
            setTimeout(() => {
                eyes.forEach(eye => {
                    if (eye.material && eye.material.color) {
                        eye.material.color.copy(eye.userData.originalColor);
                    }
                });
            }, 150 + Math.random() * 100);

            // Следующее моргание через 2–4 с
            setTimeout(blink, 2000 + Math.random() * 2000);
        };

        setTimeout(blink, 1000 + Math.random() * 500);
    }

    playAnimation(name) {
    if (!this.mixer || !this.animations[name]) {
        console.warn(`⚠️ Анимация "${name}" не найдена.`);
        return;
    }

    const oldAction = this.currentAction;
    const newAction = this.mixer.clipAction(this.animations[name]);

    if (oldAction === newAction && newAction.isRunning()) {
        return; // Уже играет то, что нужно, выходим
    }

    // --- Настройка нового действия ---
    newAction.reset();
    if (name === 'idle') {
        newAction.setLoop(THREE.LoopRepeat);
    } else {
        newAction.setLoop(THREE.LoopOnce);
        newAction.clampWhenFinished = true; // "Заморозить" позу в конце
    }

    const fadeDuration = 0.2; // Длительность плавного перехода (в секундах)

    if (oldAction) {
        newAction.play(); // Запускаем новое действие
        oldAction.crossFadeTo(newAction, fadeDuration, false);
    } else {
        // Если это первая анимация, просто плавно включаем ее
        newAction.fadeIn(fadeDuration).play();
    }

    this.currentAction = newAction;

    if (this._idleTimeout) {
        clearTimeout(this._idleTimeout);
        this._idleTimeout = null;
    }

    // Если новая анимация одноразовая, планируем возврат в idle
    if (newAction.loop === THREE.LoopOnce) {
        const clipDuration = newAction.getClip().duration;

        const delay = (clipDuration - fadeDuration) * 1000;

        if (delay > 0) {
            this._idleTimeout = setTimeout(() => {
                this.playAnimation('idle');
            }, delay);
        } else {
            // Если анимация слишком короткая, переключаемся сразу после ее завершения
             this.mixer.addEventListener('finished', (e) => {
                if(e.action === newAction) this.playAnimation('idle');
             }, { once: true }); // { once: true } автоматически удалит слушатель после срабатывания
        }
    }
}

    animate() {
        if (!this.isLoaded) return;
        const delta = this.clock.getDelta();
        if (this.mixer) this.mixer.update(delta);
        this.renderer.render(this.scene, this.camera);
    }

    resize() {
        if (!this.container || !this.renderer || !this.camera) return;
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        if (width > 0 && height > 0) {
            this.camera.aspect = width / height;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(width, height);
        }
    }
}
