from soficca_core.engine import generate_report

def test_generate_report_contract_shape_future_proof():
    result = generate_report({"any": "thing"})
    assert isinstance(result, dict)

    required_top = {"ok", "errors", "normalized_input", "report"}
    assert required_top.issubset(result)

    assert isinstance(result["ok"], bool)
    assert isinstance(result["errors"], list)
    assert isinstance(result["normalized_input"], dict)

    report = result["report"]
    assert isinstance(report, dict)

    required_report = {"scores", "flags", "recommendations", "reasons"}
    assert required_report.issubset(report)

    assert isinstance(report["scores"], dict)
    assert isinstance(report["flags"], list)
    assert isinstance(report["recommendations"], list)
    assert isinstance(report["reasons"], list)

    chat = result.get("chat", report.get("chat", {}))
    assert isinstance(chat, dict)
