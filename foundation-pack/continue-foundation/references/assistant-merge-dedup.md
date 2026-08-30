<!-- capsule-v2 -->
# Assistant merge & dedup — when base config and local blocks collide, who wins?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you merge two unrolled assistants so user-local blocks override hub defaults without duplicate models/rules?

## Incoming-first, first-seen-wins
**Path/Symbol:** `packages/config-yaml/src/load/merge.ts:mergeUnrolledAssistants` (lines 26–59), `mergeConfigYamlRequestOptions` (61–85), `packages/config-yaml/src/load/blockDuplicationDetector.ts:BlockDuplicationDetector.isDuplicated` (40–63).
**Signature:** `mergeUnrolledAssistants(current: AssistantUnrolled, incoming: AssistantUnrolled): AssistantUnrolled`.
**Data Shape:** per block type: concat `[...incoming[type], ...current[type]]`, filter through one fresh detector; empty result collapses to `undefined` (key omitted).

### Decisive source
```ts
const duplicationDetector = new BlockDuplicationDetector();
for (const blockType of BLOCK_TYPES) {
  const allOfType = [...(incoming[blockType] ?? []), ...(current[blockType] ?? [])]; // INCOMING FIRST
  const deduplicated = allOfType.filter(b => b && !duplicationDetector.isDuplicated(b, blockType));
  assistant[blockType] = deduplicated.length > 0 ? deduplicated : undefined;
}
// identity keys: rules -> string content OR name; context -> name ?? params.title ?? provider;
// everything else -> name. First sighting wins, later duplicates are dropped.
```

**Flow:** env objects shallow-merge `current ← incoming` → request options merge where **base scalar fields override global but headers are the only deep merge** (`{ ...global, ...base, headers: { ...global.headers, ...base.headers } }`, empty header set ⇒ `undefined`) → per-type dedup with incoming priority.
**Invariant:** for any identity collision the **incoming version survives and the current/base version is filtered** — verified by tests asserting "Should keep the incoming version of gpt-4 / typescript-style / code-review / api-docs / user-data / filesystem".
**Probe:** `packages/config-yaml/src/load/mergeUnrolledAssistants.test.ts:129–456` pins incoming-wins for every block type plus string-rule dedup; `core/config/yaml/models.vitest.ts:89–122,176,313` pins the requestOptions semantics end-to-end through `llmsFromModelConfig` (model timeout/proxy beat global; global `user-agent` header survives next to model `Authorization`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.yaml.loadYaml.loadConfigYaml", direction: "outbound", depth: 2 });
// loadConfigYaml calls mergeUnrolledAssistants(config, unrolledLocal.config): local = incoming => locals win
await mcp.codebase_memory.search_graph({ project: "continue", qn_pattern: "continue\\.packages\\.config-yaml\\.src\\.load\\..*", detail: "ids", limit: 30 });
```

## Verdict
Adopt incoming-priority dedup with explicit identity keys per section and the headers-only requestOptions merge; adapt identity keys to your domain's natural uniqueness; omit BLOCK_TYPES generality if your config has a fixed shape.
