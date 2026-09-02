from app.tools.speech_tool import normalize_text


def test_normalize_text_converts_numeric_digits_to_word_names():
    assert normalize_text("7") == "seven"
    assert normalize_text("7.") == "seven"
    assert normalize_text("Seven") == "seven"
    assert normalize_text("seven") == "seven"


def test_normalize_text_keeps_text_words_unchanged():
    assert normalize_text("apple") == "apple"
    assert normalize_text("my apple") == "my apple"
