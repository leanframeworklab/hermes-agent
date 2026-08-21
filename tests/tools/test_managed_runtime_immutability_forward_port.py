import json
from pathlib import Path

import pytest

from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations
from tools.skill_authority import deploy_runtime_authority
from tools.skill_manager_tool import skill_manage


def _skill(root: Path, name: str = "managed-skill") -> Path:
    path = root / "lah-stack" / name
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test\n---\nbase\n",
        encoding="utf-8",
    )
    (path / "references").mkdir()
    (path / "references" / "existing.md").write_text("original\n", encoding="utf-8")
    return path


def _manifest(root: Path, skill: Path) -> None:
    (root / ".governance_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "skills": {
                    "managed-skill": {
                        "invocation_name": "managed-skill",
                        "runtime_path": skill.relative_to(root).as_posix(),
                    }
                },
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def managed_fixture(tmp_path, monkeypatch):
    runtime = tmp_path / "skills"
    skill = _skill(runtime)
    _manifest(runtime, skill)
    monkeypatch.setattr("tools.skill_manager_tool.SKILLS_DIR", runtime)
    monkeypatch.setattr("agent.skill_utils.get_all_skills_dirs", lambda: [runtime])
    monkeypatch.setattr("tools.skill_authority.get_hermes_home", lambda: tmp_path)
    return tmp_path, runtime, skill


def test_skill_manager_denies_managed_skill_and_support_mutation(managed_fixture):
    _, _, skill = managed_fixture

    skill_result = json.loads(
        skill_manage(
            action="edit",
            name="managed-skill",
            content="---\nname: managed-skill\ndescription: changed\n---\nchanged\n",
        )
    )
    support_result = json.loads(
        skill_manage(
            action="write_file",
            name="managed-skill",
            file_path="references/new.md",
            file_content="blocked",
        )
    )
    patch_result = json.loads(
        skill_manage(
            action="patch",
            name="managed-skill",
            file_path="references/existing.md",
            old_string="original",
            new_string="changed",
        )
    )
    remove_result = json.loads(
        skill_manage(
            action="remove_file",
            name="managed-skill",
            file_path="references/existing.md",
        )
    )
    delete_result = json.loads(skill_manage(action="delete", name="managed-skill"))

    assert skill_result["error"] == "managed_skill_runtime_immutable"
    assert support_result["error"] == "managed_skill_runtime_immutable"
    assert patch_result["error"] == "managed_skill_runtime_immutable"
    assert remove_result["error"] == "managed_skill_runtime_immutable"
    assert delete_result["error"] == "managed_skill_runtime_immutable"
    assert (skill / "SKILL.md").read_text(encoding="utf-8").endswith("base\n")
    assert (skill / "references" / "existing.md").exists()
    assert not (skill / "references/new.md").exists()


def test_generic_file_operations_deny_managed_write_patch_and_symlink(managed_fixture):
    tmp_path, _, skill = managed_fixture
    env = LocalEnvironment(cwd=str(tmp_path))
    try:
        ops = ShellFileOperations(env)
        write_result = ops.write_file(str(skill / "references" / "ops.md"), "blocked")
        patch_result = ops.patch_replace(
            str(skill / "references" / "existing.md"), "original", "changed"
        )
        outside = tmp_path / "outside"
        outside.mkdir()
        (skill / "references" / "escape").symlink_to(outside, target_is_directory=True)
        symlink_result = ops.write_file(
            str(skill / "references" / "escape" / "escaped.md"), "blocked"
        )
    finally:
        env.cleanup()

    assert write_result.error == "managed_skill_runtime_immutable"
    assert patch_result.error == "managed_skill_runtime_immutable"
    assert symlink_result.error == "managed_skill_runtime_immutable"
    assert not (outside / "escaped.md").exists()


def test_generic_file_tool_denies_managed_write_and_patch(managed_fixture, monkeypatch):
    tmp_path, _, skill = managed_fixture
    env = LocalEnvironment(cwd=str(tmp_path))
    try:
        ops = ShellFileOperations(env)
        monkeypatch.setattr("tools.file_tools._get_file_ops", lambda task_id: ops)
        from tools.file_tools import patch_tool, write_file_tool

        write_result = json.loads(
            write_file_tool(str(skill / "SKILL.md"), "blocked")
        )
        patch_result = json.loads(
            patch_tool(
                mode="replace",
                path=str(skill / "references" / "existing.md"),
                old_string="original",
                new_string="changed",
            )
        )
    finally:
        env.cleanup()

    assert write_result["error"] == "managed_skill_runtime_immutable"
    assert patch_result["error"] == "managed_skill_runtime_immutable"


@pytest.mark.parametrize(
    "command_template",
    [
        "printf blocked > {target}",
        "printf blocked >> {target}",
        "cp {source} {target}",
        "mv {source} {target}",
        "install {source} {target}",
    ],
)
def test_shell_mutations_deny_managed_runtime(
    managed_fixture, command_template
):
    tmp_path, _, skill = managed_fixture
    source = tmp_path / "source.txt"
    source.write_text("source", encoding="utf-8")
    target = skill / "references" / "shell.md"
    env = LocalEnvironment(cwd=str(tmp_path))
    try:
        result = env.execute(
            command_template.format(source=source, target=target), cwd=str(tmp_path)
        )
    finally:
        env.cleanup()

    assert result["returncode"] != 0
    assert "managed_skill_runtime_immutable" in result["output"]
    assert not target.exists()


def test_unmanaged_write_and_canonical_deployment_remain_allowed(tmp_path, monkeypatch):
    source = tmp_path / "source" / "software-development" / "managed-skill"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text(
        "---\nname: managed-skill\ndescription: source\n---\nsource\n",
        encoding="utf-8",
    )
    runtime = tmp_path / "runtime"
    manifest = deploy_runtime_authority(
        runtime,
        {
            "managed-skill": {
                "source_path": str(source),
                "source_repo": "test",
                "runtime_path": "software-development/managed-skill",
            }
        },
    )
    assert manifest["skills"]["managed-skill"]["deployment_method"] == (
        "tools.skill_authority.deploy_runtime_authority"
    )

    unmanaged = tmp_path / "unmanaged.txt"
    env = LocalEnvironment(cwd=str(tmp_path))
    try:
        result = ShellFileOperations(env).write_file(str(unmanaged), "allowed")
    finally:
        env.cleanup()
    assert result.error is None
    assert unmanaged.read_text(encoding="utf-8") == "allowed"
