
from soficca_core.engine import generate_report

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
