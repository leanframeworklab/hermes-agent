"""Central runtime skill authority manifest and deterministic drift checks."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from hermes_constants import get_hermes_home


CRITICAL_SKILLS = (
    "lah-workflow",
    "lah-workflow-small-model",
    "lah-repo-router",
    "mission-decomposer",
)
MANIFEST_FILENAME = ".governance_manifest.json"
FILE_DEPLOYMENT_AUTHORITY = "tools.skill_authority.deploy_runtime_authority"
APPROVED_FILE_SOURCE_ROOTS = {
    "leanframeworklab/lah-stack-skills": Path("/home/deploy/lah-stack-repos/lah-stack-skills").resolve(),
}
APPROVED_FILE_RUNTIME_TARGETS = {
    "lah-workflow": "lah-workflow/SKILL.md",
}
APPROVED_FILE_RUNTIME_CONSUMERS = {
    "codex": Path("/home/deploy/.codex/skills").resolve(),
}


@dataclass(frozen=True)
class ManagedSkillMutationDecision:
    """Central, caller-independent decision for one runtime mutation."""

    allowed: bool
    managed: bool
    action: str
    reason: str


def _manifest_entry_for_path(
    path: Path, runtime_root: Path
) -> tuple[str, Mapping[str, Any]] | None:
    try:
        relative = Path(os.path.abspath(path)).relative_to(
            Path(os.path.abspath(runtime_root))
        )
    except (OSError, ValueError):
        return None
    try:
        manifest = json.loads(manifest_path(runtime_root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    entries = manifest.get("skills", {})
    if not isinstance(entries, Mapping):
        return None
    for name, entry in entries.items():
        if not isinstance(entry, Mapping):
            continue
        declared = Path(str(entry.get("runtime_path", "")))
        if relative == declared or declared in relative.parents:
            return str(name), entry
    file_entries = manifest.get("file_mappings", {})
    if isinstance(file_entries, Mapping):
        for name, entry in file_entries.items():
            if not isinstance(entry, Mapping):
                continue
            declared = Path(str(entry.get("runtime_file", "")))
            if relative == declared:
                return str(name), entry
    return None


def is_governance_managed_skill(
    path_or_name: str | Path, runtime_root: Path | None = None
) -> bool:
    """Return true when name/path is declared as a managed runtime artifact."""
    root = (runtime_root or (get_hermes_home() / "skills")).resolve()
    if isinstance(path_or_name, Path) or os.sep in str(path_or_name):
        return _manifest_entry_for_path(Path(path_or_name), root) is not None
    try:
        manifest = json.loads(manifest_path(root).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    entries = manifest.get("skills", {})
    return isinstance(entries, Mapping) and isinstance(
        entries.get(str(path_or_name)), Mapping
    )


def check_managed_runtime_mutation(
    target_path_or_skill: str | Path,
    operation: str,
    runtime_root: Path | None = None,
) -> ManagedSkillMutationDecision:
    """Deny ordinary mutation of manifest-declared runtime skill trees."""
    root = (runtime_root or (get_hermes_home() / "skills")).resolve()
    target = Path(target_path_or_skill)
    looks_like_path = isinstance(target_path_or_skill, Path) or os.sep in str(
        target_path_or_skill
    )
    managed = (
        is_governance_managed_skill(target, root)
        if looks_like_path
        else is_governance_managed_skill(str(target_path_or_skill), root)
    )
    if not managed:
        return ManagedSkillMutationDecision(
            True, False, "ALLOW", "target is not governance-managed"
        )
    return ManagedSkillMutationDecision(
        False, True, "DENY", f"managed runtime mutation: {operation}"
    )


def check_managed_runtime_command(
    command: str,
    *,
    cwd: str | Path = "",
    runtime_root: Path | None = None,
) -> ManagedSkillMutationDecision:
    """Fail closed for shell commands that target declared runtime trees."""
    root = (runtime_root or (get_hermes_home() / "skills")).resolve()
    try:
        manifest = json.loads(manifest_path(root).read_text(encoding="utf-8"))
        entries = manifest.get("skills", {})
    except (OSError, json.JSONDecodeError):
        return ManagedSkillMutationDecision(True, False, "ALLOW", "manifest unavailable")
    if not isinstance(entries, Mapping):
        return ManagedSkillMutationDecision(True, False, "ALLOW", "manifest has no skills")

    # Stderr suppression is read-only plumbing, not a write to the managed
    # tree. Remove it before looking for output redirection. Likewise, plain
    # ``sed -n`` is a read command; only in-place sed is a mutation here.
    command_for_mutation_scan = re.sub(r"\s*\d?>/dev/null\b", "", command)
    mutation_hint = bool(
        re.search(
            r">>?\s*|\b(?:cp|mv|install|rm|rmdir|mkdir|touch|tee|perl)\b"
            r"|\bsed\s+-[^\s]*i\b"
            r"|\b(?:write_text|write_bytes|writeFile|unlink|rename|copy|move)\s*\(",
            command_for_mutation_scan,
        )
    )
    if not mutation_hint:
        return ManagedSkillMutationDecision(True, False, "ALLOW", "read-only shell command")

    resolved_cwd = Path(cwd).resolve() if cwd else None
    for entry in entries.values():
        if not isinstance(entry, Mapping) or not entry.get("runtime_path"):
            continue
        skill_dir = (root / str(entry["runtime_path"])).resolve()
        if str(skill_dir) in command or str(root) in command:
            return ManagedSkillMutationDecision(
                False, True, "DENY", "managed runtime shell target"
            )
        if resolved_cwd is not None:
            try:
                resolved_cwd.relative_to(skill_dir)
            except ValueError:
                continue
            return ManagedSkillMutationDecision(
                False, True, "DENY", "managed runtime shell cwd"
            )
    return ManagedSkillMutationDecision(True, False, "ALLOW", "shell target unmanaged")


def classify_skill_identifier(identifier: str, canonical_names: set[str]) -> str:
    """Classify a reference without changing resolver compatibility behavior."""
    if identifier in canonical_names:
        return "VALID_CANONICAL_NAME"
    if ":" in identifier and identifier.count(":") == 1:
        return "VALID_PLUGIN_NAMESPACE"
    if "/" in identifier:
        return "CATEGORY_PATH_USED_AS_IDENTIFIER"
    return "UNKNOWN_SKILL"


def manifest_path(runtime_root: Path | None = None) -> Path:
    root = runtime_root or (get_hermes_home() / "skills")
    return root / MANIFEST_FILENAME


def _skill_fingerprint(skill_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in skill_dir.rglob("*") if p.is_file() and not p.is_symlink()):
        relative = path.relative_to(skill_dir).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _frontmatter_name(skill_dir: Path) -> str:
    path = skill_dir / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    in_frontmatter = False
    for line in text.splitlines():
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter and line.strip().startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return skill_dir.name


def _find_skill(runtime_root: Path, name: str) -> Path | None:
    matches = []
    for skill_md in runtime_root.rglob("SKILL.md"):
        if any(part in {".archive", ".git", "node_modules"} for part in skill_md.parts):
            continue
        try:
            if _frontmatter_name(skill_md.parent) == name:
                matches.append(skill_md.parent)
        except (OSError, UnicodeError):
            continue
    if len(matches) != 1:
        return None
    return matches[0]


def _git_sha(path: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_file_sha256(root: Path, source_sha: str, relative: Path) -> str | None:
    try:
        data = subprocess.check_output(
            ["git", "-C", str(root), "show", f"{source_sha}:{relative.as_posix()}"],
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return hashlib.sha256(data).hexdigest()


def _relative_file_path(value: str, error: str) -> Path:
    candidate = Path(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(error)
    return candidate


def _path_has_symlink_component(path: Path, root: Path) -> bool:
    current = root
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _plan_file_deployments(
    runtime_root: Path,
    declarations: Mapping[str, Mapping[str, Any]],
    *,
    approved_source_roots: Mapping[str, Path],
    approved_runtime_targets: Mapping[str, str],
    deployment_authority: str | None,
) -> list[dict[str, Any]]:
    if deployment_authority != FILE_DEPLOYMENT_AUTHORITY:
        raise ValueError("SKILL_DEPLOYMENT_AUTHORITY_REQUIRED")
    root = runtime_root.resolve()
    plans: list[dict[str, Any]] = []
    for name, declaration in sorted(declarations.items()):
        source_repo = str(declaration.get("source_repo", ""))
        approved_root = approved_source_roots.get(source_repo)
        source_root = Path(str(declaration.get("source_path", ""))).resolve()
        if approved_root is None or source_root != Path(approved_root).resolve():
            raise ValueError(f"UNDECLARED_SKILL_DEPLOYMENT_SOURCE: {name}")
        consumer = declaration.get("runtime_consumer")
        approved_file_consumer = APPROVED_FILE_RUNTIME_CONSUMERS.get(str(consumer))
        if consumer and approved_file_consumer:
            if root != approved_file_consumer:
                raise ValueError(f"UNDECLARED_SKILL_DEPLOYMENT_TARGET: {name}")
        elif consumer:
            raise ValueError(f"UNDECLARED_SKILL_DEPLOYMENT_TARGET: {name}")
        source_relative = _relative_file_path(
            str(declaration.get("source_file", "")),
            f"UNDECLARED_SKILL_DEPLOYMENT_SOURCE: {name}",
        )
        source_file = source_root / source_relative
        if _path_has_symlink_component(source_file, source_root) or not source_file.is_file():
            raise ValueError(f"UNDECLARED_SKILL_DEPLOYMENT_SOURCE: {name}")
        runtime_relative = _relative_file_path(
            str(declaration.get("runtime_file", "")),
            f"UNDECLARED_SKILL_DEPLOYMENT_TARGET: {name}",
        )
        if approved_runtime_targets.get(name) != runtime_relative.as_posix():
            raise ValueError(f"UNDECLARED_SKILL_DEPLOYMENT_TARGET: {name}")
        target_file = root / runtime_relative
        if _path_has_symlink_component(target_file, root):
            raise ValueError(f"UNDECLARED_SKILL_DEPLOYMENT_TARGET: {name}")
        source_fingerprint = _file_sha256(source_file)
        declared_fingerprint = declaration.get("source_fingerprint")
        if declared_fingerprint and declared_fingerprint != source_fingerprint:
            raise ValueError(f"SKILL_SOURCE_FINGERPRINT_MISMATCH: {name}")
        source_sha = declaration.get("source_sha") or _git_sha(source_root)
        if declaration.get("source_sha") and _git_sha(source_root) != declaration["source_sha"]:
            raise ValueError(f"SKILL_SOURCE_FINGERPRINT_MISMATCH: {name}")
        if declaration.get("source_sha"):
            committed_fingerprint = _git_file_sha256(source_root, declaration["source_sha"], source_relative)
            if committed_fingerprint != source_fingerprint:
                raise ValueError(f"SKILL_SOURCE_FINGERPRINT_MISMATCH: {name}")
        target_fingerprint = _file_sha256(target_file) if target_file.is_file() else None
        plans.append({
            "logical_skill": name,
            "source_repo": source_repo,
            "runtime_consumer": consumer,
            "source_path": str(source_root),
            "source_file": source_relative.as_posix(),
            "source_sha": source_sha,
            "source_fingerprint": source_fingerprint,
            "runtime_file": runtime_relative.as_posix(),
            "target": str(target_file),
            "target_current_fingerprint": target_fingerprint,
            "expected_change": target_fingerprint != source_fingerprint,
        })
    return plans


def plan_file_runtime_authority(
    runtime_root: Path,
    declarations: Mapping[str, Mapping[str, Any]],
    *,
    approved_source_roots: Mapping[str, Path] | None = None,
    approved_runtime_targets: Mapping[str, str] | None = None,
    deployment_authority: str | None = FILE_DEPLOYMENT_AUTHORITY,
) -> list[dict[str, Any]]:
    return _plan_file_deployments(
        runtime_root,
        declarations,
        approved_source_roots=approved_source_roots or APPROVED_FILE_SOURCE_ROOTS,
        approved_runtime_targets=approved_runtime_targets or APPROVED_FILE_RUNTIME_TARGETS,
        deployment_authority=deployment_authority,
    )


def load_file_deployment_declarations(
    manifest_file: Path, runtime_consumer: str
) -> dict[str, Mapping[str, Any]]:
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("SKILL_DEPLOYMENT_MANIFEST_INVALID") from exc
    entries = manifest.get("file_mappings")
    if not isinstance(entries, Mapping):
        raise ValueError("SKILL_DEPLOYMENT_MANIFEST_INVALID")
    selected = {
        str(name): entry
        for name, entry in entries.items()
        if isinstance(entry, Mapping) and entry.get("runtime_consumer") == runtime_consumer
    }
    if not selected:
        raise ValueError(f"UNDECLARED_SKILL_DEPLOYMENT_TARGET: {runtime_consumer}")
    return selected


def validate_file_runtime_authority(
    runtime_root: Path, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    root = runtime_root.resolve()
    errors: list[str] = []
    results: dict[str, Any] = {}
    entries = manifest.get("file_mappings", {})
    if not isinstance(entries, Mapping):
        return {"valid": False, "errors": ["file deployment manifest missing file_mappings"], "files": {}}
    for name, entry in entries.items():
        target = root / str(entry.get("runtime_file", ""))
        source = Path(str(entry.get("source_path", ""))) / str(entry.get("source_file", ""))
        source_fingerprint = _file_sha256(source) if source.is_file() else None
        runtime_fingerprint = _file_sha256(target) if target.is_file() else None
        results[name] = {
            "source_fingerprint": source_fingerprint,
            "runtime_fingerprint": runtime_fingerprint,
            "match": source_fingerprint == runtime_fingerprint,
        }
        if source_fingerprint != entry.get("source_fingerprint"):
            errors.append(f"{name}: source fingerprint drift")
        if runtime_fingerprint != entry.get("runtime_fingerprint"):
            errors.append(f"{name}: runtime fingerprint drift")
        if source_fingerprint != runtime_fingerprint:
            errors.append(f"{name}: content drift between source and runtime")
    return {"valid": not errors, "errors": errors, "files": results}


def build_manifest(runtime_root: Path, declarations: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    skills: dict[str, Any] = {}
    for name, declaration in sorted(declarations.items()):
        runtime_dir = _find_skill(runtime_root, name)
        if runtime_dir is None:
            raise ValueError(f"runtime skill not uniquely discoverable: {name}")
        source_dir = Path(str(declaration["source_path"])).resolve()
        skills[name] = {
            "invocation_name": name,
            "source_repo": declaration.get("source_repo"),
            "source_path": str(source_dir),
            "source_sha": declaration.get("source_sha") or _git_sha(source_dir),
            "source_content_sha256": _skill_fingerprint(source_dir),
            "runtime_path": str(runtime_dir.relative_to(runtime_root)),
            "runtime_content_sha256": _skill_fingerprint(runtime_dir),
        }
    return {"schema_version": 1, "skills": skills}


def deploy_runtime_authority(
    runtime_root: Path,
    declarations: Mapping[str, Mapping[str, Any]],
    *,
    file_declarations: Mapping[str, Mapping[str, Any]] | None = None,
    deployment_authority: str | None = None,
    allow_runtime_drift: bool = False,
) -> dict[str, Any]:
    """Atomically deploy declared skill sources and write one provenance manifest.

    Existing target drift is rejected unless the caller explicitly confirms it
    was preserved and reviewed. This keeps raw manual copying out of the
    deployment contract while allowing a deliberate first convergence.
    """
    runtime_root = runtime_root.resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    file_plans = (
        plan_file_runtime_authority(
            runtime_root,
            file_declarations,
            deployment_authority=deployment_authority,
        )
        if file_declarations
        else []
    )
    if not allow_runtime_drift:
        for item in file_plans:
            if item["expected_change"] and item["target_current_fingerprint"] is not None:
                raise ValueError(f"unexpected runtime drift: {item['logical_skill']}")
    plans: list[tuple[str, Path, Path, str, str | None, Mapping[str, Any]]] = []
    for name, declaration in sorted(declarations.items()):
        source_dir = Path(str(declaration["source_path"])).resolve()
        if not (source_dir / "SKILL.md").is_file():
            raise ValueError(f"source skill missing: {name}")
        runtime_path = declaration.get("runtime_path")
        target_dir = (
            runtime_root / str(runtime_path)
            if runtime_path
            else _find_skill(runtime_root, name)
        )
        if target_dir is None:
            raise ValueError(f"runtime skill not uniquely discoverable: {name}")
        target_dir = Path(target_dir).resolve()
        if target_dir.exists():
            target_hash = _skill_fingerprint(target_dir)
            source_hash = _skill_fingerprint(source_dir)
            if target_hash != source_hash and not allow_runtime_drift:
                raise ValueError(f"unexpected runtime drift: {name}")
        else:
            source_hash = _skill_fingerprint(source_dir)
        source_sha = declaration.get("source_sha") or _git_sha(source_dir)
        plans.append((name, source_dir, target_dir, source_hash, source_sha, declaration))

    staging_root = Path(tempfile.mkdtemp(prefix=".governance-deploy-", dir=runtime_root.parent))
    manifest: dict[str, Any] = {"schema_version": 1, "skills": {}}
    if file_plans:
        manifest["file_mappings"] = {}
    try:
        for name, source_dir, target_dir, source_hash, source_sha, declaration in plans:
            relative = target_dir.relative_to(runtime_root)
            staged_dir = staging_root / "payload" / relative
            staged_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_dir, staged_dir)
            runtime_hash = _skill_fingerprint(staged_dir)
            manifest["skills"][name] = {
                "invocation_name": name,
                "source_repo": declaration.get("source_repo"),
                "source_path": str(source_dir),
                "source_sha": source_sha,
                "source_content_sha256": source_hash,
                "runtime_path": relative.as_posix(),
                "runtime_content_sha256": runtime_hash,
                "deployment_method": "tools.skill_authority.deploy_runtime_authority",
                "deployed_at": datetime.now(timezone.utc).isoformat(),
            }
        for item in file_plans:
            staged_file = staging_root / "file-payload" / item["runtime_file"]
            staged_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(item["source_path"]) / item["source_file"], staged_file)
            if _file_sha256(staged_file) != item["source_fingerprint"]:
                raise ValueError(f"SKILL_SOURCE_FINGERPRINT_MISMATCH: {item['logical_skill']}")
            manifest["file_mappings"][item["logical_skill"]] = {
                "invocation_name": item["logical_skill"],
                "source_repo": item["source_repo"],
                "runtime_consumer": item["runtime_consumer"],
                "source_path": item["source_path"],
                "source_file": item["source_file"],
                "source_sha": item["source_sha"],
                "source_fingerprint": item["source_fingerprint"],
                "runtime_file": item["runtime_file"],
                "runtime_fingerprint": item["source_fingerprint"],
                "deployment_method": FILE_DEPLOYMENT_AUTHORITY,
            }

        for _, _, target_dir, _, _, _ in plans:
            relative = target_dir.relative_to(runtime_root)
            staged_dir = staging_root / "payload" / relative
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged_dir, target_dir)
        for item in file_plans:
            staged_file = staging_root / "file-payload" / item["runtime_file"]
            target_file = Path(item["target"])
            target_file.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged_file, target_file)

        manifest_file = manifest_path(runtime_root)
        manifest_tmp = manifest_file.with_name(f"{manifest_file.name}.tmp")
        manifest_tmp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.replace(manifest_tmp, manifest_file)
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)
    return manifest


def validate_runtime_authority(
    runtime_root: Path,
    manifest: Mapping[str, Any],
    *,
    critical: Sequence[str] = CRITICAL_SKILLS,
) -> dict[str, Any]:
    errors: list[str] = []
    entries = manifest.get("skills") if isinstance(manifest, Mapping) else None
    if manifest.get("schema_version") != 1 or not isinstance(entries, Mapping):
        return {"valid": False, "errors": ["invalid governance manifest schema"], "skills": {}}

    discovered: dict[str, list[Path]] = {}
    for skill_md in runtime_root.rglob("SKILL.md"):
        if any(part in {".archive", ".git", "node_modules"} for part in skill_md.parts):
            continue
        try:
            discovered.setdefault(_frontmatter_name(skill_md.parent), []).append(skill_md.parent)
        except (OSError, UnicodeError):
            continue
    for name, paths in discovered.items():
        if len(paths) > 1:
            errors.append(f"duplicate canonical skill name: {name}")

    results: dict[str, Any] = {}
    for name in critical:
        entry = entries.get(name)
        if not isinstance(entry, Mapping):
            errors.append(f"{name}: missing manifest entry")
            continue
        if entry.get("invocation_name") != name:
            errors.append(f"{name}: invocation identity missing or mismatched")
        if not entry.get("source_repo"):
            errors.append(f"{name}: source repository missing")
        runtime_dir = runtime_root / str(entry.get("runtime_path", ""))
        source_dir = Path(str(entry.get("source_path", "")))
        if not (runtime_dir / "SKILL.md").is_file():
            errors.append(f"{name}: runtime skill missing")
            continue
        if not (source_dir / "SKILL.md").is_file():
            errors.append(f"{name}: source skill missing")
            continue
        if _frontmatter_name(runtime_dir) != name:
            errors.append(f"{name}: runtime canonical name mismatch")
        source_hash = _skill_fingerprint(source_dir)
        runtime_hash = _skill_fingerprint(runtime_dir)
        declared_source_hash = entry.get("source_content_sha256")
        declared_runtime_hash = entry.get("runtime_content_sha256")
        if declared_source_hash and declared_source_hash != source_hash:
            errors.append(f"{name}: declared source fingerprint mismatch")
        if declared_runtime_hash and declared_runtime_hash != runtime_hash:
            errors.append(f"{name}: declared runtime fingerprint mismatch")
        declared_sha = entry.get("source_sha")
        current_sha = _git_sha(source_dir) if declared_sha else None
        if declared_sha and current_sha and declared_sha != current_sha:
            errors.append(f"{name}: source Git SHA drift")
        results[name] = {
            "source_content_sha256": source_hash,
            "runtime_content_sha256": runtime_hash,
            "match": source_hash == runtime_hash,
            "source_sha": current_sha or declared_sha,
            "invocation_name": entry.get("invocation_name"),
        }
        if source_hash != runtime_hash:
            errors.append(f"{name}: content drift between source and runtime")
    return {"valid": not errors, "errors": errors, "skills": results}


def load_runtime_authority_status(runtime_root: Path | None = None) -> dict[str, Any]:
    root = runtime_root or (get_hermes_home() / "skills")
    path = manifest_path(root)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"valid": False, "errors": [f"missing or invalid manifest: {path}"], "skills": {}}
    return validate_runtime_authority(root, manifest)


def load_file_runtime_authority_status(runtime_root: Path) -> dict[str, Any]:
    root = runtime_root.resolve()
    path = manifest_path(root)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"valid": False, "errors": [f"missing or invalid manifest: {path}"], "files": {}}
    return validate_file_runtime_authority(root, manifest)
