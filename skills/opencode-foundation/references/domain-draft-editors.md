<!-- capsule-v2 -->
# Domain draft editors — what contract must an AgentV2/CommandV2/SkillV2/Catalog/Integration draft satisfy so plugins can create-or-update rows without ever desynchronizing a key from its row?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Five services hand plugins a mutable "draft" over a Map of rows. What is the exact create-on-first-touch / re-pin-key / remove contract, and where do the five domains deliberately differ?

## The shared draft contract, instantiated five ways
**Path/Symbol:** `packages/core/src/agent.ts` (`State.create` :48-64, `selectable`/`selectedDefault` :67-81); `packages/core/src/command.ts` (:32-44); `packages/core/src/skill.ts` (`State.create` :62-71, lazy `load` :73-107, cached `list` :109-118); `packages/core/src/catalog.ts` (`State.create` :105-159, `finalize` :160-169); `packages/core/src/integration.ts` (`State.create` :228-284, `resolveConnections` :288-301).
**Signature:** `draft.update(id, fn: (row: DeepMutable<Info>) => void) → void`; `draft.remove(id) → void`; `draft.get(id) → Info | undefined`; `draft.list() → readonly Info[]`.
**Data Shape:** every Data is a `Map` of `Types.DeepMutable<Info>` rows (AgentV2 adds `default?: ID`; Catalog nests provider→{provider, models: Map}; Integration's Entry = {ref, methods[], implementations: Map<MethodID, OAuthImplementation>}; SkillV2 stores SOURCES not rows).

### Decisive source
```ts
// agent.ts:57-61 — create-on-first-touch, apply fn, RE-PIN the key after fn
const current = draft.agents.get(id) ?? (Info.empty(id) as Types.DeepMutable<Info>)
if (!draft.agents.has(id)) draft.agents.set(id, current)
fn(current)
current.id = id
// catalog.ts:143-149 — model.update additionally re-pins BOTH identity fields
fn(model)
model.id = modelID
model.providerID = providerID
normalizeApi(model)
```

**Flow:** `update` gets-or-creates the row via the domain's `Info.empty(id)` factory, applies the caller's mutation to the DeepMutable row, then re-pins the identity field(s) AFTER fn so a transform can never desynchronize a key from its row. `remove` deletes the key (a later transform's update re-creates it — that is how "disabled:true removes even built-ins" survives replay order). Domain differences: CommandV2 keys by name string with `{name, template:""}` default; Catalog's nested draft auto-creates the ProviderRecord on model.update and runs `normalizeApi` (request.body.baseURL → api.url) after EVERY provider/model fn; Integration's `method.update` upserts methods by (type, oauth?id) — non-oauth methods match by type alone, oauth by id — and separately registers the OAuth implementation in a parallel map; SkillV2's draft only dedup-appends Sources via `Source.equals` and defers ALL row loading to read time (per-source cache keyed by `Source.key`, never invalidated — inline QUESTION(Dax) comment admits no fs-watch invalidation yet), with later sources overriding earlier by name.
**Invariant:** the draft is the ONLY write surface and is only valid inside a transform; every read method (`get/all/list`) reads the committed state, never the draft mid-rebuild; key re-pinning after fn makes row identity idempotent under replay; Integration's draft stores only registry facts — connections are PROJECTED at read from credentials (newest-first via `toReversed()`) plus live env vars, so credential churn never mutates the registry.
**Probe:** `packages/core/test/agent.test.ts` (131L, 7 `it.effect`): "creates agents with runtime defaults and supports direct removal" pins Info.empty creation + remove; "materializes replayable agent transforms" pins replay; "rebuilds state when a transform is replaced" pins reload re-reading captured values. `test/command.test.ts` (56L, 1 `it.effect`) pins later-update-wins within one transform (template "Second" over "First", description persists). `test/skill.test.ts` (125L, 2 `it.live`): "registers sources and resolves later source precedence" pins Source dedupe + later-source override; "loads URL sources and filters skills for agents" pins per-source cache (pulls===1 across two list() calls) + PermissionV2 deny filtering. `test/catalog.test.ts` (353L, 13 `it.effect`): "normalizes provider/model baseURL into api url" pins normalizeApi; "resolves provider and model request merges" pins provider-under-model merge. `test/integration.test.ts` (349L, 9 `it.effect`): "registers and overrides methods independently" pins method upsert-by-id and override-then-revert on scope close; "projects credential and env connections" pins newest-credential-first projection. Source pin:
```bash
grep -c 'selectedDefault' packages/core/src/agent.ts          # expect 4
grep -c 'Source.equals' packages/core/src/skill.ts           # expect 1
grep -c 'normalizeApi' packages/core/src/catalog.ts          # expect 3
grep -c 'resolveConnections' packages/core/src/integration.ts # expect 4
grep -c 'toReversed' packages/core/src/integration.ts        # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "AgentV2 CommandV2 SkillV2 Catalog Integration draft update remove Info.empty DeepMutable method upsert implementations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the draft contract: get-or-create via an empty factory, mutate a deep-mutable row, re-pin identity after mutation, delete on remove, and keep reads on committed state only. Adopt SkillV2's sources-not-rows shape when contributions are directories/URLs whose contents load lazily. Adapt the per-domain defaults and Catalog's nested two-level draft to your schema; omit the Effect/Schema plumbing. Coverage caveat: Codebase Memory MCP not connected this session — Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
