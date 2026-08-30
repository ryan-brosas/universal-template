<!-- capsule-v2 -->
# Goal-ledger bootstrap — how does an agent run a multi-phase init WITHOUT fabricating progress?

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** What file shape lets a goal re-issue across agent sessions and forces every claim to carry evidence instead of invented status?

## Active-goal ledger with evidence-or-[NEEDS CLARIFICATION] contract
**Path/Symbol:** `goals/template-init.md` (whole file, 37 lines); frontmatter `name`/`goal`/`updated`; sections `Objective`, `Acceptance criteria`, `Ledger (phase plan + progression)`, `Durable state`, `Evidence`.
**Signature:** frontmatter `name: <slug>`; `goal:` one-sentence objective; ledger rows `- [x| ] <Phase> — <what ran / what was written> (<evidence>)`.
**Data Shape:** the ledger is BOTH plan and progression record — each phase row cites its evidence inline (`node scripts/check.mjs (exit 0)`, `git log --oneline -20 (conventions)`, `git status` paths); unverifiable facts are written as `[NEEDS CLARIFICATION: reason]`, never guessed; the active goal is "re-issued each wrapper until the ledger below shows complete".

### Decisive source
```markdown
Active goal re-issued each wrapper until the ledger below shows complete.

## Objective
Run /init on the dsh-template: verify the cloned baseline, correct AGENTS.md so
its claims match the live repo, land the command-plugin surface, and record a
durable goal + active context. No fabricated roadmap.

## Ledger (phase plan + progression)
- [x] Detect   — ran node scripts/check.mjs (exit 0), git log --oneline -20 (conventions), mapped .dsh/ surface.
- [x] Compose  — AGENTS.md: added .dsh/plugins/ to product surface; corrected foundation-bar claim ...
- [ ] Verify   — re-read AGENTS.md + run node scripts/check.mjs; report per-artifact (pending final run).

## Durable state
- Do not invent versions, commands, or policies — cite file:line / command output /
  user answer, or mark [NEEDS CLARIFICATION: reason].
```

**Flow:** (1) write the goal file FIRST with unchecked phase rows before doing the work; (2) each phase runs, then its row is checked off WITH its evidence appended in the same line; (3) anything not verifiable becomes `[NEEDS CLARIFICATION: reason]` (e.g. the real repo's `continue-foundation reuse-guide` gap and "confirm next authoring unit" questions); (4) the goal re-enters every session wrapper until completion criteria are demonstrably met; (5) durable side-state (fabric_mesh updates) is declared in the same file.
**Invariant:** no roadmap invention ("No fabricated roadmap") and no uncited claims — a claim without evidence is a draft; the anti-fabrication valve means unknowns surface as visible markers rather than confident lies. The instance docs at the template root (`project.md`, `roadmap.md`, `tech-stack.md`) are this same contract applied to whole documents: every section ends with an Evidence block, unverified values marked `[NEEDS CLARIFICATION: reason]` (live instances: `project.md` "Instantiated from `.dsh/templates/project.md`", `tech-stack.md` Commands table carrying verified dates + exit codes).
**Probe:** anchor grep `'re-issued each wrapper' goals/template-init.md` → 1 hit; live instances carry the same contract (`grep -c 'NEEDS CLARIFICATION' project.md roadmap.md tech-stack.md` ≥1 each). No test runner exists (coverage caveat: deterministic anchors only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "goal template-init ledger", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the goal-file-as-resume-ledger (frontmatter identity + acceptance criteria + evidence-cited checkbox rows + explicit NEEDS-CLARIFICATION valve) for any long-running agentic init/migration. Adapt section names and the durable-state backend to the host. Omit the fabric_mesh coupling if your host has no shared state store — the ledger file alone still carries the resume.
