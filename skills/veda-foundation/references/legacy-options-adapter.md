<!-- capsule-v2 -->
# Legacy options adapter — how do typed CLI unions flow into command handlers that still speak the legacy flat-options shape?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** When you adopt a parse-don't-validate discriminated-union CLI plane, must you also rewrite every command handler — or is there a boundary seam that translates the union into the legacy options bag?

## Three adapter functions collapse the union into legacy CliOptions at one boundary
**Path/Symbol:** `src/cli/adapter.ts` — `simpleConfigToCliOptions` (:17-44), `deepConfigToCliOptions` (:46-121), `resumeConfigToCliOptions` (:123-146), private `outputConfigToPath` (:148-150); re-exported by `src/cli/index.ts:12`; consumed only by `src/index.ts` dispatch (:68, :83, :91). Direct test `tests/cli/adapter-listed.test.ts` (58L whole).
**Signature:** `deepConfigToCliOptions(config: DeepConfig): CliOptions` (plus the Simple/Resume twins).
**Data Shape:** input = the discriminated-union configs from `src/cli/types.ts` (SimpleConfig / DeepConfig with `stages.solver: SolverConfig` three-arm union, `verify: VerifyConfig` two-arm union); output = the legacy flat `CliOptions` bag (`src/cli/index.ts`) — every field explicitly set, including `deep: false`, `help: false`, `version: false`, and `distributeSolvers: undefined` on the non-deep arms.

### Decisive source
```ts
  } else {
    options.distributeSolvers = true;
    options.solverBackends = config.stages.solver.backends;
    // In distributed mode, don't set solverModel - let the pipeline resolve
    // per-backend models from defaults. Setting it would override all backends
    // with the same model, breaking per-backend default resolution.
  }
```
**Flow:** `src/index.ts` dispatch reads stdin, appends it to the prompt, then calls exactly one adapter per command arm (`resume` → resumeConfigToCliOptions :68; `prompt` deep → deepConfigToCliOptions :83; `prompt` simple → simpleConfigToCliOptions :91) and hands the legacy bag to the unchanged handler (`handleResume`/`handleDeep`/`handleRun`). Inside the deep adapter: fixed mode sets `solverBackend`+`solverModel`; listed mode maps slots 1:1 into `options.solverSlots` and leaves the single-shape knobs (`solverBackend`, `solverModel`, `distributeSolvers`, `solverBackends`) undefined; distributed mode sets `distributeSolvers`+`solverBackends` and deliberately leaves `solverModel` unset. VerifyConfig collapses losslessly to `noVerify = !enabled`, `forceVerify = enabled && forced` (the union makes the illegal combination unrepresentable upstream). `outputConfigToPath` projects the output union to `string | undefined` — only `format: 'file'` carries a path.
**Invariant:** in distributed solver mode `solverModel` must remain unset, or the pipeline's per-backend default resolution is overridden with one model for every backend (the adapter's own comment names this failure). Listed mode must leave all four single-shape knobs undefined — the test pins each with `toBeUndefined`. The Simple/Resume adapters hard-pin `deep: false` and zero out deep-only fields rather than leaking `undefined` into the legacy bag.
**Probe:** `tests/cli/adapter-listed.test.ts` (executed live at pin: 2 pass / 0 fail) pins listed-mode slot mapping plus all four `toBeUndefined` knobs, and distributed-mode `distributeSolvers === true` with `solverSlots` undefined.
**Coverage caveat:** only the listed/distributed arms have a dedicated test; the fixed-mode and Simple/Resume arms are source-pinned only (grep-verified — no other test imports the adapters).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "deepConfigToCliOptions solverSlots distributeSolvers solverModel legacy CliOptions adapter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the boundary-seam pattern: keep handlers on the legacy shape and translate the typed union at exactly one adapter file, so a union adoption never forces a handler rewrite. Adapt the field vocabulary (solver/judge/verifier/revision knobs, notify flags) to your host's option bag. Omit nothing if your host has both a typed parse plane and legacy handlers — the distributed-mode unset-`solverModel` rule is the invariant that survives any port.
