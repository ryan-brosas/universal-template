<!-- capsule-v2 -->
# Doc Shutdown Ladder — in what order do you tear down a live collaborative document so nothing is lost and nothing hangs?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the shutdown ordering (and per-step timeout policy) for a stateful document object holding clients, a sandbox engine, an SQLite file, timers, and background queues?

## Idempotent mute-first ladder with safeCallAndWait timeouts and parallel final teardown
**Path/Symbol:** `app/server/lib/ActiveDoc.ts` — `shutdown()` (758–767, `this._doShutdown ||= this._doShutdownImpl(...)` idempotency), `_doShutdownImpl` (2590–2694), timeout helper via `timeoutReached(Deps.SHUTDOWN_ITEM_TIMEOUT_MS=5000)`; keep-open interplay: `@ActiveDoc.keepDocOpen` decorator on load/create/apply paths, `KEEP_DOC_OPEN_TIMEOUT_MS = 5min` (:236) capping pending-action holds.
**Signature:** `shutdown(options?: { beforeShutdown?(): Promise<void>, afterShutdown?(): Promise<void> }): Promise<void>` — hooks run with NO timeout (hangs make the doc unusable by design).
**Data Shape:** teardown targets enumerated inline: clients set, webhook queue, attachment manager, pubsub subscription, TTL fetch cache, intervals, throttled reporters, doc storage, plugin manager, sandbox engine.

### Decisive source
```ts
const safeCallAndWait = async (funcDesc: string, func: () => Promise<unknown>) => {
  try {
    if (await timeoutReached(Deps.SHUTDOWN_ITEM_TIMEOUT_MS, func())) {
      this._log.error(docSession, `${funcDesc} timed out`);
    }
  } catch (err) { this._log.error(docSession, `${funcDesc} failed`, err); }
};
...
if (this.docClients.clientCount() > 0) {           // evict clients FIRST
  await this.docClients.broadcastDocMessage(null, "docShutdown", null);
  this.docClients.interruptAllClients();
  this.docClients.removeAllClients();
}
this._webhookQueue.shutdown();
await safeCallAndWait("attachmentFileManager", ...); // transfers finish BEFORE DocStorage dies
...
this._shuttingDown = true;   // blocks new engine creation before killing it
await Promise.all([
  this.docStorage.shutdown(),
  this.docPluginManager?.shutdown(),
  this._isSnapshot ? undefined : dataEngine?.shutdown(),
]);
```
Tail: usage sync deferred to the very end (`syncUsageToDatabase` only after all measurement steps ran); `RemoveStaleObjects` user action is applied pre-teardown while the engine still lives; `finally { this._docManager.removeActiveDoc(this); }` guarantees deregistration even on partial failure.

**Flow:** mute + disable inactivity timer → caller's `beforeShutdown` → evict all clients with explicit docShutdown notice → stop webhook queue → drain attachment transfers → unsubscribe pubsub → clear TTL-cache timers → cancel all intervals in parallel → final measurements/cleanup under 5s each → close storage manager → block engine creation then shut storage+plugins+engine in PARALLEL → wait out straggler initialization → `afterShutdown` hook → deregister from DocManager in `finally`.
**Invariant:** shutdown runs EXACTLY ONCE per object regardless of concurrent callers (`_doShutdown ||=`) and never throws past its internal try/except-per-item — every individual step failing or timing out must not prevent later (more important) steps. Order constraints are semantic, not arbitrary: clients before queues (no new work), attachments before storage (transfers need the DB), `_shuttingDown = true` BEFORE killing the engine (blocks re-creation races noted vs Sharing.ts's Calculate check), usage-sync last (needs final numbers). The 5-second cap applies to optional cleanup only — the two hooks and client eviction are unbounded because half-evicting clients is worse than slow shutdown.
**Probe:** direct tests `test/server/lib/ActiveDocShutdown.ts`: "should close ActiveDoc if there are no clients connected" (:60), "...while there are clients connected" (:72), "...while an import is pending" (:112), "...while loading" (:144), "...in infinite loop after timeout" (:183), plus VACUUM-before-close assertions at :352/:365 in the same suite.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "_doShutdownImpl shutdown safeCallAndWait ActiveDoc", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the canonical ordering template for any long-lived stateful server object (doc/cache/session workers). Adapt which resources exist in your stack and the timeout budget; keep the three structural ideas — single-shot idempotency, per-item timeout isolation, semantically-ordered parallel tail. Omit the keepDocOpen decorator machinery unless you also auto-retire idle documents.
