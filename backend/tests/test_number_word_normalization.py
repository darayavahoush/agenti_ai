from app.tools.speech_tool import normalize_text


def test_normalize_text_converts_numeric_digits_to_word_names():
    assert normalize_text("7") == "seven"
    assert normalize_text("7.") == "seven"
    assert normalize_text("Seven") == "seven"
    assert normalize_text("seven") == "seven"


def test_normalize_text_cleans_common_word_punctuation_and_spacing():
    assert normalize_text("Apple!") == "apple"
    assert normalize_text("  apple  ") == "apple"
    assert normalize_text("my apple") == "my apple"
    assert normalize_text("my, apple!") == "my apple"
    assert normalize_text("hello-world") == "hello world"


def test_normalize_text_preserves_non_english_word_text():
    assert normalize_text("कुत्ता") == "कुत्ता"
    assert normalize_text("ఏడు") == "ఏడు"
