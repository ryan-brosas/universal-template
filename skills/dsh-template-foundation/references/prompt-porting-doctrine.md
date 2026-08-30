<!-- capsule-v2 -->
# Prompt-command doctrine — how do procedural slash-commands port onto a new harness?

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** What is the reusable pattern for carrying a proven command set (init/plan/ship/fix/…) from one coding-agent harness to another without losing its discipline?

## pi→DSH prompt-porting table with per-command surface mapping
**Path/Symbol:** `.dsh/prompts/README.md` (whole file, 52 lines) — the nine-row porting table (`| pi command | DSH-native prompt | Primary DSH surfaces |`), "How it is wired" doc-citation block, "Activating in a project" mount section; each `.dsh/prompts/<name>.md` frontmatter carries only `name` + `description`.
**Signature:** row shape `<old-command> → <new-file.md> → <surface list>`; e.g. `/plan → .dsh/prompts/plan.md → codebase-driven-development, evidence-router, fovea_focus/impact, fabric_mesh`; `/research → .dsh/prompts/research.md → evidence-router, codebase-memory + context7 + exa + deepwiki MCP`.
**Data Shape:** prompts are plain durable markdown (no executable); activation is EXPLICIT — "DSH does not auto-scan `.dsh/prompts/` for commands (only `.dsh/skills/` is auto-scanned by `dsh-skill-filesystem`)" — so a plugin/config mount is required; every behavioral claim cites harness docs (capability-seams, cordis-tutorial 03/05/07).

### Decisive source
```markdown
| /ship    | .dsh/prompts/ship.md   | shipping-and-launch, run_code, schema gate, fabric_mesh
| /research| .dsh/prompts/research.md | evidence-router, codebase-memory + context7 + exa + deepwiki MCP

These `.md` files are the durable prompt text. To make them actual DSH
slash-commands, the bundled command plugin registers each one via
`ctx.commands.register` and feeds the file body into the agent on invocation.

- DSH does not auto-scan `.dsh/prompts/` for commands (only `.dsh/skills/` is
  auto-scanned). Mount the plugin from a project config row with a relative path.
```

**Flow:** (1) keep each command's PROCEDURE as a standalone `.md` with minimal frontmatter; (2) map every old-harness tool reference onto the new harness's surface in a visible table row (fovea_* for discovery, schema gate for mutations, fabric_mesh for durable state, check.mjs for verification); (3) document the exact wiring mechanism with doc citations; (4) require an explicit mount step because prompt dirs are not auto-discovered.
**Invariant:** the doctrine text is portable and harness-independent while the surface column is host-specific — porting = rewriting the surface column, never the procedure; the escalation ladder inside `/research` (graph → fovea → deepwiki → context7 → exa → single fetch, "escalate only after a named gap", bounded to one project/symbol depth and coverage-checked before asserting absence) is itself a reusable research discipline; `/ship`'s stop-set (BLOCKED after same-failure-twice / destructive action / ambiguity) is the reusable safety boundary.
**Probe:** anchor grep `/verify` in `.dsh/prompts/README.md` → line 12 (also evidences the phantom-command defect); frontmatter census: all 8 prompt files carry exactly `name`+`description`. No test runner exists (coverage caveat: deterministic anchors only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "prompts init ship audit DSH-native", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the porting-table pattern (durable markdown procedures × explicit host-surface mapping × cited wiring docs) whenever moving a command culture between agent harnesses; adopt the research escalation ladder and ship stop-set verbatim as disciplines. Adapt the surface names, plugin mechanism, and mount syntax to the target harness. Omit auto-scan assumptions — check whether your harness scans prompt dirs at all before relying on it.
