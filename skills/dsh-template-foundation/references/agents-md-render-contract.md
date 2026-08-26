<!-- capsule-v2 -->
# AGENTS.md render discipline — what makes an auto-loaded agent-rules file trustworthy?

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** Which authoring rules keep a project's AGENTS.md load-bearing (verified facts, enforced conventions, safety boundaries) instead of decaying into generic doctrine the agent can ignore?

## Verified-only AGENTS.md authoring guide
**Path/Symbol:** `.dsh/templates/agents.md` (whole file, 113 lines); "How to render" rules 1–8 (:9–17), anti-copy rule (:19–20), rendered skeleton sections (`Golden rule`, `Repository facts`, `Safety boundaries`, `Repository invariants`, `Operational traps`, `Product map`, `Conventions`, `Verification evidence`).
**Signature:** each instruction must be one of: verified repository fact, measurable outcome, irreversible-action boundary, or automation-inexpressible trap; conventions are included ONLY with "a mechanical check or an external protocol".
**Data Shape:** skeleton mandates a golden-rule command block ("State exactly what the command runs, what a green result proves"), an Evidence line per section (`Evidence: [validator, test, workflow, manifest, or config]`), and host-side capabilities explicitly demoted to non-clone-dependencies.

### Decisive source
```markdown
1. Discover the repository's real commands and run them before naming them.
2. Select one canonical completion command. If none exists, list the verified
   command set and mark the missing aggregate check.
5. Include destructive-action and secret boundaries. Keep other workflow and
   style preferences out of the rendered file unless a checker enforces them.
Do not copy generic coding doctrine, research philosophy, prose rules, planning
rituals, or examples from another repository. Do not invent commands.
```

**Flow:** (1) run candidate commands BEFORE writing them down; (2) pick ONE canonical completion command and state exactly what green proves; (3) record invariants only with file/command evidence; (4) carry destructive-action + secret boundaries always, everything else only when a checker enforces it; (5) keep detailed architecture out of AGENTS.md — link an on-demand record (`.dsh/templates/project.md` shape); (6) preview material changes before writing.
**Invariant:** nothing unverifiable enters the file — no invented commands, no copied doctrine; every convention cites its enforcement point (the live instance names `node scripts/check.mjs` as both golden rule AND commit-convention enforcement point); the file stays short because depth lives in linked on-demand records.
**Probe:** anchor grep `'Do not copy generic coding doctrine' .dsh/templates/agents.md` → 1 hit; live instance satisfies the same contract (`AGENTS.md` root: golden-rule block = `node scripts/check.mjs`, Evidence lines under Repository facts/Conventions). No test runner exists (coverage caveat: deterministic anchors only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "mgraph wrapper codebase-memory cli", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-legal-claim taxonomy (fact / outcome / boundary / trap) and the evidence-per-section skeleton for any auto-loaded agent instructions file; adopt the "one canonical completion command" rule. Adapt section set to the host harness. Omit the pi-specific on-demand-record linkage if your target has no doc templates.
