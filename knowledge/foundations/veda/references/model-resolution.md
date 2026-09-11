<!-- capsule-v2 -->
# Model resolution — resolve backend + model from explicit args, aliases, prefixes, fallbacks, and global config

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How does a CLI oracle decide which backend and model to call when the user can pass `-b`/`-m`, a model alias (`opus`, `sol`, `terra`), a model-name prefix (`gpt-*`, `pi/*`), a fallback, or a global config default — and how does it tag which source won?

## Backend + model resolution
**Path/Symbol:** `src/agent/config-extract.ts:resolveBackendModelExtracted` (213–285), with `determineBackend` (123–147), `determineModelForResolution` (155–197), `shouldApplyAlias` (107–117), `inferBackendFromModel` (27–35), `validateModelOrThrow` (56–72); composed by `src/agent/config.ts:resolveBackendModel` (403–410) and `resolveBackendModelForStage` (412–422) which inject the `resolveModel`/`resolveModelForStage` final step.
**Signature:** `resolveBackendModelExtracted(opts, resolveModelFn) → { backend, model?, source: ModelSource, aliasReasoning? }`.
**Data Shape:** `opts = { explicitBackend?, explicitModel?, fallbackBackend?, fallbackModel?, globalConfig?: { model?, modelAliases?, backendModels? }, modelAliases? }`. `ModelSource = { kind: 'explicit'|'alias'|'prefix'|'fallback'|'default' }`. Prefix→backend map: `gpt-|o1-|o3- → codex`, `claude- → claude-code`, `pi/ → pi`, `agy/ → agy`.

### Decisive source
```ts
// determineBackend (config-extract.ts:123-147)
if (explicitBackend) return explicitBackend;
if (aliasTarget && shouldUseAlias) return aliasTarget.backend;
if (explicitModel) { const inf = inferBackendFromModel(explicitModel); if (inf) return inf; validateModelOrThrow(explicitModel, explicitBackend, extraAliases); }
return fallbackBackend ?? 'codex';

// shouldApplyAlias (107-117): no explicit backend → true; else aliasTarget.backend === explicitBackend
// resolveBackendModelExtracted: useAlias=false when (explicitModel==null && fallbackModel!=null && fallbackBackend!=null)  // fallback treated as literal
// source tagging: alias→{kind:'alias'}; explicitBackend→{kind:'explicit'}; prefix-inferred→{kind:'prefix'}; fallbackModel→{kind:'fallback'}; else {kind:'default'}
```

**Flow:** compute `preferredModel = explicitModel ?? fallbackModel ?? globalConfig?.model` → try alias → decide `useAlias` (alias applies to the backend AND not vetoed by a fallback-backend-with-fallback-model) → determine backend (explicit > alias > prefix-inference > fallback, throwing a helpful error on an unknown model with no backend) → determine model for final resolution (explicit > fallback > global-config, with alias substitution) → call `resolveModelFn(backend, model)` → tag the winning source.

**Invariant:** an explicit backend always wins; a model alias only applies when its backend matches the resolved backend (or no backend is set); a fallback model is treated as a literal when a fallback backend is also given; the resolution never silently leaks a foreign model across an explicit `-b` switch (global-config model is filtered by prefix/alias backend match in `resolveModelWithSource`).

**Probe:** `tests/agent/config-extract.test.ts` — `resolveModelAliasNormalized` (trims/lowercases, idempotent), `tryResolveAliasTarget` (unknown→undefined, `opus`→claude-code, `terra`/`sol`→codex with reasoning, `gemini-pro`→agy), and `inferBackendFromModel` via `resolveBackendModel` (`gpt-5.2`→codex, `pi/crof/glm-5.2`→pi, `claude-sonnet-4`→claude-code, explicit backend overrides inference). Coverage caveat: `tests/` is excluded from the index by design (`fast-pattern`), so these probes are source-grounded from the on-disk test files, not graph-covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "resolveBackendModelExtracted determineBackend inferBackendFromModel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the backend/model resolution precedence chain (explicit > alias > prefix > fallback > default) with source tagging and the alias-application rules. Adapt the prefix→backend map, alias table, backend names, and default models to the host. Omit the CLI flag parsing and stage-specific default tables unless a target needs them.
