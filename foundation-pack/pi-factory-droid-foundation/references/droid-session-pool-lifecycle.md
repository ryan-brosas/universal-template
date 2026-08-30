<!-- capsule-v2 -->
# Droid session pool lifecycle — how do I pool foreign agent subprocesses per conversation and tear them down safely?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** When a host runtime spawns one external agent subprocess per conversation, what must the pool key contain, when must a live session be recreated instead of reused, and in what order is teardown performed?

## Session pool with hash-keyed reuse and ordered teardown
**Path/Symbol:** `src/providers.ts:getOrCreateEntry` (634-755), `ensureSweeper` (180-199), `destroyEntry` (201-217); constants at 62-68; `PoolEntry` at 151-174.
**Signature:** `async function getOrCreateEntry(cfg: ResolvedConfig, apiKey: string, modelId: string, reasoning: ReasoningEffort | undefined, runtime: InstanceRuntime, contextBlock: string, opts: { mode: ResolvedConfig["mode"]; tools?: Context["tools"]; toolsHash?: string }): Promise<PoolEntry>`
**Data Shape:** `pool: Map<string, PoolEntry>` where key = `` `${sha256(apiKey)}:${runtime.sessionKey}:${opts.mode}` ``. `PoolEntry` carries `contextHash`, `toolsHash`, `modelId`, `reasoning`, `lastUsedAt`, `usage: UsageTracker`, `board`, `mcpServer`, `activeTurn`. Constants: `MAX_POOL_SESSIONS = 8`, `IDLE_TTL_MS = 15*60*1000`, `SWEEP_INTERVAL_MS = 60*1000`.

### Decisive source
```ts
const keyHash = createHash("sha256").update(apiKey).digest("hex");
// Separate pools per mode so flipping agent↔pi-tools never reuses the wrong session.
const key = `${keyHash}:${runtime.sessionKey}:${opts.mode}`;
const contextHash = contextBlock ? createHash("sha256").update(contextBlock).digest("hex") : "";

let entry = pool.get(key);
// Persona/memory/skills changed mid-conversation → restart the Droid session
if (entry && entry.contextHash !== contextHash) {
  await destroyEntry(entry);
  entry = undefined;
}
...
// Room for the new subprocess: evict the least-recently-used entry.
while (pool.size >= MAX_POOL_SESSIONS) {
  const lru = [...pool.values()].sort((a, b) => a.lastUsedAt - b.lastUsedAt)[0];
  if (!lru) break;
  await destroyEntry(lru);
}
```

Teardown order (destroyEntry):
```ts
if (pool.get(entry.key) === entry) pool.delete(entry.key);
entry.usage.detach();
entry.activeTurn?.consumerAbort.abort();
entry.board?.rejectAll("droid session closed");
entry.activeTurn = null;
await entry.mcpServer?.close();   // try/catch ignore
await entry.session.close();      // try/catch — shutdown must be best-effort
```

**Flow:** ensureSweeper() → compute key/contextHash → destroy on contextHash mismatch → (pi-tools only) destroy on toolsHash mismatch → destroy on mode mismatch → same model? updateSettings in place (on failure destroy) → touch lastUsedAt and return → else LRU-evict to < cap → createSession with autonomy/permission/askUser handlers + env key → strictModelMatch guard closes+throws on resolved-model drift → store PoolEntry.
**Invariant:** A pool hit must never observe a stale persona (contextHash), stale tool set (toolsHash), wrong mode, or another account's key (keyHash in key); teardown must first remove from the map, then abort in-flight consumers, then close transports best-effort — so no turn can push events into a closed stream.
**Probe:** No dedicated upstream suite drives the pool (it needs the Droid SDK subprocess); recorded caveat. Deterministic pins: `src/providers.ts:65-68` constants; `test/` suites cover only pure helpers. The sweeper's exit hook (`process.once("exit", ...)` closing every pooled session, providers.ts:190-198) is the orphan-prevention boundary.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "getOrCreateEntry pool destroyEntry ensureSweeper", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the key composition (`hash(secret):conversationId:mode`), hash-driven recreation on context/tool-set change, LRU eviction cap, idle-TTL sweep with unref'd timer plus process-exit hook, and the delete→abort→reject→close teardown order. Adapt caps/TTLs and the settings-update-in-place branch to your host's session API. Omit Droid-specific `strictModelMatch` init-result verification unless your harness reports back its resolved model.
