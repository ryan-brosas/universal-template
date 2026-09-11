<!-- capsule-v2 -->
# Catalog plugin composition — how do you build a model catalog from an upstream dump plus per-vendor patches without confusing modes with variants?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A host's model catalog is assembled from many writers: an upstream models.dev dump, per-vendor header/SDK patches, config files, and reasoning-effort variant generators. How do you order and scope these writers so the result is deterministic and modes never masquerade as variants?

## Boot-ordered plugin batch over two stores
**Path/Symbol:** `packages/core/src/plugin/internal.ts` (`State.batch` registration :108-122, service-injection `add` closure :84-106), `packages/core/src/plugin/models-dev.ts` (integration projection :140-158, catalog projection :159-175, Refreshed reload :177-181, `applyModel` :76-122, `mergeCost` :52-74), `packages/core/src/plugin/variant.ts` (`generate` :27-39, explicit-wins merge :14-24), `packages/core/src/plugin/provider/anthropic.ts` (whole, 27L).
**Signature:** `Plugin = {id, effect: (ctx: PluginContext) → Effect<void, never, R | Scope>}`; `ctx.catalog.transform / ctx.integration.transform` give a Draft editor; `define()` is an identity helper.
**Data Shape:** `ModelsDev.Provider → (Integration rows: key+env methods) + (Catalog rows: provider + models + "<id>-<mode>" sibling models)`; `ModelV2Info["variants"] = {id, headers, body}[]`.

### Decisive source
```ts
// plugin/models-dev.ts:165-172 — experimental modes become SEPARATE models, not variants
for (const [mode, options] of Object.entries(model.experimental?.modes ?? {})) {
  catalog.model.update(providerID, `${model.id}-${mode}`, (draft) =>
    applyModel(draft, model, {
      name: modeName(model, mode),
      cost: mergeCost(baseCost, options.cost),
      request: options.provider,
    }),
  )
}
```

**Flow:** `internal.ts` registers ALL built-ins inside ONE `State.batch` in a fixed order — ConfigReference → Agent → Command → Skill → **ModelsDev** → ConfigAgent → ConfigCommand → ConfigSkill → 34 ProviderPlugins → ConfigExternal → ConfigProvider → **Variant** — each wrapped by a closure that injects every core service, so plugin order is the only ordering mechanism and batch failure semantics are uniform. ModelsDevPlugin first projects integrations (providers with env vars get key + env methods), then the catalog: `applyModel` maps the raw dump onto ModelV2 rows (npm→aisdk api, else native), tiered costs merged by tier key (`mergeCost`), and each `experimental.modes` entry becomes a sibling model `<id>-<mode>` carrying the mode's headers/body — deliberately NOT a variant (pinned by models-dev.test.ts: base model keeps `variants: []` while `gpt-5.4-fast` gets `request.headers["x-mode"]`). A `ModelsDev.Event.Refreshed` subscription reloads both stores so a background refresh (see models-dev-catalog-cache) re-projects without restart. VariantPlugin runs LAST and generates `reasoning_effort` variants (`high`/`max`) only for `@ai-sdk/openai-compatible` models whose id contains glm-5.2/glm-5-2/glm-5p2, with explicit variants winning over generated ones by id. Per-vendor plugins are tiny: anthropic.ts adds the `anthropic-beta` header to aisdk providers and dynamically imports/creates the SDK via `ctx.aisdk.sdk`.
**Invariant:** composition is deterministic — same dump + same plugin order ⇒ same catalog; modes and variants are distinct mechanisms (modes = sibling model rows with request overrides; variants = request-overlay entries consumed by the resolver's variant stage); explicit user/config data always beats generated data (explicit variants win; ConfigProvider runs after ModelsDev); a models.dev refresh re-projects through the same path.
**Probe:** `packages/core/test/plugin/models-dev.test.ts` (170L, 2 `it.effect`): "projects models.dev modes as separate models instead of variants" pins the sibling-model mapping with merged tiered cost; "registers key methods for providers with environment variables" pins the integration side against a fixture file. `packages/core/test/plugin/variant.test.ts` (67L, 2 `it.effect`): "adds GLM 5.2 variants after catalog sources" and "keeps explicit variants over generated defaults" pin the generator and the explicit-wins rule. Source pin:
```bash
grep -c 'mergeCost' packages/core/src/plugin/models-dev.ts  # expect 2
grep -c 'generate' packages/core/src/plugin/variant.ts      # expect 6
grep -c 'ProviderPlugins' packages/core/src/plugin/internal.ts # expect 2
grep -c 'it.effect' packages/core/test/plugin/variant.test.ts  # expect 2
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "ModelsDevPlugin applyModel experimental modes separate model mergeCost VariantPlugin generate reasoning_effort explicit variants State.batch plugin registration order", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt boot-ordered plugin composition over shared stores, the modes-as-sibling-models rule, tier-keyed cost merging, and the explicit-beats-generated precedence for variants. Adapt the plugin context shape and registration mechanism; omit the specific GLM heuristic and vendor header patches (site-specific). Coverage caveat: the 33 remaining vendor plugin bodies share anthropic.ts's two patterns but only a subset have direct tests (provider-*.test.ts exist per vendor); the Refreshed-reload path is source-confirmed only; Codebase Memory MCP not connected this session, Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
