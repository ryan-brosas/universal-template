<!-- capsule-v2 -->
# V2 catalog availability + api projection — how do you derive "which models can actually run" from config, credentials, and integrations without mutating stored state?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A model catalog stores provider/model entries from config and plugins, but whether a model is USABLE depends on runtime facts (a credential exists, an integration is connected, the provider is not disabled, policy allows it). How do you project availability and provider-level defaults onto models at read time so stored state stays pure?

## Availability predicate + read-time projection
**Path/Symbol:** `packages/core/src/catalog.ts` (`available` predicate :71-77, `projectModel` :78-97, `normalizeApi` :99-103, `provider.available` :184-189, `model.available` :210-213, `model.default` :215-232, `finalize` :160-169).
**Signature:** `available(provider, integration?) → boolean`; `projectModel(model, provider) → ModelV2.Info`; `model.available() → Effect<ModelV2.Info[]>`; `model.default() → Effect<ModelV2.Info | undefined>`.
**Data Shape:** stored `Data = { providers: Map<ProviderV2.ID, ProviderRecord>, defaultModel? }`; reads return projected copies (`ModelV2.Info.make({...model, api, request})`) — never the stored mutable records.

### Decisive source
```ts
// catalog.ts:71-77 — availability is derived, never stored
const available = (provider: ProviderV2.Info, integration: Integration.Info | undefined) => {
  if (provider.disabled) return false
  if (typeof provider.request.body.apiKey === "string") return true
  if (integration?.connections.length) return true
  return provider.integrationID === undefined && !integration
}
```

**Flow:** provider.available() joins stored providers with live integration connections and filters by the predicate (disabled → out; inline apiKey → in; integration with connections → in; NO integration declared and none active → in, i.e. unmanaged providers pass). model.available() = model.all() filtered to available providers AND model.enabled, where model.all() projects every model through projectModel: provider-level api (url/settings), headers, and body merge UNDER the model's own values, and a native api with no url/settings INHERITS the provider api entirely. normalizeApi() migrates legacy `request.body.baseURL` into `api.url` at write time. model.default() checks the configured default only if its provider is available and the model enabled, else falls back to the NEWEST available model by time.released (pinned by test). finalize() applies policy: providers denied for "provider.use" are REMOVED from the draft (not flagged), then Event.Updated publishes. model.small() scores candidates by a 0.8/0.2 cost/age blend with SMALL_MODEL_RE keyword preference and hard-coded provider carve-outs (azure skip, gpt-5-nano pin).
**Invariant:** availability is computed from live credential/integration state on every read — creating or deleting a credential changes availability without touching provider state (test pins request.body stays {} after credential churn); stored catalog records are never mutated by reads; policy denial is removal, not a flag.
**Probe:** `packages/core/test/catalog.test.ts` (353L, 13 `it.effect`): "derives availability from active credentials without changing provider state" pins credential-driven availability with untouched stored body; "derives availability from a provider's integration" pins connection-gated availability; "resolves default model api from provider api" pins native-api inheritance; "falls back to newest available model when no default is configured" pins the recency fallback; "ignores a configured default on a disabled provider" pins the availability gate on the default; "removes providers denied by policy after loading" pins finalize removal. Source pin:
```bash
grep -c 'SMALL_MODEL_RE' packages/core/src/catalog.ts   # expect 2
grep -c 'hasStatements' packages/core/src/catalog.ts    # expect 1
grep -c 'publish(Event.Updated' packages/core/src/catalog.ts  # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Catalog available projectModel provider integration connections default model fallback policy provider.use", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt derived-at-read availability (predicate over disabled/apiKey/integration-connections) and read-time projection with provider-under-model merging; adopt the newest-enabled recency fallback for defaults and policy-denial-as-removal. Adapt the scoring constants in model.small() (opencode-tuned); omit the hard-coded provider carve-outs. Coverage caveat: Codebase Memory MCP not connected this session — Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
