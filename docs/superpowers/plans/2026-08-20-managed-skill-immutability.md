# Managed Skill Immutability and Background Review Authority Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep governance-managed runtime skills immutable to ordinary Hermes mutation paths while preserving self-improvement as reviewable proposals and halting terminal mandatory-governance failures.

**Architecture:** `tools.skill_authority` owns manifest-based managed-skill detection, mutation authorization, proposal staging, and explicit canonical-deployment authority. Skill manager, hub/sync, curator, and restore paths call that seam. Governance turn state exposes one terminal predicate consumed by the tool executor and conversation loop.

**Tech Stack:** Python 3.12, pytest, JSON manifests, existing Hermes tool registry and conversation loop.

**Spec:** User mission `LAH_HERMES_MANAGED_SKILL_IMMUTABILITY_AND_BACKGROUND_REVIEW_AUTHORITY_REPAIR_P0_V1`.

## Global Constraints

- Preserve primary dirty state and forensic runtime evidence.
- Never trust self-mutated runtime content or regenerate manifest around drift.
- Canonical deployment remains the only ordinary writer for managed runtime skills.
- Unmanaged/user skills keep existing behavior.
- No provider, spend, launch, force-push, reset, clean, or unrelated resolver changes.

### Task 1: Reproduce runtime mutation drift

**Files:** Test `tests/tools/test_skill_authority.py`, `tests/tools/test_skill_manager_tool.py`.

- [ ] Add temporary source/runtime/manifest fixture.
- [ ] Assert current background-origin `skill_manage` patch changes runtime while manifest remains unchanged and validation becomes invalid.
- [ ] Run focused tests and record RED evidence.

### Task 2: Add central managed-runtime policy and proposal staging

**Files:** Modify `tools/skill_authority.py`; test `tests/tools/test_skill_authority.py`.

- [ ] Add manifest entry/path resolver and `is_governance_managed_skill`.
- [ ] Add explicit `canonical_deployment_authority` context and mutation denial receipt.
- [ ] Add proposal staging with base source fingerprint, operation, content, origin, session, timestamp.
- [ ] Add tests for denied ordinary writes, staged proposal, and deployment exception.

### Task 3: Protect all ordinary skill mutation paths

**Files:** Modify `tools/skill_manager_tool.py`, `tools/skills_hub.py`, `tools/skills_sync.py`, `agent/curator_backup.py`; tests for manager, hub/sync, curator.

- [ ] Deny managed runtime mutation before filesystem writes/deletes.
- [ ] Route background-review managed mutations to proposal staging.
- [ ] Keep unmanaged behavior and canonical deployment green.
- [ ] Update background-review and curator prompts/docs with compatibility model.

### Task 4: Add terminal governance state and halt behavior

**Files:** New/modify smallest existing governance state module, `agent/tool_executor.py`, `agent/conversation_loop.py`; tests under `tests/agent` and `tests/run_agent`.

- [ ] Define terminal mandatory failure set and `state.is_terminal_failure`.
- [ ] Mark state on first terminal receipt.
- [ ] Stop further model/tool iterations for terminal governance failures only.
- [ ] Prove non-terminal `ROUTER_REQUIRED` recovery and non-governance errors remain unchanged.

### Task 5: Restore, canary, certify

- [ ] Run focused and relevant regression suites.
- [ ] Preserve the observed governance-enforcement improvement as proposal evidence.
- [ ] Deploy four critical skills through `tools.skill_authority.deploy_runtime_authority` with explicit drift confirmation.
- [ ] Revalidate authority and run safe review/turn canaries.
- [ ] Commit logical units; do not push unless credentials and normal workflow permit.

