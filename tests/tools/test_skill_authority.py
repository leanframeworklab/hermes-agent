import json

from tools.skill_authority import (
    build_manifest,
    canonical_deployment_authority,
    check_managed_runtime_mutation,
    classify_skill_identifier,
    deploy_runtime_authority,
    validate_runtime_authority,
)


def test_managed_decision_is_caller_independent(tmp_path):
    source = _skill(tmp_path / "source", "software-development", "managed-skill")
    runtime = _skill(tmp_path / "runtime", "software-development", "managed-skill")
    manifest = build_manifest(
        tmp_path / "runtime",
        {"managed-skill": {"source_path": str(source), "source_repo": "test"}},
    )
    (tmp_path / "runtime" / ".governance_manifest.json").write_text(json.dumps(manifest))

    foreground = check_managed_runtime_mutation(
        runtime, "patch", mutation_authority="foreground", runtime_root=tmp_path / "runtime"
    )
    background = check_managed_runtime_mutation(
        runtime, "patch", mutation_authority="background_review", runtime_root=tmp_path / "runtime"
    )
    assert foreground == background
    assert foreground.allowed is False
    assert foreground.managed is True


def test_only_canonical_deployment_authority_can_allow_managed_mutation(tmp_path):
    source = _skill(tmp_path / "source", "software-development", "managed-skill")
    runtime = _skill(tmp_path / "runtime", "software-development", "managed-skill")
    manifest = build_manifest(
        tmp_path / "runtime",
        {"managed-skill": {"source_path": str(source), "source_repo": "test"}},
    )
    (tmp_path / "runtime" / ".governance_manifest.json").write_text(json.dumps(manifest))

    denied = check_managed_runtime_mutation(runtime, "patch", runtime_root=tmp_path / "runtime")
    assert denied.allowed is False
    with canonical_deployment_authority():
        allowed = check_managed_runtime_mutation(runtime, "patch", runtime_root=tmp_path / "runtime")
    assert allowed.allowed is True
    assert allowed.managed is True


def test_invalid_manifest_fails_closed_for_critical_path_but_not_unmanaged(tmp_path):
    runtime = tmp_path / "runtime"
    critical = runtime / "lah-stack" / "lah-workflow-small-model"
    critical.mkdir(parents=True)
    (critical / "SKILL.md").write_text("managed", encoding="utf-8")
    (runtime / ".governance_manifest.json").write_text("{invalid", encoding="utf-8")

    critical_decision = check_managed_runtime_mutation(critical, "patch", runtime_root=runtime)
    user_decision = check_managed_runtime_mutation(runtime / "user-skill", "patch", runtime_root=runtime)
    assert critical_decision.managed is True
    assert critical_decision.allowed is False
    assert user_decision.managed is False
    assert user_decision.allowed is True


def _skill(root, category, name, body="body"):
    path = root / category / name
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {name}\n---\n{body}\n",
        encoding="utf-8",
    )
    return path


def test_manifest_fingerprint_matches_declared_source_and_runtime(tmp_path):
    source = _skill(tmp_path / "source", "software-development", "lah-repo-router")
    runtime = _skill(tmp_path / "runtime", "software-development", "lah-repo-router")
    manifest = build_manifest(
        runtime,
        {"lah-repo-router": {"source_path": str(source), "source_repo": "test"}},
    )
    result = validate_runtime_authority(runtime, manifest, critical=("lah-repo-router",))
    assert result["valid"] is True


def test_manifest_detects_runtime_drift(tmp_path):
    source = _skill(tmp_path / "source", "software-development", "lah-repo-router")
    runtime = _skill(tmp_path / "runtime", "software-development", "lah-repo-router", "changed")
    manifest = build_manifest(
        runtime,
        {"lah-repo-router": {"source_path": str(source), "source_repo": "test"}},
    )
    result = validate_runtime_authority(runtime, manifest, critical=("lah-repo-router",))
    assert result["valid"] is False
    assert "content drift" in result["errors"][0]


def test_missing_critical_manifest_entry_blocks(tmp_path):
    runtime = _skill(tmp_path / "runtime", "software-development", "lah-repo-router")
    manifest = {"schema_version": 1, "skills": {}}
    result = validate_runtime_authority(runtime, manifest, critical=("lah-repo-router",))
    assert result["valid"] is False
    assert "missing manifest entry" in result["errors"][0]


def test_declared_fingerprint_cannot_be_stale(tmp_path):
    source = _skill(tmp_path / "source", "software-development", "lah-repo-router")
    runtime = _skill(tmp_path / "runtime", "software-development", "lah-repo-router")
    manifest = build_manifest(
        runtime,
        {"lah-repo-router": {"source_path": str(source), "source_repo": "test"}},
    )
    manifest["skills"]["lah-repo-router"]["runtime_content_sha256"] = "stale"
    result = validate_runtime_authority(runtime, manifest, critical=("lah-repo-router",))
    assert result["valid"] is False
    assert any("declared runtime fingerprint mismatch" in error for error in result["errors"])


def test_manifest_requires_explicit_invocation_identity(tmp_path):
    source = _skill(tmp_path / "source", "software-development", "lah-repo-router")
    runtime = _skill(tmp_path / "runtime", "software-development", "lah-repo-router")
    manifest = build_manifest(
        runtime,
        {"lah-repo-router": {"source_path": str(source), "source_repo": "test"}},
    )
    manifest["skills"]["lah-repo-router"].pop("invocation_name", None)
    result = validate_runtime_authority(runtime, manifest, critical=("lah-repo-router",))
    assert result["valid"] is False
    assert "invocation identity missing" in result["errors"][0]


def test_identifier_classifier_keeps_plugin_and_local_contracts_distinct():
    names = {"lah-repo-router"}
    assert classify_skill_identifier("lah-repo-router", names) == "VALID_CANONICAL_NAME"
    assert classify_skill_identifier("lah-stack/lah-repo-router", names) == "CATEGORY_PATH_USED_AS_IDENTIFIER"
    assert classify_skill_identifier("superpowers:writing-plans", names) == "VALID_PLUGIN_NAMESPACE"


def test_deployment_refuses_unexpected_divergent_target(tmp_path):
    source = _skill(tmp_path / "source", "software-development", "lah-repo-router", "source")
    runtime = tmp_path / "runtime"
    _skill(runtime, "software-development", "lah-repo-router", "runtime")

    try:
        deploy_runtime_authority(
            runtime,
            {"lah-repo-router": {"source_path": str(source), "source_repo": "test"}},
        )
    except ValueError as exc:
        assert "unexpected runtime drift" in str(exc)
    else:
        raise AssertionError("deployment must refuse divergent target without explicit convergence")


def test_deployment_atomically_converges_and_writes_manifest(tmp_path):
    source = _skill(tmp_path / "source", "software-development", "lah-repo-router", "source")
    runtime = tmp_path / "runtime"
    _skill(runtime, "software-development", "lah-repo-router", "runtime")

    manifest = deploy_runtime_authority(
        runtime,
        {"lah-repo-router": {"source_path": str(source), "source_repo": "test"}},
        allow_runtime_drift=True,
    )

    assert (runtime / "software-development/lah-repo-router/SKILL.md").read_text(encoding="utf-8").endswith("source\n")
    assert manifest["schema_version"] == 1
    assert manifest["skills"]["lah-repo-router"]["invocation_name"] == "lah-repo-router"
    assert validate_runtime_authority(runtime, manifest, critical=("lah-repo-router",))["valid"] is True


def test_deployment_creates_missing_target_parents_in_fresh_runtime(tmp_path):
    source = _skill(tmp_path / "source", "software-development", "lah-repo-router", "source")
    runtime = tmp_path / "fresh-runtime"

    manifest = deploy_runtime_authority(
        runtime,
        {
            "lah-repo-router": {
                "source_path": str(source),
                "source_repo": "test",
                "runtime_path": "software-development/lah-repo-router",
            }
        },
    )

    assert (runtime / "software-development/lah-repo-router/SKILL.md").is_file()
    assert validate_runtime_authority(runtime, manifest, critical=("lah-repo-router",))["valid"] is True
