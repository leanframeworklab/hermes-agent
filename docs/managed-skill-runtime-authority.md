# Managed Skill Runtime Authority

Hermes keeps two skill classes:

- User, bundled, and hub skills retain their existing runtime behavior.
- A skill listed in `.governance_manifest.json` is a deployed artifact. Its
  runtime directory is immutable to `skill_manage`, background review, curator,
  hub install/uninstall, bundled sync, and curator restore.

Background review remains active. When it identifies an improvement for a
managed skill, the central authority guard writes a JSON proposal under
`/home/deploy/.lah-skill-authority/.proposals/` (derived from the manifest
source path). The proposal includes skill identity, base source SHA and
fingerprint, operation, intended content, origin, session, and timestamp. It
does not change authoring source, runtime, or manifest.

Only `tools.skill_authority.deploy_runtime_authority` enters the explicit
canonical deployment authority context. It may converge runtime and regenerate
the provenance manifest together.
