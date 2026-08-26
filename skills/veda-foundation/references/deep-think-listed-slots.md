<!-- capsule-v2 -->
# Listed-mode solver slots — how do you pin one exact backend/model/reasoning per solver while keeping prompts byte-identical?

**Source:** veda MIT `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`; Codebase Memory `veda`. **Question:** How does a roster of explicitly-configured solvers project into ensemble members, and when must module injection be suppressed entirely?

## planSolverModules + buildSolverMembers projection seams
**Path/Symbol:** `src/pipelines/deep-think.ts:planSolverModules` (:758-771), `buildSolverMembers` (:779-827); both EXPORTED pure functions ("Exported for tests (pure planning seam; no backend I/O)").
**Signature:** `planSolverModules(solver: SolverOptions): (ReasoningModule | undefined)[]`; `buildSolverMembers(prompt, solver, modules) → {members: EnsembleMember[], metas: MemberMeta[]}`.
**Data Shape:** `SolverSlotSpec {backend, model, reasoning?}`; k derives as `solver.slots?.length ?? solver.k` (roster length is the ONLY thing that may set roster size in listed mode); member id = `solver-<i>-<backend>-<model>-<category/module_id>` or `uniform/none`.

### Decisive source
```ts
if (solver.uniformPrompt) {
  return new Array(k).fill(undefined);
}
...
const systemPrompt = module ? buildDeepSolverSystemPrompt({ module }) : SOLVER_SYSTEM_PROMPT,
...
// First slot per backend, for trace/notification display. Member construction
// reads slot.model directly, so same-backend duplicates with distinct models work.
```

**Flow:** uniform-prompt mode (listed slots without zipped modules) fills the module array with `undefined` so EVERY member gets the byte-identical SOLVER_SYSTEM_PROMPT and `tools: []` regardless of backend → per-slot backend/model/reasoning override the round-robin backends array positionally (`slots?.[i] ?? backends[i % backends.length]`) → duplicate backends with distinct models stay distinct because model comes from the slot, not a per-backend map → zipped modules pair module i with slot i POSITIONALLY.
**Invariant:** Fair comparison requires identical prompts — any module leakage into uniform mode invalidates the ensemble; roster size is authoritative (no other flag may grow/shrink it); members request NO tools even on tool-capable backends; uniform candidates must never enter the single-judge stats store (no module signal — enforced at :1551).
**Probe:** `tests/pipelines/listed-solver-models.test.ts` (:31 no-modules→uniform, :45 "byte-identical SOLVER_SYSTEM_PROMPT (Invariant 1)", :61 per-slot fields flow + uniform/none ids, :76 same-backend distinct models, :91 positional zip) — EXECUTED this pass: pass after scratch-env `yaml` shim, 0 fail at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "buildSolverMembers SolverSlotSpec uniform", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt pure-plan/project seam separation (testable without I/O) and the byte-identical-prompt invariant for controlled LLM comparisons. Adapt slot schema to your config surface. Omit legacy round-robin branch if you only support explicit rosters.
