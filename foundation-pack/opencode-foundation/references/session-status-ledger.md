<!-- capsule-v2 -->
# Session status ledger — how does opencode track busy/idle per session without persisting anything?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** Where does per-session run status live and what are the exact publish/evict semantics?

## In-memory instance-scoped map with idle-eviction
**Path/Symbol:** `packages/opencode/src/session/status.ts` (whole file, 56L; layer :21–52).
**Signature:** `get(sessionID) → Info` / `list() → Map<SessionID, Info>` / `set(sessionID, status) → void`.
**Data Shape:** `Info` comes from the shared schema (`SessionStatusEvent.Info`); the backing store is a plain `Map<SessionID, Info>` created inside `InstanceState.make` — one map per opencode instance, NOTHING touches disk.

### Decisive source
```ts
// status.ts:39-48 — publish BEFORE mutate; idle DELETES instead of storing
const set = Effect.fn("SessionStatus.set")(function* (sessionID: SessionID, status: Info) {
  const data = yield* InstanceState.get(state)
  yield* events.publish(Event.Status, { sessionID, status })
  if (status.type === "idle") {
    yield* events.publish(Event.Idle, { sessionID })   // second, distinct event
    data.delete(sessionID)
    return
  }
  data.set(sessionID, status)
})
// status.ts:30-33 — reads default to idle for UNKNOWN sessions
return data.get(sessionID) ?? { type: "idle" as const }
```

**Flow:** Every transition publishes `Event.Status`; going idle ADDITIONALLY publishes a dedicated `Event.Idle` and evicts the key so `list()` only ever returns ACTIVE sessions. Readers of an unknown session get synthesized `{type:"idle"}` rather than undefined.
**Invariant:** The ledger is intentionally volatile — restart wipes it and that is correct because no loop can survive the process. Idle must EVICT (not store `idle` rows) or long-lived instances accumulate one dead entry per historical session and `list()` becomes meaningless. The double-publish on idle (Status then Idle) lets subscribers choose coarse vs precise signals.
**Probe:** direct source pin:
```bash
grep -n 'data.delete\|Event.Idle\|?? { type: "idle"' packages/opencode/src/session/status.ts
```
expect exactly :44,:43,:32.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SessionStatus idle publish event bridge", limit: 5 });
// resolves the EventV2Bridge.publish sink (event-v2-bridge.ts:19-33) the ledger publishes through; the
// tiny status service closures themselves are NOT graph nodes (known Effect-fn class) — status.ts is
// 56L, read it whole.
```

## Verdict
Adopt the ephemeral map + publish-before-mutate + idle-eviction contract verbatim; adapt event bus to host; omit the schema import specifics.
