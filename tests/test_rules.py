from soficca_core.rules import apply_rules


def test_rules_intermittent_allows_meds():
    signals = {
        "intermittent_pattern": True,
        "user_requests_meds": None,
        "morning_erection_reduced": False,
    }
    decision = apply_rules(signals)
    assert decision["path"] == "PATH_MEDS_OK"


def test_rules_persistent_eval_first_when_no_meds_request():
    signals = {
        "intermittent_pattern": False,
        "user_requests_meds": None,
        "morning_erection_reduced": True,
    }
    decision = apply_rules(signals)
    assert decision["path"] == "PATH_EVAL_FIRST"
    assert "persistent_pattern" in decision["flags"]
    assert "physiology_signal" in decision["flags"]


def test_rules_persistent_user_requests_meds_adds_parallel_eval():
    signals = {
        "intermittent_pattern": False,
        "user_requests_meds": True,
        "morning_erection_reduced": True,
    }
    decision = apply_rules(signals)
    assert decision["path"] == "PATH_MEDS_OK"
    assert "needs_eval_parallel" in decision["flags"]
    assert "physiology_signal" in decision["flags"]
