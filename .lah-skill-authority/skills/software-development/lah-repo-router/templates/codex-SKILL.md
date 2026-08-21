---
name: lah-repo-router
description: "LAH Stack schema v4 role-aware router. Delegates to Hermes executable authority."
---

# LAH Repo Router (schema v4)

The Git tree `leanframeworklab/lah-stack-skills/lah-repo-router` is the source authority. Hermes `dry-run-route.sh` is the execution authority after validated installation. This Codex skill is a derived delegation and handoff artifact only.

Canonical ontology and mapping:

`lah-repo-router/references/repo_mappings.json` in Git; the installed Hermes path is derived and verified against it.

Run before repository inspection:

```bash
printf '%s\n' '<exact mission text>' > /tmp/lah-mission.txt
bash /home/deploy/.hermes/skills/software-development/lah-repo-router/scripts/dry-run-route.sh \
  /home/deploy/.hermes/skills/software-development/lah-repo-router/references/repo_mappings.json \
  /tmp/lah-mission.txt
```

Receipt canonical model:

```json
{
  "schema_version": "4",
  "decision": "RESOLVED | AMBIGUOUS | UNRESOLVED | BLOCKED",
  "primary_role": null,
  "repository_authority": null,
  "execution_workspace": null,
  "implementation_repo": null,
  "execution_repo": null,
  "governance_repo": null,
  "memory_repo": null,
  "context_repos": [],
  "skill_knowledge_repo": null,
  "business_asset_repo": null,
  "write_intents": [],
  "write_allowed_repos": [],
  "write_forbidden_roots": [],
  "role_evidence": {},
  "ontology_status": {},
  "explicit_target": null,
  "conflicts": [],
  "confidence": "high | medium | low"
}
```

Roles: `IMPLEMENTATION`, `EXECUTION_RUNTIME`, `GOVERNANCE`, `MEMORY`, `CONTEXT`, `SKILL_KNOWLEDGE`, `BUSINESS_ASSET`. No independent observability repository is assumed.

Rules:

1. Current implementation topology and current repo-local ownership contracts are peer evidence. Material conflict fails closed.
2. Resolve current ownership before historical prefixes or aliases. `LAH_`, `OPENCLAW_`, `CLOE_`, and old receipts are contextual only.
3. Explicit repo/path target is preserved and checked against ownership. It never overrides ownership or write policy.
4. Multiple roles and repositories are valid. Conflict means competing candidates for one required role, not different repos for different roles.
5. `AMBIGUOUS` means ownership candidates remain plausible. `UNRESOLVED` means evidence is missing or contradictory. `BLOCKED` means ownership is known but write policy/scope forbids the mutation.
6. `context_repos` are read-only unless independently resolved by an explicit mutable role.
7. `write_allowed_repos` derives only from `write_intents` and resolved ownership. No silent scope widening.
8. `repository_authority` is legacy derived compatibility, never canonical routing input.
9. CodeGraph supplies evidence only. It cannot resolve an explicit unresolved ownership conflict.
10. After routing, repo-local contracts control bootstrap, CodeGraph freshness, inspection, and writes.

Active memory authority: `cartelogic-v2`. Archived OpenClaw agent-memory is non-writable.

Validate documentation/mapping drift:

```bash
node /home/deploy/.hermes/skills/software-development/lah-repo-router/scripts/validate-routing-drift.cjs
```
