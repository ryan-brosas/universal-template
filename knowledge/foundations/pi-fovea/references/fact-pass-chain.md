<!-- capsule-v2 -->
# Fact-pass serialization chain — why must ALL extraction passes run one-at-a-time process-wide?

**Source:** pi-fovea MIT `main@5bd4e6f`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** Cold builds, refreshes, and hint-driven updates all run ast-grep — why does the code deliberately serialize them through ONE promise chain even though they touch different roots?

## Single never-rejecting chain guarding a failure ledger
**Path/Symbol:** `src/core/state.ts:factChain/factPass` (:102-114); every entry point funnels through it (`buildState` :172, `refreshState` :318).
**Signature:** `factPass<T>(job: () => Promise<T>): Promise<T>` — caller's promise settles independently; the CHAIN swallows both outcomes.
**Data Shape:** module-level `let factChain: Promise<unknown>` initialized resolved; each pass appends `factChain.then(job, job)` and re-assigns the chain to a voided version of its result.

### Decisive source
```ts
// All live fact passes serialize through one chain. Extraction-failure
// attribution is a process-wide ledger (astgrep cannot see nested passes),
// so overlapping passes would misblame files — and piled-up ast-grep spawns
// would freeze the host anyway. The chain itself never rejects.
let factChain: Promise<unknown> = Promise.resolve();
const factPass = <T>(job: () => Promise<T>): Promise<T> => {
  const run = factChain.then(job, job);
  factChain = run.then(() => undefined, () => undefined);
  return run;
};
```

**Flow:** any number of concurrent ensureState/refresh calls enqueue their extraction work → jobs run strictly one at a time in enqueue order → each caller still gets its own settled promise (success or failure) while the shared chain stays permanently resolved → the drainExtractionFailures ledger inside astgrep therefore sees non-overlapping passes.
**Invariant:** two independent reasons stack here: (1) correctness — the process-wide failed-file ledger would misattribute failures if passes overlapped (ast-grep can't see sibling invocations); (2) survival — N piled-up ast-grep spawns would freeze the host. The chain NEVER rejects: a failed pass must not poison every subsequent one. This trades throughput for determinism on purpose; per-file parallelism INSIDE one pass is where concurrency lives instead.
**Probe:** `tests/report.test.ts` — "healthy extraction > reports zero failures and drains a previous run's ledger" (ledger drain semantics); `tests/sync.test.ts` + `tests/workspace.test.ts` interleave cold builds and refreshes concurrently without flake.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "factPass factChain", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whenever a global side-ledger (failure attribution, metrics, rate budgets) makes naive concurrency lie. Adapt chain placement (per-process vs per-worker). Omit nothing — 8 lines, fully portable.
