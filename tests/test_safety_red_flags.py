from soficca_core.engine import generate_report

def test_red_flag_escalation_sets_path_and_message():
    payload = {
        "user": {},
        "measurements": [],
        "context": {
            "chat_text": "I want to kill myself",
            "chat_state": None,
            "debug": False,
        },
    }
    res = generate_report(payload)
    assert res["ok"] is True
    assert res["report"]["path"] == "PATH_ESCALATE_HUMAN"
    assert "RED_FLAG_SELF_HARM" in res["report"]["flags"]
    assert isinstance(res["report"]["chat"]["assistant_message"], str)
