<!-- capsule-v2 -->
# Template surface — DSH-native format templates mapped to DSH capabilities

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** How does a DSH template provide a full set of source-format document templates (adr, design, prd, roadmap, state, tasks, tech-stack, etc.) and map each to the DSH surface that drives it?

## DSH-native template surface
**Path/Symbol:** `.dsh/templates/` (13 files: adr, agents, design, issue, prd, project, proposal, README, roadmap, state, tasks, tech-stack, user) + `.dsh/templates/README.md` (the mapping table). **Signature:** copy a template into the working set and fill it in — there is no `/init` step in DSH; `AGENTS.md` is read directly at session start.
**Data Shape:** each template maps to the DSH surfaces it drives. Examples: `adr.md` → `schema_*` gate + `fabric_mesh` (decisions topic); `prd.md` → `.dsh/prompts/plan.md` + `goals/` + `fabric_mesh`; `tasks.md` → `.dsh/prompts/ship.md` + `fabric_mesh` work actors; `tech-stack.md` → `fovea_sketch`/`focus` + `AGENTS.md` + `check.mjs`; `user.md` → session memory + `goals/` (no secrets).

### Decisive source
```text
| pi-template (.pi/templates/) | DSH-native template | Primary DSH surfaces |
| adr.md       | .dsh/templates/adr.md      | schema_* gate, fabric_mesh (decisions topic) |
| prd.md       | .dsh/templates/prd.md      | .dsh/prompts/plan.md, goals/, fabric_mesh |
| tasks.md     | .dsh/templates/tasks.md    | .dsh/prompts/ship.md, fabric_mesh work actors |
| tech-stack.md| .dsh/templates/tech-stack.md | fovea_sketch/focus, AGENTS.md, check.mjs |
| user.md      | .dsh/templates/user.md     | session memory, goals/ (no secrets) |
```
```md
# PRD / Spec
> Template notes: replace placeholders; if a section cannot be filled
> confidently, mark it [NEEDS CLARIFICATION: reason] and resolve before
> planning. Delete this block when done.
**Work ID:** [slug or none]  **Repository:** [owner/repo or none]
**Status:** Draft | In Review | Approved
## Problem Statement
- **What problem are we solving?** [Description, user and business impact]
- **Why now?** [Trigger / cost of inaction]
```

**Flow:** (1) copy a template into the working set; (2) fill it in, marking uncertain sections `[NEEDS CLARIFICATION: reason]`; (3) the template drives the matching DSH surface (schema gate, fabric_mesh topic/state/actors, goals, fovea discovery, prompts); (4) delete the template-note block when done.

**Invariant:** templates are source-format documents (no `/init` render step in DSH); every template maps to at least one DSH surface; `user.md`/secrets never hold real credentials; uncertain sections are marked `[NEEDS CLARIFICATION]` and resolved before planning.

**Probe:** no direct test file exists. Verified by direct source read (`.dsh/templates/README.md` + the template files). The mapping table and `[NEEDS CLARIFICATION]` discipline are the executable contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "templates adr prd tech-stack fabric_mesh fovea", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the source-format template surface and the template→DSH-surface mapping discipline. Adapt the template set and the surface mapping to the host. Omit templates the host does not use (e.g. `issue.md` if no GitHub issue forms).
