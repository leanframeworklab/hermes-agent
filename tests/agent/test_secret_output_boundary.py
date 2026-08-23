"""Fail-closed synthetic tests for the agent secret-output boundary."""

import json
from unittest.mock import MagicMock

from agent.secret_output import (
    OUTPUT_WITHHELD,
    classify_secret_command,
    sanitize_command_display,
    sanitize_environment_metadata,
    sanitize_exception,
    sanitize_mapping,
    sanitize_secret_output,
)


def clean(value, stream="stdout"):
    return sanitize_secret_output(value, source_stream=stream).text


def test_stdout_assignment_redacted():
    secret = "synthetic-gh-token-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean(f"GH_TOKEN={secret}")
    assert secret not in result
    assert "[REDACTED:credential]" in result


def test_stderr_bearer_redacted():
    secret = "synthetic-bearer-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean(f"Authorization: Bearer {secret}", "stderr")
    assert secret not in result
    assert "[REDACTED:bearer_token]" in result


def test_json_token_redacted():
    secret = "synthetic-json-token-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean(json.dumps({"token": secret}))
    assert secret not in result
    assert "[REDACTED:credential]" in result


def test_authorization_header_redacted():
    secret = "synthetic-auth-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean(f"authorization: Basic {secret}")
    assert secret not in result
    assert "[REDACTED:credential]" in result


def test_url_userinfo_password_redacted():
    result = clean("https://user:synthetic-password-ABCDEFGHIJKLMNOP@example.com/path")
    assert "synthetic-password" not in result
    assert "[REDACTED:password]" in result


def test_url_query_api_key_redacted():
    secret = "synthetic-query-key-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean(f"https://example.com/path?api_key={secret}&public_id=42")
    assert secret not in result
    assert "api_key=[REDACTED:credential]" in result
    assert "public_id=42" in result


def test_private_key_redacted():
    result = clean("-----BEGIN PRIVATE KEY-----\nsynthetic-private-material\n-----END PRIVATE KEY-----")
    assert "synthetic-private-material" not in result
    assert "[REDACTED:private_key]" in result


def test_jwt_shaped_credential_redacted():
    value = "eyJhbGciOiJIUzI1NiJ9.syntheticpayload.syntheticsignature"
    result = clean(value)
    assert value not in result
    assert "[REDACTED:jwt]" in result


def test_github_shaped_credential_redacted():
    value = "ghp_ABCDEFGHIJKLMNOPQRSTUV1234567890"
    result = clean(value)
    assert value not in result
    assert "[REDACTED:github_token]" in result


def test_git_sha_not_redacted():
    value = "deployment sha 0123456789abcdef0123456789abcdef01234567"
    assert clean(value) == value


def test_uuid_not_redacted():
    value = "run 123e4567-e89b-12d3-a456-426614174000"
    assert clean(value) == value


def test_campaign_id_not_redacted():
    value = "campaign 8552896"
    assert clean(value) == value


def test_credential_helper_response_redacts_password_only():
    secret = "synthetic-helper-password-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean(f"protocol=https\nhost=github.com\nusername=test\npassword={secret}")
    assert "username=test" in result
    assert secret not in result
    assert "password=[REDACTED:credential]" in result


def test_exception_redacts_stdout_and_stderr():
    secret = "synthetic-exception-secret-ABCDEFGHIJKLMNOPQRSTUV"
    result = sanitize_exception(RuntimeError(f"stdout={secret}; stderr={secret}"))
    assert secret not in result.text
    assert result.secret_detected


def test_receipt_mapping_redacts_nested_secret():
    secret = "synthetic-receipt-secret-ABCDEFGHIJKLMNOPQRSTUV"
    result = sanitize_mapping({"status": "PASS", "details": {"token": secret}})
    assert result.value["status"] == "PASS"
    assert result.value["details"]["token"] == "[REDACTED:credential]"
    assert secret not in json.dumps(result.value)


def test_logger_serialization_contract_is_sanitized():
    secret = "synthetic-log-secret-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean(f"log token={secret}")
    assert secret not in result


def test_command_display_redacts_inline_token():
    secret = "synthetic-command-token-ABCDEFGHIJKLMNOPQRSTUV"
    result = sanitize_command_display(f"tool --token={secret}")
    assert secret not in result.text
    assert "[REDACTED:credential]" in result.text


def test_environment_metadata_exposes_presence_only():
    result = sanitize_environment_metadata({"GH_TOKEN": "synthetic-env-secret", "PATH": "/bin"})
    assert result == {"GH_TOKEN": {"present": True}, "PATH": {"present": True}}


def test_multiple_secrets_redacted():
    first = "ghp_ABCDEFGHIJKLMNOPQRSTUV1234567890"
    second = "synthetic-second-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean(f"GH_TOKEN={first}\npassword={second}")
    assert first not in result and second not in result
    assert result.count("[REDACTED:") >= 2


def test_mixed_stdout_stderr_contract():
    secret = "synthetic-mixed-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean(f"stdout token={secret}\nstderr Authorization: Bearer {secret}", "combined")
    assert secret not in result


def test_multiline_private_material_redacted():
    result = clean("prefix\n-----BEGIN RSA PRIVATE KEY-----\nsynthetic\n-----END RSA PRIVATE KEY-----\nsuffix")
    assert "synthetic" not in result
    assert "prefix" in result and "suffix" in result


def test_structured_escaped_secret_redacted():
    secret = "synthetic-escaped-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean('{"outer":{"token":"' + secret + '"},"items":[1,2]}')
    assert secret not in result
    assert "[REDACTED:credential]" in result


def test_ansi_and_secret_redacted():
    secret = "synthetic-ansi-ABCDEFGHIJKLMNOPQRSTUV"
    result = clean(f"\x1b[31mTOKEN={secret}\x1b[0m")
    assert secret not in result


def test_command_guard_blocks_secret_dump_patterns():
    commands = [
        "gh auth token",
        "gh auth status --show-token",
        "git credential fill",
        "credential-helper get",
        "printenv GH_TOKEN",
        "echo $GITHUB_TOKEN",
        "cat ~/.config/gh/hosts.yml",
        "env",
    ]
    for command in commands:
        decision = classify_secret_command(command)
        assert decision["allowed"] is False
        assert "[REDACTED" not in decision["command"]


def test_command_guard_allows_metadata_status():
    decision = classify_secret_command("gh auth status")
    assert decision["allowed"] is True


def test_sanitizer_failure_withholds_output(monkeypatch):
    import agent.secret_output as module

    monkeypatch.setattr(module, "_sanitize_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("synthetic failure")))
    result = sanitize_secret_output("synthetic secret")
    assert result.status == OUTPUT_WITHHELD
    assert result.text == "[OUTPUT_WITHHELD]"
    assert "synthetic secret" not in result.text


def test_mcp_tool_result_contract_uses_same_boundary():
    secret = "synthetic-mcp-ABCDEFGHIJKLMNOPQRSTUV"
    result = sanitize_mapping({"content": [{"type": "text", "text": secret}], "isError": False})
    assert secret not in json.dumps(result.value)


def test_exact_sha_receipt_not_false_positive():
    value = {"deployed_sha": "0123456789abcdef0123456789abcdef01234567", "status": "PASS"}
    result = sanitize_mapping(value)
    assert result.value == value


def test_terminal_tool_sanitizes_before_transform_hook(monkeypatch, tmp_path):
    import tools.terminal_tool as terminal_tool_module

    secret = "synthetic-terminal-ABCDEFGHIJKLMNOPQRSTUV"
    env = MagicMock()
    env.execute.return_value = {"output": f"TOKEN={secret}", "returncode": 0}
    monkeypatch.setattr(terminal_tool_module, "_get_env_config", lambda: {
        "env_type": "local", "timeout": 30, "cwd": str(tmp_path), "host_cwd": None,
        "modal_mode": "auto", "docker_image": "", "singularity_image": "",
        "modal_image": "", "daytona_image": "",
    })
    monkeypatch.setattr(terminal_tool_module, "_start_cleanup_thread", lambda: None)
    monkeypatch.setattr(terminal_tool_module, "_check_all_guards", lambda *_a, **_k: {"approved": True})
    monkeypatch.setitem(terminal_tool_module._active_environments, "default", env)
    monkeypatch.setitem(terminal_tool_module._last_activity, "default", 0.0)
    seen = {}

    def hook(_name, **kwargs):
        seen.update(kwargs)
        return []

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", hook)
    result = json.loads(terminal_tool_module.terminal_tool(command="echo synthetic"))
    assert secret not in seen["output"]
    assert secret not in result["output"]
