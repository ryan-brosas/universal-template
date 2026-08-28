<!-- capsule-v2 -->
# SessionManager close identity — re-entrant close when restore races dispose

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you make session close re-entrant safe when a concurrent restore can reuse the same session id while the old instance is still disposing?

## closing map keyed by instance identity
**Path/Symbol:** `src/acp/session.ts` `SessionManager` — `closing` map (:157), `closeSession` (:178-194), `disposeAll` (:161-163), `close`/`closeAllExcept` (:174-204), `create` error mapping (:220-251).
**Signature:** `async closeSession(sessionId: string): Promise<void>`; `private readonly closing = new Map<string, { session: PiAcpSession; promise: Promise<void> }>()`.
**Data Shape:** `closing` maps sessionId → the exact session instance being disposed plus its dispose promise; `sessions: Map<sessionId, PiAcpSession>` is the live registry.

### Decisive source
```ts
async closeSession(sessionId: string): Promise<void> {
  const existing = this.closing.get(sessionId)
  const session = this.sessions.get(sessionId)
  if (!session) return
  // A concurrent restore can install a new session under the same id while
  // the previous one is still closing; only reuse the in-flight promise when
  // it belongs to the exact session instance being closed.
  if (existing && existing.session === session) return existing.promise

  // Remove it before awaiting disposal so incoming MCP messages cannot route to a closing bridge.
  this.sessions.delete(sessionId)
  const promise = session.dispose().finally(() => {
    if (this.closing.get(sessionId)?.session === session) this.closing.delete(sessionId)
  })
  this.closing.set(sessionId, { session, promise })
  await promise
}
```
```ts
// create(): spawn failure mapping + state degradation
catch (e) {
  if (e instanceof PiRpcSpawnError) throw RequestError.internalError({ code: e.code }, e.message)
  throw e
}
// getState failure degrades instead of failing the session:
const sessionId = typeof state?.sessionId === 'string' ? state?.sessionId : crypto.randomUUID()
const sessionFile = typeof state?.sessionFile === 'string' ? state?.sessionFile : null
if (sessionFile) this.store.upsert({ sessionId, cwd: params.cwd, sessionFile })
```

**Flow:** `closeSession` first checks whether an in-flight close exists for the SAME instance (identity `===`, not id equality); if a restore replaced the session under the same id, the new instance gets its own close cycle. The session leaves the live registry BEFORE `dispose()` is awaited, so `handleIncomingMcpMessage`'s scan (:212-217) can never route a message into a disposing bridge. The `finally` cleanup is itself identity-guarded so a newer entry under the same id is never deleted by the older close. `disposeAll`/`closeAllExceptAsync` fan out over `closeSession` with per-call `.catch(() => undefined)` — one bad dispose cannot fail the batch.
**Invariant:** close reuse is keyed by instance identity, never by session id alone; the live registry is mutated before the await (route-away-before-dispose); cleanup is identity-guarded; per-fanout errors are swallowed at the call site. In `create()`, a spawn failure surfaces the Node spawn code verbatim via `RequestError.internalError({code}, msg)`, and a failed `getState` degrades to a random sessionId with `sessionFile=null` (no store upsert) rather than failing session creation.
**Probe:** `test/unit/agent-gaps.test.ts` ("PiAcpAgent: closeSession cancels and disposes a live session and is idempotent otherwise" — pins closeSession double-call + unknown-id no-op at the agent layer); `test/unit/entrypoint-shutdown.test.ts` (real child pi: closing stdin waits for subprocess termination — exercises disposeAll through the awaited shutdown path); `test/component/session-queue-cancel.test.ts` "dispose settles the running prompt as cancelled (P1-1 audit)" (dispose ladder consumer side). The identity-reuse branch itself is source-read only (no direct test constructs a restore-during-close race at this pin) — recorded as a coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "SessionManager closeSession closing disposeAll create PiRpcSpawnError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the instance-identity closing map, delete-before-await routing, and identity-guarded cleanup. Adapt the fan-out error policy (swallow vs aggregate) to your shutdown semantics. Omit the `getState` random-sessionId degradation only if your protocol requires server-asserted session ids.
