from app.services.transformer import transform


def test_transform_converts_lowercase_to_uppercase():
    assert transform("hello") == "HELLO"


def test_transform_handles_mixed_case():
    assert transform("Hello World") == "HELLO WORLD"


def test_transform_handles_empty_string():
    assert transform("") == ""


def test_transform_preserves_numbers_and_punctuation():
    assert transform("hello, world! 123") == "HELLO, WORLD! 123"    
