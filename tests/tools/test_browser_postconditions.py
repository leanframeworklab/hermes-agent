import json
from tools import browser_tool


def test_click_with_postcondition_fails_closed_when_business_effect_missing(monkeypatch):
    def fake_run(task_id, command, args=None, timeout=None, _engine_override=None):
        if command == "click":
            return {"success": True, "data": {}}
        if command == "eval":
            return {"success": True, "data": {"result": "false"}}
        raise AssertionError(command)
    monkeypatch.setattr(browser_tool, "_run_browser_command", fake_run)
    out = json.loads(browser_tool.browser_click("@e5", task_id="t1", postcondition={"type": "js_truthy", "expression": "window.saved === true"}))
    assert out["success"] is False
    assert out["driver_success"] is True
    assert out["effect_verified"] is False
    assert out["error_code"] == "POSTCONDITION_FAILED"


def test_click_with_postcondition_returns_verified_evidence(monkeypatch):
    def fake_run(task_id, command, args=None, timeout=None, _engine_override=None):
        if command == "click":
            return {"success": True, "data": {}}
        if command == "eval":
            return {"success": True, "data": {"result": "true"}}
        raise AssertionError(command)
    monkeypatch.setattr(browser_tool, "_run_browser_command", fake_run)
    out = json.loads(browser_tool.browser_click("e5", task_id="t1", postcondition={"type": "js_truthy", "expression": "window.saved === true"}))
    assert out["success"] is True
    assert out["effect_verified"] is True
    assert out["verification"]["type"] == "js_truthy"


def test_type_value_equals_postcondition(monkeypatch):
    def fake_run(task_id, command, args=None, timeout=None, _engine_override=None):
        if command == "fill":
            return {"success": True, "data": {}}
        if command == "eval":
            return {"success": True, "data": {"result": '"cedrick"'}}
        raise AssertionError(command)
    monkeypatch.setattr(browser_tool, "_run_browser_command", fake_run)
    out = json.loads(browser_tool.browser_type("@e3", "cedrick", task_id="t1", postcondition={"type": "js_equals", "expression": "document.querySelector('#name').value", "expected": "cedrick"}))
    assert out["success"] is True
    assert out["effect_verified"] is True
