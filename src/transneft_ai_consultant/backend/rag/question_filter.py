"""
Продвинутая система фильтрации нерелевантных вопросов.
Многоуровневая защита от off-topic запросов.
"""
import re
import numpy as np
import logging

from typing import Tuple, Dict
from sentence_transformers import SentenceTransformer

# ═══════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 1: Чёрные списки (моментальная блокировка)
# ═══════════════════════════════════════════════════════════════════════════

# Категории явно запрещённых тем
BLACKLIST_CATEGORIES = {
    "погода": ["погода", "температура", "дождь", "снег", "солнечно", "облачно"],
    "кулинария": ["рецепт", "готовить", "приготовить", "кулинар", "варить", "жарить"],
    "кино": ["фильм", "кино", "сериал", "актер", "актриса", "режиссер"],
    "спорт": ["футбол", "хоккей", "баскетбол", "спорт", "матч", "чемпионат"],
    "технологии": ["iphone", "android", "смартфон", "телефон", "компьютер", "ноутбук"],
    "транспорт_личный": ["автомобиль", "машина", "авто", "bmw", "mercedes", "toyota"],
    "развлечения": ["игра", "играть", "геймер", "консоль", "playstation", "xbox"],
    "здоровье": ["болезнь", "лекарство", "врач", "больница", "лечить"],
    "политика": ["президент", "правительство", "министр", "выборы", "парламент"],
}

# Токсичные/атакующие паттерны
TOXIC_PATTERNS = [
    r"игнор[иу]й",
    r"забудь",
    r"ты (тупой|глупый|идиот)",
    r"как (взломать|хакнуть)",
    r"secret[_\s]?key",
    r"пароль",
]

# ═══════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 2: Белый список (обязательные темы Транснефти)
# ═══════════════════════════════════════════════════════════════════════════

WHITELIST_KEYWORDS = {
    "компания": ["транснефть", "transneft", "пао", "организация", "предприятие", "компания"],
    "деятельность": ["нефтепровод", "нефть", "трубопровод", "магистраль", 
                     "транспортировка", "перекачка", "экспорт", "импорт"],
    "география": ["россия", "месторождение", "регион", "область", "край"],
    "бизнес": ["выручка", "прибыль", "инвестиции", "проект", "контракт"],
}

# ═══════════════════════════════════════════════════════════════════════════
# УРОВЕНЬ 3: Семантический анализ
# ═══════════════════════════════════════════════════════════════════════════

# Эталонные фразы о Транснефти (для семантического сравнения)
REFERENCE_QUERIES = [
    "Чем занимается ПАО Транснефть?",
    "Какая длина нефтепроводов Транснефти?",
    "Где находятся объекты Транснефти?",
    "Какая выручка компании Транснефть?",
    "История создания Транснефти",
    "Структура корпоративного управления в Транснефти",
    "Сколько сотрудников работает в компании?",
    "Какие инвестиционные проекты реализует Транснефть?",
    "Финансовые показатели компании за последний год",
    "Кто является акционерами ПАО Транснефть?",
    "Основные направления деятельности Транснефти",
    "Какая протяженность магистральных нефтепроводов?",
]

_semantic_model = None

def get_semantic_model():
    """Ленивая загрузка модели семантического анализа."""
    global _semantic_model
    if _semantic_model is None:
        print("Загрузка модели семантического анализа...")
        _semantic_model = SentenceTransformer('intfloat/multilingual-e5-small')
        print("✅ Модель загружена")
    return _semantic_model


# ═══════════════════════════════════════════════════════════════════════════
# ПРОВЕРКИ
# ═══════════════════════════════════════════════════════════════════════════

def check_blacklist(question: str) -> Tuple[bool, str]:
    """Проверка на чёрный список."""
    question_lower = question.lower()

    # 1. Категории
    for category, keywords in BLACKLIST_CATEGORIES.items():
        for keyword in keywords:
            if keyword in question_lower:
                return False, f"blacklist_{category}"

    # 2. Токсичные паттерны
    for pattern in TOXIC_PATTERNS:
        if re.search(pattern, question_lower):
            return False, "toxic_pattern"

    return True, ""


def check_whitelist(question: str) -> Tuple[bool, float]:
    """
    Проверка на белый список.
    Returns: (passed, score) где score = % совпадений с белым списком
    """
    question_lower = question.lower()

    total_keywords = sum(len(kws) for kws in WHITELIST_KEYWORDS.values())
    matched_keywords = 0

    for category, keywords in WHITELIST_KEYWORDS.items():
        for keyword in keywords:
            if keyword in question_lower:
                matched_keywords += 1

    score = matched_keywords / total_keywords if total_keywords > 0 else 0

    # Если вопрос длинный (>5 слов) и нет ключевых слов - блокируем
    words = question_lower.split()
    if len(words) >= 5 and score == 0:
        return False, score

    return True, score


def check_semantic_similarity(question: str, threshold: float = 0.4) -> Tuple[bool, float]:
    """
    Семантическое сравнение с эталонными вопросами о Транснефти.

    Args:
        question: Вопрос пользователя
        threshold: Минимальный порог similarity (0.4 = 40%)

    Returns:
        (passed, max_similarity)
    """
    try:
        model = get_semantic_model()

        # Эмбеддинги
        question_emb = model.encode([question])[0]
        reference_embs = model.encode(REFERENCE_QUERIES)

        # Косинусное сходство
        similarities = [
            np.dot(question_emb, ref_emb) / (np.linalg.norm(question_emb) * np.linalg.norm(ref_emb))
            for ref_emb in reference_embs
        ]

        max_similarity = max(similarities)

        passed = max_similarity >= threshold
        return passed, max_similarity

    except Exception as e:
        print(f"⚠️ Ошибка семантического анализа: {e}")
        return True, 0.0  # В случае ошибки пропускаем


# ═══════════════════════════════════════════════════════════════════════════
# ГЛАВНАЯ ФУНКЦИЯ ПРОВЕРКИ
# ═══════════════════════════════════════════════════════════════════════════

def is_question_relevant_advanced(question: str, use_semantic: bool = True) -> Tuple[bool, Dict]:

    logger = logging.getLogger(__name__)

    logger.debug(f"🔍 Проверка вопроса: {question}")

    question_lower = question.lower()

    # ═════════════════════════════════════════════════════════════
    # УРОВЕНЬ 1: IRRELEVANT (философские вопросы, мнения)
    # ═════════════════════════════════════════════════════════════

    irrelevant_patterns = [
        r'\b(европа|америка|азия)\s+(лучше|хуже)',  # "Европа лучше?"
        r'\b(лучше|хуже)\s+чем\b',  # "Лучше чем..."
        r'\bкак дела\b',  # "Как дела?"
        r'\b(привет|здравствуй)\b',  # Приветствия
        r'\bчто нового\b',  # "Что нового?"
    ]

    for pattern in irrelevant_patterns:
        if re.search(pattern, question_lower):
            return False, {
                "reason": "irrelevant_topic",
                "pattern": pattern,
                "severity": "high"
            }

    # ═════════════════════════════════════════════════════════════
    # УРОВЕНЬ 2: TOXIC PATTERNS (атаки, prompt injection)
    # ═════════════════════════════════════════════════════════════

    for pattern in TOXIC_PATTERNS:
        if re.search(pattern, question_lower):
            return False, {
                "reason": "toxic_pattern",
                "pattern": pattern,
                "severity": "critical"
            }

    # ═════════════════════════════════════════════════════════════
    # УРОВЕНЬ 3: BLACKLIST (погода, кино, спорт)
    # ═════════════════════════════════════════════════════════════

    for category, keywords in BLACKLIST_CATEGORIES.items():
        for keyword in keywords:
            if keyword in question_lower:
                return False, {
                    "reason": f"blacklist_{category}",
                    "severity": "high"
                }

    # ═════════════════════════════════════════════════════════════
    # УРОВЕНЬ 4: WHITELIST (бизнес-ключевые слова)
    # ═════════════════════════════════════════════════════════════

    business_keywords = [
        'корпоративн', 'управлени', 'структур', 'совет', 'директор',
        'акционер', 'выручк', 'прибыл', 'доход', 'финанс', 'отчёт',
        'деятельност', 'бизнес', 'компани', 'предприяти', 'транснефт',
        'нефтепровод', 'нефт', 'персонал', 'сотрудник', 'инвестици',
        'трубопровод', 'магистраль', 'перекачк', 'транспорт'
    ]

    if any(kw in question_lower for kw in business_keywords):
        return True, {
            "reason": "business_keywords",
            "severity": "low",
            "passed_all": True
        }

    # ═════════════════════════════════════════════════════════════
    # УРОВЕНЬ 5: QUESTION WORDS (вопросительные слова)
    # ═════════════════════════════════════════════════════════════

    question_words = ['что', 'как', 'где', 'когда', 'почему', 'сколько',
                      'какой', 'какая', 'какие', 'кто', 'чем', 'зачем']

    if any(question_lower.startswith(qw) for qw in question_words):
        # Есть вопросительное слово, но нет бизнес-терминов
        # Проверяем семантику
        if use_semantic:
            passed_semantic, semantic_score = check_semantic_similarity(question, threshold=0.4)

            if passed_semantic:
                return True, {
                    "reason": "semantic_match",
                    "severity": "low",
                    "semantic_score": semantic_score
                }
            else:
                return False, {
                    "reason": "low_semantic_similarity",
                    "severity": "medium",
                    "semantic_score": semantic_score
                }
        else:
            # Семантика выключена - пропускаем
            return True, {
                "reason": "valid_question_format",
                "severity": "low"
            }

    # ═════════════════════════════════════════════════════════════
    # УРОВЕНЬ 6: FINAL REJECTION (нет совпадений)
    # ═════════════════════════════════════════════════════════════

    return False, {
        "reason": "no_keywords",
        "level": "whitelist",
        "severity": "medium",
        "whitelist_score": 0.0
    }


def get_rejection_message_advanced(details: Dict) -> str:
    """Возвращает персонализированное сообщение отклонения."""

    severity = details.get("severity", "medium")
    reason = details.get("reason", "unknown")

    if severity == "high" or "toxic" in reason:
        return (
            "Прошу прощения, я не могу обработать ваш запрос. "
            "Пожалуйста, задайте вопрос о ПАО «Транснефть»."
        )

    if "blacklist" in reason:
        return (
            "Прошу прощения, я не знаю ответ на ваш вопрос. "
            "Возможно, он не связан с ПАО «Транснефть». "
            "Я специализируюсь на вопросах о нефтетранспортной компании."
        )

    if "semantic" in reason:
        score = details.get("semantic_score", 0)
        return (
            f"Прошу прощения, ваш вопрос недостаточно связан с ПАО «Транснефть» "
            f"(релевантность: {score*100:.0f}%). "
            f"Попробуйте переформулировать вопрос более конкретно."
        )

    return (
        "Прошу прощения, я не нашёл информации по вашему вопросу. "
        "Задайте вопрос о ПАО «Транснефть» ещё раз."
    )