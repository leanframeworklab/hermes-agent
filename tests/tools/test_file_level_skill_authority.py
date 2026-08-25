import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from tools.skill_authority import (
    FILE_DEPLOYMENT_AUTHORITY,
    check_managed_runtime_mutation,
    deploy_runtime_authority,
    plan_file_runtime_authority,
    validate_file_runtime_authority,
)


CANONICAL_SOURCE = Path("/home/deploy/lah-stack-repos/lah-stack-skills")


def declaration(**overrides):
    value = {
        "source_repo": "leanframeworklab/lah-stack-skills",
        "source_path": str(CANONICAL_SOURCE),
        "source_file": "SKILL.md",
        "runtime_file": "lah-workflow/SKILL.md",
    }
    value.update(overrides)
    return {"lah-workflow": value}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deploy(runtime, **overrides):
    return deploy_runtime_authority(
        runtime,
        {},
        file_declarations=declaration(**overrides),
        deployment_authority=FILE_DEPLOYMENT_AUTHORITY,
        allow_runtime_drift=True,
    )


def test_declared_canonical_file_to_declared_codex_target_succeeds(tmp_path):
    manifest = deploy(tmp_path / "codex-skills")
    assert (tmp_path / "codex-skills/lah-workflow/SKILL.md").is_file()
    assert manifest["file_mappings"]["lah-workflow"]["runtime_file"] == "lah-workflow/SKILL.md"


def test_exact_source_and_runtime_fingerprints_record_and_match(tmp_path):
    runtime = tmp_path / "codex-skills"
    manifest = deploy(runtime)
    entry = manifest["file_mappings"]["lah-workflow"]
    assert entry["source_fingerprint"] == sha(CANONICAL_SOURCE / "SKILL.md")
    assert entry["runtime_fingerprint"] == entry["source_fingerprint"]
    assert validate_file_runtime_authority(runtime, manifest)["valid"] is True


def test_validation_uses_declared_git_blob_when_worktree_is_dirty(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    source_file = source / "SKILL.md"
    source_file.write_text("committed\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=source, check=True)
    subprocess.run(["git", "add", "SKILL.md"], cwd=source, check=True)
    subprocess.run(["git", "commit", "-qm", "source"], cwd=source, check=True)
    source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    committed_fingerprint = hashlib.sha256(b"committed\n").hexdigest()
    source_file.write_text("uncommitted dirty state\n", encoding="utf-8")
    runtime = tmp_path / "runtime"
    target = runtime / "x/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("committed\n", encoding="utf-8")
    manifest = {"file_mappings": {"x": {
        "source_path": str(source),
        "source_file": "SKILL.md",
        "source_sha": source_sha,
        "source_fingerprint": committed_fingerprint,
        "runtime_file": "x/SKILL.md",
        "runtime_fingerprint": committed_fingerprint,
    }}}
    assert validate_file_runtime_authority(runtime, manifest)["valid"] is True


def test_undeclared_source_rejected(tmp_path):
    with pytest.raises(ValueError, match="UNDECLARED_SKILL_DEPLOYMENT_SOURCE"):
        deploy(tmp_path / "runtime", source_repo="other/repo")


def test_undeclared_target_rejected(tmp_path):
    with pytest.raises(ValueError, match="UNDECLARED_SKILL_DEPLOYMENT_TARGET"):
        deploy(tmp_path / "runtime", runtime_file="other/SKILL.md")


def test_path_traversal_rejected(tmp_path):
    with pytest.raises(ValueError, match="UNDECLARED_SKILL_DEPLOYMENT_TARGET"):
        deploy(tmp_path / "runtime", runtime_file="../outside/SKILL.md")


def test_source_symlink_escape_rejected(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    (source_root / "escape.md").symlink_to(outside)
    with pytest.raises(ValueError, match="UNDECLARED_SKILL_DEPLOYMENT_SOURCE"):
        plan_file_runtime_authority(
            tmp_path / "runtime",
            {"x": {"source_repo": "test", "source_path": str(source_root), "source_file": "escape.md", "runtime_file": "x/SKILL.md"}},
            approved_source_roots={"test": source_root},
            approved_runtime_targets={"x": "x/SKILL.md"},
        )


def test_target_symlink_escape_rejected(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (runtime / "lah-workflow").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="UNDECLARED_SKILL_DEPLOYMENT_TARGET"):
        deploy(runtime)


def test_source_fingerprint_mismatch_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="SKILL_SOURCE_FINGERPRINT_MISMATCH"):
        deploy(tmp_path / "runtime", source_fingerprint="wrong")


def test_committed_sha_rejects_uncommitted_source_file(tmp_path):
    with pytest.raises(ValueError, match="SKILL_SOURCE_FINGERPRINT_MISMATCH"):
        deploy(tmp_path / "runtime", source_sha="0" * 40)


def test_direct_foreground_mutation_remains_denied(tmp_path):
    runtime = tmp_path / "codex-skills"
    deploy(runtime)
    decision = check_managed_runtime_mutation(runtime / "lah-workflow/SKILL.md", "write", runtime_root=runtime)
    assert decision.allowed is False
    assert decision.managed is True


def test_approved_canonical_deployment_caller_succeeds(tmp_path):
    deploy(tmp_path / "runtime")


def test_unrelated_runtime_file_unchanged(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    unrelated = runtime / "other-skill/SKILL.md"
    unrelated.parent.mkdir()
    unrelated.write_text("keep", encoding="utf-8")
    before = sha(unrelated)
    deploy(runtime)
    assert sha(unrelated) == before


def test_dirty_unrelated_state_unchanged(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    dirty = runtime / "operator-note.txt"
    dirty.write_text("preserve", encoding="utf-8")
    deploy(runtime)
    assert dirty.read_text(encoding="utf-8") == "preserve"


def test_repeated_exact_deployment_is_idempotent(tmp_path):
    runtime = tmp_path / "runtime"
    first = deploy(runtime)
    second = deploy(runtime)
    assert first["file_mappings"]["lah-workflow"]["source_fingerprint"] == second["file_mappings"]["lah-workflow"]["source_fingerprint"]


def test_changed_canonical_source_produces_new_fingerprint(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    source_file = source / "SKILL.md"
    source_file.write_text("one", encoding="utf-8")
    first = plan_file_runtime_authority(
        tmp_path / "runtime",
        {"x": {"source_repo": "test", "source_path": str(source), "source_file": "SKILL.md", "runtime_file": "x/SKILL.md"}},
        approved_source_roots={"test": source},
        approved_runtime_targets={"x": "x/SKILL.md"},
    )
    source_file.write_text("two", encoding="utf-8")
    second = plan_file_runtime_authority(
        tmp_path / "runtime",
        {"x": {"source_repo": "test", "source_path": str(source), "source_file": "SKILL.md", "runtime_file": "x/SKILL.md"}},
        approved_source_roots={"test": source},
        approved_runtime_targets={"x": "x/SKILL.md"},
    )
    assert first[0]["source_fingerprint"] != second[0]["source_fingerprint"]


def test_failed_drift_deployment_leaves_target_unchanged(tmp_path):
    runtime = tmp_path / "runtime"
    target = runtime / "lah-workflow/SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("old", encoding="utf-8")
    before = target.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected runtime drift"):
        deploy_runtime_authority(
            runtime,
            {},
            file_declarations=declaration(),
            deployment_authority=FILE_DEPLOYMENT_AUTHORITY,
        )
    assert target.read_text(encoding="utf-8") == before
