import razdel
import pymorphy2
from rouge_score import rouge_scorer, scoring

_morph_instance = None

def get_morph():
    """Ленивая инициализация pymorphy2 с обработкой ошибок."""
    global _morph_instance
    if _morph_instance is None:
        try:
            import inspect
            # Патч для Python 3.11+
            if not hasattr(inspect, 'getargspec'):
                inspect.getargspec = inspect.getfullargspec
            _morph_instance = pymorphy2.MorphAnalyzer()
        except Exception as e:
            print(f"⚠️ pymorphy2 недоступен: {e}. Используется простая токенизация.")
            _morph_instance = None
    return _morph_instance

def normalize_word(word):
    """Нормализует слово к начальной форме (лемме)"""
    morph = get_morph()
    if morph:
        parsed_word = morph.parse(word)[0]
        return parsed_word.normal_form
    else:
        # Фоллбэк: просто lowercase
        return word.lower()


def tokenize_text_ru(text):
    """Разбивает текст на слова с учетом особенностей русского языка"""
    # Используем библиотеку razdel для корректного разбиения русского текста
    words = [token.text for token in razdel.tokenize(text)]
    return words


def tokenize_sentences_ru(text):
    """Разбивает текст на предложения с учетом особенностей русского языка"""
    # Используем библиотеку razdel для корректного разбиения русского текста на предложения
    sentences = [sentence.text for sentence in razdel.sentenize(text)]
    return sentences


class RougeRuScorer(rouge_scorer.RougeScorer):
    """Адаптированный скорер ROUGE для русского языка"""

    def __init__(self, rouge_types, use_stemmer=True):
        """Инициализация с сохранением use_stemmer."""
        super().__init__(rouge_types, use_stemmer=False)  # Базовый stemmer не нужен
        self.use_stemmer = use_stemmer  # Сохраняем наш флаг

    def _preprocess_summary_ru(self, summary, use_stemmer=True):
        """Предобрабатывает текст для оценки ROUGE с учетом русского языка"""
        if use_stemmer:
            # Токенизируем и нормализуем каждое слово
            tokens = tokenize_text_ru(summary.lower())
            preprocessed_tokens = [normalize_word(token) for token in tokens]
            return preprocessed_tokens
        else:
            return tokenize_text_ru(summary.lower())

    def score_ru(self, target, prediction):
        """Рассчитывает метрики ROUGE для русского языка"""
        scores = {}
        for rouge_type in self.rouge_types:
            if rouge_type == 'rougeL':
                # Для ROUGE-L используем наши токены с учетом русской морфологии
                target_tokens = self._preprocess_summary_ru(target, self.use_stemmer)
                prediction_tokens = self._preprocess_summary_ru(prediction, self.use_stemmer)
                scores[rouge_type] = self._score_lcs(target_tokens, prediction_tokens)
            elif rouge_type == 'rougeLsum':
                # Для ROUGE-Lsum разбиваем на предложения
                target_sents = tokenize_sentences_ru(target)
                prediction_sents = tokenize_sentences_ru(prediction)

                target_tokens_list = [self._preprocess_summary_ru(s, self.use_stemmer) for s in target_sents]
                prediction_tokens_list = [self._preprocess_summary_ru(s, self.use_stemmer) for s in prediction_sents]
                scores[rouge_type] = self._score_lcs_merge(target_tokens_list, prediction_tokens_list)
            else:
                # Для других типов ROUGE (rouge1, rouge2)
                target_tokens = self._preprocess_summary_ru(target, self.use_stemmer)
                prediction_tokens = self._preprocess_summary_ru(prediction, self.use_stemmer)
                scores[rouge_type] = self._score_ngrams(rouge_type, target_tokens, prediction_tokens)

        return scores


def calculate_rouge_ru(predictions, references, rouge_types=None):
    """Упрощённая функция для вычисления ROUGE с русскими текстами"""
    if rouge_types is None:
        rouge_types = ["rouge1", "rouge2", "rougeL"]

    # Используем стандартный scorer
    scorer = rouge_scorer.RougeScorer(rouge_types, use_stemmer=False)

    scores = {}
    for rouge_type in rouge_types:
        scores[rouge_type] = scoring.Score(precision=0, recall=0, fmeasure=0)

    for pred, ref in zip(predictions, references):
        # Просто lowercase, без морфологии
        pred_lower = pred.lower()
        ref_lower = ref.lower()

        score = scorer.score(ref_lower, pred_lower)
        for rouge_type in rouge_types:
            scores[rouge_type] = scoring.Score(
                precision=scores[rouge_type].precision + score[rouge_type].precision,
                recall=scores[rouge_type].recall + score[rouge_type].recall,
                fmeasure=scores[rouge_type].fmeasure + score[rouge_type].fmeasure
            )

    # Вычисляем среднее
    n = len(predictions)
    for rouge_type in rouge_types:
        scores[rouge_type] = scoring.Score(
            precision=scores[rouge_type].precision / n,
            recall=scores[rouge_type].recall / n,
            fmeasure=scores[rouge_type].fmeasure / n
        )

    return scores


# Пример использования
if __name__ == "__main__":
    references = ["Транснефть является крупнейшей российской трубопроводной компанией."]
    predictions = ["Компания Транснефть - самая большая компания в России в сфере трубопроводного транспорта."]

    scores = calculate_rouge_ru(predictions, references)
    print("ROUGE-1:", scores["rouge1"])
    print("ROUGE-2:", scores["rouge2"])
    print("ROUGE-L:", scores["rougeL"])