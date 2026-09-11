<!-- capsule-v2 -->
# Detached model catalog projection — how do you expose a provider's full model catalog to policy/settings/UI surfaces as detached minimal projections nobody can mutate through?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** How do you expose a provider's full model catalog to policy/settings/UI surfaces as detached minimal projections nobody can mutate through?

## Fresh {id,name}-only projection per call
**Path/Symbol:** `src/adapter.ts:openAICodexModelCatalog` (`:17-20`); sole caller `src/index.ts` apply (`:168` seeds the service; `:187` narrows advertisement).
**Signature:** `export function openAICodexModelCatalog(): readonly ModelCatalogEntry[]`.
**Data Shape:** Maps the vendored provider's `getModels()` to FRESH `{ id, name }` objects on every call — no shared references, no non-portable metadata (context windows, pricing, capabilities) crossing into host-facing surfaces.

### Decisive source
```ts
// src/adapter.ts :17-20
/** Return a detached copy of the complete pi-ai Codex model catalog. */
export function openAICodexModelCatalog(): readonly ModelCatalogEntry[] {
  return openaiCodexProvider().getModels().map(model => ({ id: model.id, name: model.name }))
}

// src/index.ts :168 — sole consumption point seeds the service once per apply()
modelCatalog: openAICodexModelCatalog(),
// src/index.ts :187 — advertisement narrows through the policy snapshot closure
() => imageTools.modelCatalogSnapshot().models,
```

**Flow:** `apply()` calls the projection ONCE at registration and hands the fresh array to `OpenAICodexService`; from there `ImageToolPolicy.normalizeModels` uses it as the intersection base for configured model lists, settings GET snapshots serve it to the browser, and the client UI renders it; `listModels` advertisement is narrowed independently by the `visibleModelIds` closure so hiding a model never removes it from the intersection universe (advertise ≠ resolve).
**Invariant:** Every consumer holds its own copy — mutating a projected entry must be impossible to observe through the provider definitions or other consumers; the projection carries ONLY `{id,name}` so vendor-specific metadata cannot leak into persisted settings or browser payloads.
**Probe:** `tests/adapter.spec.ts :52-66` (full-catalog advertisement contains gpt-5.4/gpt-5.6-luna/sol/terra when no model list configured) plus tests/adapter.spec.ts :34-50 (configured subset advertised while hidden models stay resolvable). Honest caveat: NO dedicated spec targets the projection function itself — evidence is the complete source read plus these consumer-level pins.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", qn_pattern: "^dsh-codex\\.src\\.adapter\\.openAICodexModelCatalog$", limit: 10 });
// observed live: total 1 — Function :18-20, in=1/out=2; trace_path(inbound): callers_total=1 → dsh-codex.src.apply
```

## Verdict
Adopt call-fresh minimal-field projection for any provider-owned catalog exposed to config/UI layers. Adapt the field set to what the host surfaces genuinely render. Omit visibility filtering here (owned by adapter-replay-models) and normalization/intersection (owned by tool-policy). Coverage caveat: check_index_coverage clean for src/adapter.ts, src/index.ts, tests/adapter.spec.ts.
