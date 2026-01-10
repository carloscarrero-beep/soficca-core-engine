from soficca_core.interpret_en import interpret


def test_frequency_good_days_bad_days_is_sometimes():
    parsed = interpret("Not always. I have good days and bad days.", "frequency")
    assert parsed["type"] == "answer"
    assert parsed["value"] == "sometimes"


def test_frequency_every_time_is_always():
    parsed = interpret("Every time.", "frequency")
    assert parsed["type"] == "answer"
    assert parsed["value"] == "always"


def test_frequency_depends_is_sometimes():
    parsed = interpret("It depends.", "frequency")
    assert parsed["type"] == "answer"
    assert parsed["value"] == "sometimes"
