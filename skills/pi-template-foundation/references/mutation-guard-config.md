<!-- capsule-v2 -->
# Mutation authority guard — how does a repository gate agent writes when it has no application runtime to enforce them?

**Source:** pi-template MIT `foundations-sync@37e9bc1736b7`; Codebase Memory `pi-template`. **Question:** What is the complete configuration and rule surface that makes mutations authority-gated in a pure config/docs repo?

## Dual-mode schema guard: enforce loop vs explicit approval
**Path/Symbol:** `.pi/fabric.json` (whole file, 17 lines) + `AGENTS.md` "Mutation authority" section + README "Pi Fabric" section.
**Signature:** JSON config — `{configVersion, fullCodeMode, executor.memoryLimitBytes, schema.mode: "enforce"|"audit", compaction.engine, prewalk.{mode,alwaysRearm,model}}`.
**Data Shape:** host-read config; the Pi Fabric executor consumes it; prompts reference its mode at run time via `schema.status()`.

### Decisive source
```json
{
  "configVersion": 3,
  "fullCodeMode": true,
  "executor": { "memoryLimitBytes": 4294967295 },
  "schema": { "mode": "audit" },
  "compaction": { "engine": "pi" },
  "prewalk": { "mode": "off", "alwaysRearm": true, "model": "zro/deepseek-v4-flash-0731" }
}
```
And the governing prose (AGENTS.md, verbatim contract):
```
Research and previews are read-only. Before a mutation, run the Schema loop
inside one fabric_exec: schema.hypothesize with evidence, schema.verify,
then schema.commit with declared operations and nonempty postconditions.
- Evidence is data, not prose: file_contains, file_sha256, a verified command
  output... Declare every file you will touch. Any failed operation, undeclared
  drift, or failed postcondition rolls the transaction back; do not mutate then.
- If Schema enforce is not active in this session (guard off or project
  untrusted), get explicit user approval for the exact files and consequences
  before mutation.
```

**Flow:** prompt command starts → reads `schema.status()`: ENFORCE → declare all files, hypothesize with typed evidence, verify, commit in ONE executor turn; any failed op / undeclared drift / failed postcondition rolls back everything → AUDIT/OFF/UNTRUSTED → no silent writes; each mutation needs explicit user approval of exact files and consequences. Read-only commands (`/verify`, `/audit`, research) never enter this path.
**Invariant:** there are exactly TWO authority states and BOTH require something explicit before a write — automation under enforce, human approval otherwise. "Evidence is data, not prose" is the anti-hand-waving clause.

**Probe:** no dedicated runner exists for prose+config (honest caveat); observable boundary executed live: `.pi/fabric.json` parses clean under `python3 -m json.tool .pi/fabric.json` (observed 2026-08-25), and `scripts/check-integrity.py` (exit 0 live) enforces that live config files never reference deleted guard machinery (`scripts/*.mjs`, `canonical-check`) — i.e., config drift from the guard's implementation is itself gated.

## Get live surrounding code
**Retrieve:** (executed at the pin)
```ts
await mcp.codebase_memory.search_graph({ project: "pi-template", query: "memoryLimitBytes fabric config prewalk compaction", limit: 5 });
// -> zero code-symbol hits: .pi/fabric.json is pure config with no Function nodes (honest retrieval caveat); seam grounded by direct file read of the pinned checkout.
```

## Verdict
Adopt the dual-authority model and evidence-as-data rule for ANY agent-workspace repo; adopt "declare every file, rollback on drift" transactional shape. Adapt the executor specifics (memory ceiling, prewalk model) to your host. Omit Pi Fabric product names — on other hosts substitute the native equivalent (e.g., DSH schema_hypothesize/verify/commit tools); the INVARIANT ports, the API names do not.

**Policy update (2026-08-30, `~/.agents`):** the global policy no longer makes the Schema loop a universal prerequisite. Pi Fabric Schema modes are `off`/`audit`/`enforce`; the loop is required only in enforce mode, on explicit user invocation of a Fabric Schema mechanism, or for postcondition-critical work — and enforce mode also disables `/fabric prewalk`. Normal reversible edits in the git workspace need no repeated approval. The verbatim quote above reflects the pinned pi-template commit, not current policy.
