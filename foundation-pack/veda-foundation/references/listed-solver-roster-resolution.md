<!-- capsule-v2 -->
# Listed-solver roster resolution — how do you expand a comma-separated model list (CLI or config) into fully-pinned per-slot solver rosters with loud failure and one authoritative roster size?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** `--solver-models sol,k3,fable` must become N solvers, each with its own backend/model/reasoning — where entries may be aliases, prefixed raw ids, or garbage; where the same list can also come from config (`DEEP_SOLVER_MODELS`); and where `-k` (roster size) must not be able to contradict the list. How is that resolved without silent skips or ambiguous sizes?

## Connected graph-selected seam
**Path/Symbol:** `src/cli/resolve.ts:resolveSolverConfig` listed-mode block (:205–275); types `ListedSlot` / `SolverConfig` union in `src/cli/types.ts` (:102–117); per-slot reasoning via `resolveStageReasoning` (:553–614). Downstream projection into ensemble members is the pipeline plane — see `deep-think-listed-slots.md` (this capsule is the CLI-side resolution; that one is the prompt/member projection).
**Signature:** `resolveSolverConfig(flags, base, globalConfig?, aliasReasoning?): SolverConfig`; returns `{ mode: 'listed'; slots: ListedSlot[]; reasoning?: ReasoningLevel }`.
**Data Shape:** `ListedSlot { backend: string; model: string; reasoning?: ReasoningLevel }` — fully pinned per slot. The `SolverConfig` discriminated union (`fixed | distributed | listed`) makes mode-mixing unrepresentable at type level.

### Decisive source
```ts
  // === Listed mode (--solver-models / DEEP_SOLVER_MODELS) ===
  // One solver per model entry; backend/model/reasoning fully pinned per slot.
  // Other solver-shape flags are rejected by detectConflicts; explicit CLI/base
  // solver-shape intent additionally suppresses config-provided models here.
  const cliRequestsOtherSolverShape =
    flags.distributeSolvers !== undefined ||
    !!flags.solverBackends ||
    !!flags.solverBackend ||
    !!flags.solverModel ||
    !!flags.model;
  const listedModelEntries = flags.solverModels
    ?? (cliRequestsOtherSolverShape ? undefined : deepConfig?.solverModels);

  if (listedModelEntries && listedModelEntries.length > 0) {
    if (listedModelEntries.length > 12) {
      throw new CliValidationError(
        `--solver-models supports at most 12 entries, got ${listedModelEntries.length}`,
        'INVALID_K_VALUE'
      );
    }

    // Roster size derives from the list; -k may only confirm it.
    // (CLI-flag mismatch is caught by detectConflicts; this also covers config lists.)
    if (flags.k !== undefined && flags.k !== listedModelEntries.length) {
      throw new CliValidationError(
        `-k ${flags.k} conflicts with --solver-models (${listedModelEntries.length} models listed)`,
        'INVALID_K_VALUE',
        'Remove -k (roster size = list length) or repeat entries to duplicate models'
      );
    }
```
```ts
    const slots: ListedSlot[] = listedModelEntries.map((entry) => {
      const alias = resolveModelAlias(entry, globalConfig?.modelAliases);
      ...
      if (alias) {
        backend = alias.backend;
        model = alias.model;
        // Alias reasoning strings pass through as-is; 'xhigh'/'max' are valid
        // ReasoningLevels (per-slot, not base-wide) in listed mode.
        entryAliasReasoning = alias.reasoning as ReasoningLevel | undefined;
      } else {
        // Prefix inference or unknown — resolveBackendModel throws UNKNOWN_MODEL.
        const resolved = resolveBackendModel({
          explicitModel: entry,
          globalConfig,
          stage: 'solver',
        });
        backend = resolved.backend;
        model = resolved.model;
        entryAliasReasoning = resolved.aliasReasoning;
      }

      return {
        backend,
        model,
        reasoning: cliReasoning ?? entryAliasReasoning ?? configOrDefault,
      };
    });
```

**Flow:** entry source = CLI list, else config list UNLESS any explicit CLI solver-shape intent exists (the five-flag `cliRequestsOtherSolverShape` check — a visible `-m` alone suppresses the config roster). Then hard gates: >12 entries throws; `-k` present and ≠ list length throws with a remedy suggestion ("repeat entries to duplicate models"). Per slot: alias lookup first (alias backend+model+reasoning hint), else `resolveBackendModel` with prefix inference — which THROWS `UNKNOWN_MODEL` for unresolvable entries, so one bad entry kills the whole run before any spend. Per-slot reasoning precedence: `--solver-reasoning` > base `-r` > entry alias hint > `DEEP_SOLVER_REASONING`/stage default (the last two arrive via `resolveStageReasoning(flags,'solver',globalConfig)` WITHOUT the base alias hint — deliberately, so a base alias's reasoning does not leak into per-slot resolution). Duplicate entries are allowed and mean "run this model twice". The dry-run projection (cli/index.ts:214–223) emits the slot LIST rather than a backend→model map because "per-slot models can repeat backends, so a backend→model map cannot represent the roster".
**Invariant:** list length is the ONLY authority on roster size (no flag may grow/shrink it); every entry resolves to a fully-pinned slot or the run fails loudly before spend; config-provided rosters are a convenience layer that any visible CLI solver-shape intent suppresses; per-slot alias reasoning is valid per-slot even when exotic ('xhigh'/'max').
**Probe:** `tests/cli/resolve-solver-models.test.ts` (executed green at pin: 9 pass / 0 fail within the 39-test batch) — pins alias slots resolving to per-slot backend/model/reasoning (`sol`→codex/high, user `k3`→pi/max, `fable`→droid/medium), prefix-based ids without aliases, `--solver-reasoning low` overriding all per-slot hints, base `-r high` likewise, unknown entry throwing `UNKNOWN_MODEL`, config `DEEP_SOLVER_MODELS` activating listed mode, explicit `--distribute-solvers --solver-backends codex` suppressing the config list (mode becomes distributed), `-k 4` vs 2-entry config list throwing `INVALID_K_VALUE` with "(2 models listed)", and `sol,sol,k3` yielding duplicate slots.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "resolveSolverConfig listedModelEntries cliRequestsOtherSolverShape ListedSlot INVALID_K_VALUE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern for any "list of things to run" feature: one authoritative size source (the list itself), confirmation-only companion flags that throw on mismatch with a remedy message, loud per-entry failure before any resource spend, and a suppression rule where ANY visible CLI intent overrides config-provided lists. Adapt the 12-entry cap, the intent-flag set, and the reasoning precedence to your domain. Omit nothing behavioral; keep the discriminated-union mode type so downstream code cannot accidentally treat a roster as a single backend. Do not let base-level alias hints leak into per-slot resolution unless you want them to — veda deliberately passes the config/default layer only.
