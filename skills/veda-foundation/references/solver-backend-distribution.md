<!-- capsule-v2 -->
# Solver-backend distribution — how do you assign k solver slots across backends deterministically?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A deep run wants k solvers. How does the CLI handler choose which backend each slot uses — fixed, distributed, or inferred — and what makes the distribution deterministic?

## Four-arm precedence with sorted round-robin
**Path/Symbol:** `src/commands/deep.ts:selectSolverBackends` (:40-105) + `resolveCandidates` (:108-156); direct test `tests/commands/distribute.test.ts`.
**Signature:** `selectSolverBackends(options: { k, distributeSolvers?, solverBackend?, solverBackends?, solverModel?, baseBackend? }) → Promise<{ backends: string[], mode: 'fixed' | 'distributed' }>`.
**Data Shape:** `k` bounded 1..12 (defensive re-check beside CLI validation); `backends` length always exactly k; `mode` records which arm won so the handler can log distribution and pick a notification backend.

### Decisive source
```ts
// Precedence 1: Explicit single backend override
if (selector.solverBackend) {
  return { backends: Array(k).fill(selector.solverBackend), mode: 'fixed' };
}

// Precedence 2: Round-robin distribution
if (selector.distributeSolvers) {
  const candidates = await resolveCandidates(selector.solverBackends);
  const selected: string[] = [];
  const n = candidates.length;
  for (let i = 0; i < k; i++) {
    selected.push(candidates[i % n]);
  }
  return { backends: selected, mode: 'distributed' };
}

// Precedence 3: Infer backend from solverModel if specified
if (selector.solverModel) {
  const resolved = resolveBackendModel({ explicitModel: selector.solverModel, fallbackBackend: baseBackend ?? 'codex' });
  return { backends: Array(k).fill(resolved.backend), mode: 'fixed' };
}
```
**Flow:** arm 1 explicit `--solver-backend` fills all k slots fixed → arm 2 `--distribute-solvers` resolves candidates (explicit list wins; else registry `getAvailableBackends()`), then normalizes (trim/lowercase/dedupe) and SORTS before validation, so flag order never changes the roster → unknown names throw loudly (`Unknown backend(s): …`), registered-but-unavailable names only warn to stderr and stay in the roster → arm 3 infers the backend from `--solver-model` prefix via `resolveBackendModel` → arm 4 falls back to `baseBackend ?? 'codex'` fixed.
**Invariant:** the roster is deterministic (sorted candidates, `i % n` cycling) and always exactly k long; distribution never silently drops an unknown backend — it fails loudly BEFORE spend; availability is a warning, not a gate, because per-member spawn retries absorb later failures.
**Probe:** `tests/commands/distribute.test.ts` (executed live at pin: 32 pass / 0 fail) pins even/remainder cycling, determinism across flag order, unknown-backend throw, mixed-case/whitespace/duplicate normalization, empty-list throw, k bounds 1..12, and the fixed-mode precedence arms.
**Coverage caveat:** the no-explicit-list arm depends on the host's installed backends; the suite asserts membership in `getAvailableBackends()` rather than exact names.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "selectSolverBackends resolveCandidates distributeSolvers round-robin", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-arm precedence with sorted round-robin and loud unknown-name failure before spend. Adapt the backend registry and availability probe to your host. Omit the notification-backend derivation (first slot) if you have no notification plane.
