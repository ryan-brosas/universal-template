<!-- capsule-v2 -->
# Mnemopi — one facade, session-scoped banks, recall orchestration

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you run persistent conversational memory with per-user banks plus a recall path that can toggle between linear and polyphonic engines without the caller caring?

## Bank + session scoping on a beam-backed facade
**Path/Symbol:** `packages/mnemopi/src/core/memory.ts:Mnemopi` (382–662) and module-level `remember/recall/get/forget/update/search/query` (568–676).
**Signature:** `new Mnemopi({ sessionId?, bank?, db?, reconcile? })`; `remember(content, opts): string`; `recall(query, topK, opts): Promise<RecallResult[]>`.
**Data Shape:** `sessionId` (default `default`), `bank` (default `default`), `dbPath` via `resolveDbPath(options, bank)`, `BeamMemory` owns the DB unless caller injects `db` (then facade re-points `beam.db` + annotations + episodic graph), `#ownsDb` decides close.

### Decisive source
```ts
this.bank = options.bank ?? "default";
this.sessionId = options.sessionId ?? options.session_id ?? "default";
this.dbPath = resolveDbPath(options, this.bank);
this.beam = new BeamMemory({ sessionId: this.sessionId, dbPath: options.db === undefined ? this.dbPath : ":memory:", ... });
this.#ownsDb = options.db === undefined;
if (options.reconcile !== false) this.#withRuntimeOptions(() => reconcileEmbeddingModel(this.beam));
```

**Flow:** constructor defaults (+ snake_case aliases) → build beam over the bank's DB path or an injected `:memory:` DB → reconcile embedding vectors only when not read-only (`reconcile: false` on an ephemeral reader must never trigger a destructive async rebuild it will exit mid-flight) → facade methods delegate per instance; module-level `setBank/getBank/getDefaultInstance` change the *default* instance. `close()` closes only when owner.

**Invariant:** read-only opens never migrate; the bank name never silently leaks into another bank's path; explicit `db` injection keeps ownership with the caller.

**Probe:** `packages/mnemopi/test/memory-facade.test.ts` (facade remember/recall across banks and injected DB), `db-page-size.test.ts` (page size seq), `cli`-stats parity test pins facade↔library equivalence.

## One recall call, two engines, explicit flags beat env
**Path/Symbol:** `packages/mnemopi/src/core/orchestrator.ts:orchestrateRecall` (39); `core/memory.ts:setBank` etc.
**Signature:** `orchestrateRecall(beam, query, topK, { forceLinear?, forcePolyphonic?, queryEmbedding?, enhanced? })`.
**Data Shape:** query embedding (auto-embedded by `embedQuery` when absent; explicit `null` is preserved as no-embedding), beam engine with `recall`/`recallEnhanced`.

### Decisive source
```ts
const polyphonic = !options.forceLinear && (options.forcePolyphonic === true || polyphonicRecallIsEnabled());
let queryEmbedding = options.queryEmbedding;
if (queryEmbedding === undefined && query.length > 0) queryEmbedding = await embedQuery(query);
if (polyphonic) return polyphonicRecall(beam, query, topK, { ...options, queryEmbedding });
const linearOptions = toLinearRecallOptions({ ...options, queryEmbedding });
if (options.enhanced === true && typeof beam.recallEnhanced === "function") return beam.recallEnhanced(query, topK, linearOptions);
return beam.recall(query, topK, linearOptions);
```

**Flow:** engine decided per call — `forcePolyphonic` wins unless `forceLinear`; env toggle is the default. `embedQuery` returning `null` (embeddings disabled / no provider) is a no-op for FTS-only deployments; `forceLinear` passes linear options; `enhanced` prefers `beam.recallEnhanced`. Callers shear none of the engine choice — the orchestrator hides linear vs poly.

**Invariant:** no engine path is hidden behind exception; the fallback always returns a recall. `polyphonicReturnEnabled` treats only truthy `0/false/no/off` as disabled, never throwing on malformed metadata in `parseMetadata`.

**Probe:** `tests/polyphonic-recall.test.ts` (engine-level cosine/allow-norm), `tests/orchestrator.test.ts` (explicit flag matrix: forceLinear beats forcePolyphonic, forcePolyphonic beats env), `tests/memory-facade.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(orchestrateRecall|polyphonicRecallIsEnabled|polyphonicRecall|setBank|getDefaultInstance|resolveDbPath)$", limit: 14, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.mnemonic.src.core.memory.Mnemopi" });
```
