from soficca_core.engine import generate_report

def test_safety_lock_asks_country_then_escalates():
    # Turn 1: red flag triggers safety lock and asks for country
    payload1 = {
        "user": {},
        "measurements": [],
        "context": {
            "chat_text": "I want to kill myself",
            "chat_state": None,
            "debug": False,
        },
    }
    res1 = generate_report(payload1)
    assert res1["ok"] is True
    assert res1["report"]["path"] == "PATH_ESCALATE_HUMAN"
    assert "RED_FLAG_SELF_HARM" in res1["report"]["flags"]
    assert "country" in (res1["report"]["chat"].get("assistant_message") or "").lower()

    # Turn 2: provide country; should give escalation guidance and end
    st = res1["report"]["chat"]["state"]
    payload2 = {
        "user": {},
        "measurements": [],
        "context": {
            "chat_text": "Colombia",
            "chat_state": st,
            "debug": False,
        },
    }
    res2 = generate_report(payload2)
    assert res2["ok"] is True
    assert res2["report"]["path"] == "PATH_ESCALATE_HUMAN"
    assert res2["report"]["chat"]["done"] is True


def test_generate_report_contract_shape_future_proof():
    result = generate_report({"any": "thing"})
    assert isinstance(result, dict)

    required_top = {"ok", "errors", "normalized_input", "report"}
    assert required_top.issubset(result)

    assert isinstance(result["ok"], bool)
    assert isinstance(result["errors"], list)
    assert isinstance(result["normalized_input"], dict)

    ni = result["normalized_input"]
    assert {"user", "measurements", "context"}.issubset(ni)
    assert isinstance(ni["user"], dict)
    assert isinstance(ni["measurements"], list)
    assert isinstance(ni["context"], dict)

    report = result["report"]
    assert isinstance(report, dict)

    required_report = {"path","scores", "flags", "recommendations", "reasons", "chat"}
    assert required_report.issubset(report)

    assert isinstance(report["path"], str)
    assert isinstance(report["scores"], dict)
    assert isinstance(report["flags"], list)
    assert isinstance(report["recommendations"], list)
    assert isinstance(report["reasons"], list)
    assert isinstance(report["chat"], dict)
