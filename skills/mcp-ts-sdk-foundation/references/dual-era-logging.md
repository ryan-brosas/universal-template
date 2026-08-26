<!-- capsule-v2 -->
# Dual-era logging threshold — how does one log() call honour a per-request envelope key and a session-scoped setLevel at once?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How do you filter log notifications when the new protocol declares thresholds per request but the old one negotiates them per session?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/server.ts`: `buildContext` ctx.mcpReq.log closure (:384-416), `_loggingLevels` map (:432), `LOG_LEVEL_SEVERITY` (:435), `isMessageIgnored` (:438-441), `_registerLoggingHandler` (:361-372).
**Signature:** `log(level, data, logger?)` inside ServerContext.mcpReq; severity = index in `LoggingLevelSchema.options`.
**Data Shape:** `_loggingLevels: Map<sessionId | undefined, LoggingLevel>`; modern key = `_meta[LOG_LEVEL_META_KEY]`.

### Decisive source
```ts
let threshold: LoggingLevel | undefined;
if (this._servedModernEra()) {
    threshold = ctx.mcpReq.envelope?.[LOG_LEVEL_META_KEY] as LoggingLevel | undefined;
    if (threshold === undefined) return Promise.resolve();   // absent key SUPPRESSES on 2026 era (spec MUST NOT send)
} else {
    threshold = this._loggingLevels.get(ctx.sessionId) ?? this._loggingLevels.get(undefined); // session, then default bucket
}
if (threshold !== undefined && this.LOG_LEVEL_SEVERITY.get(level)! < this.LOG_LEVEL_SEVERITY.get(threshold)!) {
    return Promise.resolve();
}
// Emit request-related so the notification rides the IN-FLIGHT exchange: without the
// related-request stamp, per-request hosting silently drops it (no session-wide stream exists).
return ctx.mcpReq.notify({ method: 'notifications/message', params: { level, data, logger } });
```

**Flow:** capability gate (`_capabilities.logging`, else no-op) → era branch picks the threshold source → severity compare (index order of the zod enum options) → emit via request-scoped notify.

**Invariant:** The SAME absence means OPPOSITE things per era: on the 2026 envelope an absent `logLevel` suppresses; on the 2025 session an absent `logging/setLevel` means NO filter. `logging/setLevel` keys its map by `ctx.sessionId || http 'mcp-session-id' header || undefined` — the undefined bucket is the stateless/default tier. Unparseable levels are ignored (parse-fail ⇒ no map write). Notifications must ride the request exchange or per-request hosting drops them.

**Probe:** `packages/server/test/server/server.test.ts` :52-88 (`_oninitialize` propagates negotiated version incl. transport); logging behavior pinned through `sendLoggingMessage`/`isMessageIgnored` path and `inputRequired.test.ts` shim legs; coverage caveat: no dedicated upstream unit suite for the buildContext closure at this pin — pinned indirectly via serving-entry tests.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "LOG_LEVEL_META_KEY _loggingLevels isMessageIgnored buildContext", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt dual-source threshold resolution + enum-index severity + related-request stamping for request-scoped notifications; adapt the meta-key name/session id plumbing; omit SEP-2577 migration guidance.
