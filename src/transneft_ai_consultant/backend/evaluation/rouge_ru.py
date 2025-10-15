import razdel  # Библиотека для работы с русскими текстами
import pymorphy2  # Морфологический анализатор для русского языка

from rouge_score import rouge_scorer, scoring

# Создаем морфологический анализатор
morph = pymorphy2.MorphAnalyzer()


def normalize_word(word):
    """Нормализует слово к начальной форме (лемме)"""
    parsed_word = morph.parse(word)[0]
    return parsed_word.normal_form


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
        # Сохраняем оригинальную функцию токенизации
        original_tokenize = self._tokenize

        # Заменяем на нашу функцию для русского языка
        self._tokenize = self._preprocess_summary_ru

        # Рассчитываем метрики
        scores = {}
        for rouge_type in self.rouge_types:
            if rouge_type == 'rougeL':
                # Для ROUGE-L используем наши токены с учетом русской морфологии
                target_tokens = self._preprocess_summary_ru(target, self.use_stemmer)
                prediction_tokens = self._preprocess_summary_ru(prediction, self.use_stemmer)
                scores[rouge_type] = self._score_lcs(target_tokens, prediction_tokens)
            elif rouge_type == 'rougeLsum':
                # Для ROUGE-Lsum разбиваем на предложения с учетом русской пунктуации
                target_sents = tokenize_sentences_ru(target)
                prediction_sents = tokenize_sentences_ru(prediction)

                target_tokens_list = [self._preprocess_summary_ru(s, self.use_stemmer) for s in target_sents]
                prediction_tokens_list = [self._preprocess_summary_ru(s, self.use_stemmer) for s in prediction_sents]
                scores[rouge_type] = self._score_lcs_merge(target_tokens_list, prediction_tokens_list)
            else:
                # Для других типов ROUGE используем стандартную логику библиотеки
                scores[rouge_type] = self._score_ngrams(rouge_type, target, prediction)

        # Восстанавливаем оригинальную функцию токенизации
        self._tokenize = original_tokenize

        return scores


def calculate_rouge_ru(predictions, references, rouge_types=None):
    """Удобная функция для вычисления ROUGE с русскими текстами"""
    if rouge_types is None:
        rouge_types = ["rouge1", "rouge2", "rougeL"]

    scorer = RougeRuScorer(rouge_types=rouge_types, use_stemmer=True)

    scores = {}
    for rouge_type in rouge_types:
        scores[rouge_type] = scoring.Score(precision=0, recall=0, fmeasure=0)

    for pred, ref in zip(predictions, references):
        score = scorer.score_ru(ref, pred)
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