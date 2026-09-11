<!-- capsule-v2 -->
# Global-model leak guard — how do you keep a global default model from leaking across an explicit backend switch onto a strict backend?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** The user's global config says `MODEL=gpt-5.6-sol` (a codex model). They run `veda -b agy "..."`. A strict backend like agy will reject a codex model id — so the resolver must NOT hand it over. But `MODEL=some-custom-model` (no known prefix) IS portable. And a per-backend override (`backendModels.agy`) must beat the global model. How is that arbitration encoded?

## Connected graph-selected seam
**Path/Symbol:** `src/cli/resolve.ts:resolveBackendModel` model ladder (:136–165), with `inferBackendFromPrefix` (:41–49) over `MODEL_PREFIX_TO_BACKEND` (:32–39); last-resort defaults from `src/backend/defaults.ts:getBackendDefaultModelForStage` (:40–45) over `BACKEND_DEFAULT_MODELS` (:7–13) + `BACKEND_STAGE_DEFAULT_MODELS` (:21–25).
**Signature:** `resolveBackendModel(opts: {explicitBackend?, explicitModel?, globalConfig?, stage?, aliasReasoning?}): ResolvedBackendModel`; `getBackendDefaultModelForStage(backendId: string, stage: ModelStage): string | undefined`.
**Data Shape:** `GlobalConfig { model?, modelAliases?, backendModels?: Record<backend, model>, backend? }`. The guard has four arms: foreign-alias → stage default; foreign-prefix raw → stage default; own-prefix or unprefixed raw → apply; same-backend alias → pass through verbatim.

### Decisive source
```ts
  } else if (globalConfig?.model) {
    // Check if global model is an alias that doesn't match our backend
    const globalAlias = resolveModelAlias(globalConfig.model, globalConfig.modelAliases);
    if (globalAlias && globalAlias.backend !== backend) {
      // Global model alias doesn't match our backend, use backend default
      model = getBackendDefaultModelForStage(backend, stage) ?? 'unknown';
    } else if (!globalAlias) {
      // Raw model string: apply it only when its prefix belongs to this
      // backend (or it has no known prefix); a foreign raw model must not
      // leak across an explicit -b switch onto a strict backend.
      const inferred = inferBackendFromPrefix(globalConfig.model);
      if (!inferred || inferred === backend) {
        model = globalConfig.model;
      } else {
        model = getBackendDefaultModelForStage(backend, stage) ?? 'unknown';
      }
    } else {
      model = globalConfig.model;
    }
  } else {
    model = getBackendDefaultModelForStage(backend, stage) ?? 'unknown';
  }
```
```ts
// src/backend/defaults.ts — the last resort is STAGE-AWARE:
export function getBackendDefaultModelForStage(
  backendId: string,
  stage: ModelStage
): string | undefined {
  const stageOverride = BACKEND_STAGE_DEFAULT_MODELS[backendId]?.[stage];
  return stageOverride ?? getBackendDefaultModel(backendId);
}
// BACKEND_STAGE_DEFAULT_MODELS: codex { solver: 'gpt-5.3-codex', verifier: 'gpt-5.3-codex' }
// while BACKEND_DEFAULT_MODELS.codex = 'gpt-5.2' — different models per stage.
```

**Flow:** full model precedence inside `resolveBackendModel`: explicit alias target > explicit `-m` > per-backend config override (`backendModels[backend]`) > global MODEL (through the four-arm guard above) > stage-aware built-in default (`?? 'unknown'` as the final sentinel). The guard's logic: resolve the global value as an alias first — if it names a DIFFERENT backend, drop to the stage default; if it is a raw string, infer its prefix — unknown prefix means portable (apply), foreign prefix means drop to the stage default; if it is an alias for THIS backend, pass the raw value through verbatim (alias→model expansion happens later in the agent-plane resolver, but the leak check only needs the namespace). Note the asymmetries with the explicit-`-m` path: an explicit model ALIAS targeting a different backend than `-b` THROWS (`ALIAS_BACKEND_MISMATCH`, :95–101), and an explicit raw model with no backend and no known prefix THROWS (`UNKNOWN_MODEL`, :118–125) — but an explicit raw model with a foreign prefix plus an explicit `-b` passes through UNCHECKED (the strict backend rejects it at runtime). A global foreign model, by contrast, SILENTLY degrades to the backend default: ambient config fails soft, resolvable user input fails loud, and only the unresolvable-explicit case is left to the backend.
**Invariant:** a global model can never cross a backend boundary it does not belong to; unprefixed ids are the portable class; per-backend overrides always beat the global model; the fallback is stage-aware (solver/verifier may legitimately default to a different model than base on the same backend); `'unknown'` is the last-resort sentinel so resolution never returns `undefined`.
**Probe:** `tests/cli/resolve-global-model.test.ts` (executed green at pin: 7 pass / 0 fail within the 39-test batch) — pins every arm: global raw `gpt-5.6-sol` + `-b agy` → `gemini-3.1-pro-high` (agy default); same global + `-b codex` → applies; global alias `sol` + `-b agy` → agy default; same-backend alias `gemini` + `-b agy` → passes through verbatim; unprefixed `some-custom-model` + `-b agy` → portable; `agy/gemini-3.6-flash-low` without `-b` → prefix-inferred backend, source `'prefix'`; `backendModels.agy` beats a foreign global model.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "inferBackendFromPrefix MODEL_PREFIX_TO_BACKEND getBackendDefaultModelForStage BACKEND_STAGE_DEFAULT_MODELS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-arm guard for any system where ambient config carries a resource id and the caller can switch namespaces: classify the id (alias vs raw, own vs foreign vs unclassifiable) and only apply the unclassifiable/own classes. Adopt the loud-vs-soft asymmetry: explicit alias-to-wrong-namespace and unresolvable-explicit throw; ambient config degrades to the namespace default; an explicit raw id with a foreign prefix plus an explicit namespace switch is deliberately left unchecked (the target rejects it at runtime) — decide consciously which of those three postures your port wants for each input class. Adopt stage-aware built-in defaults when the same resource plays different roles at different pipeline stages. Adapt the prefix table, alias table, and default tables to your host. Omit nothing behavioral; keep the `'unknown'` sentinel so downstream code never sees `undefined` from resolution. Relationship note: `model-resolution.md` documents the agent-plane twin (`config-extract.ts`) at the older pin; this capsule is the CLI-plane implementation with its own dedicated test suite.
