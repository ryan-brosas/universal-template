<!-- capsule-v2 -->
# ModelV2/ProviderV2 schema shapes — what exactly does the v2 catalog store per model and provider, and how do empty-row factories support partial registration?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** The pass-13 resolver consumes `ModelV2.Info` and the catalog stores `ProviderV2.Info`, but both were cited only as interfaces. What are the concrete row shapes, how do catalog `update()` calls auto-create missing rows, and how does `parse()` handle model IDs that contain slashes?

## The stored rows and their empty factories
**Path/Symbol:** `packages/schema/src/model.ts` (`Info` :56-88, `empty` :90-105, `Api` :44-53), `packages/schema/src/provider.ts` (`AISDK` :22-29, `Native` :31-38, `Api` :40-44, `Info` :55-70, `empty` :64), `packages/core/src/model.ts` (`parse` :33-38, `MutableInfo` :22-24), `packages/core/src/provider.ts` (`MutableApi` :16-18).
**Signature:** `ModelV2.Info.empty(providerID, modelID) → Info`; `ProviderV2.Info.empty(id) → Info`; `ModelV2.parse("provider/model/with/slashes") → {providerID, modelID}`.
**Data Shape:** `ModelV2.Info = {id, providerID, family?, name, api: Api, capabilities: {tools, input[], output[]}, request: {headers, body, variant?}, variants: {id, headers, body}[], time: {released}, cost: Cost[], status: "alpha"|"beta"|"deprecated"|"active", enabled, limit: {context, input?, output}}`; `Api = aisdk{id, package, url?, settings?} | native{id, url?, settings}` (tagged union via `Schema.toTaggedUnion`). `ProviderV2.Info = {id, integrationID?, name, disabled?, api: AISDK|Native, request: {headers, body}}`.

### Decisive source
```ts
// schema/src/model.ts:90-96 — the empty factory the catalog's draft update() falls back to
empty: (providerID: Provider.ID, modelID: ID) =>
  schema.make({
    id: modelID,
    providerID,
    name: modelID,
    api: { id: modelID, type: "native", settings: {} },
    capabilities: { tools: false, input: [], output: [] },
    request: { headers: {}, body: {} },
    variants: [],
    time: { released: 0 },
    cost: [],
    status: "active",
    enabled: true,
    limit: { context: 0, output: 0 },
  }),
```

**Flow:** Any catalog `provider.update`/`model.update` on a missing row creates it from the `.empty()` static (catalog.ts :130-140/:156-166), then runs the mutator and re-pins `model.id`/`model.providerID` so a mutator cannot detach the row from its key. `normalizeApi` (:99-103) migrates a legacy `request.body.baseURL` into `api.url` and deletes the body key on every update. `projectModel` (see catalog-availability-projection) merges provider-under-model api/request at READ time, so stored rows stay partial and projection completes them. `parse()` splits on the FIRST slash only and re-joins the rest — model IDs may legally contain slashes. `MutableInfo` types punch `settings` back to `any` through `Types.DeepMutable`, because the mutator API hands out immer-style drafts over Schema-typed rows.
**Invariant:** a stored model row is always self-describing enough to render (empty factory gives `status:"active"`, `enabled:true`, zero limits) — availability gating happens at read time, never by row absence; `id`/`providerID` are re-pinned after every mutator run; the aisdk/native tag is the single discriminator the resolver's three-route mapping switches on.
**Probe:** `packages/core/test/model.test.ts` (23L, 2 `test()`): decodes `ModelV2.Ref` with and without an explicit variant, pinning the optional-variant shape. `packages/core/test/catalog.test.ts` (353L, 13 `it.effect`) pins the update-created-row behavior end-to-end. Source pin:
```bash
grep -c 'Info.empty' packages/core/src/catalog.ts        # expect 3 (2 provider + 1 model fallbacks)
grep -c 'empty: (providerID' packages/schema/src/model.ts  # expect 1
grep -c 'it.effect' packages/core/test/catalog.test.ts   # expect 13
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "ModelV2 Info empty factory ProviderV2 Info AISDK Native tagged union normalizeApi baseURL MutableInfo parse slash", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the row shapes as the contract between catalog writers (plugins/config) and readers (resolver/UI): partial rows + read-time projection + empty factories, with keys re-pinned after mutation. Adapt field names and the schema library; omit the Effect Schema `statics` machinery if your host builds factories directly. Coverage caveat: `parse()` has no dedicated direct test at this pin (source-confirmed only; the slash-containing-ID behavior follows from the split/join implementation); Codebase Memory MCP not connected this session, Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
