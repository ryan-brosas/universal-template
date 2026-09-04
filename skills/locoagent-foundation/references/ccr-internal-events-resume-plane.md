<!-- capsule-v2 -->
# CCR internal-events resume plane — how do you persist worker-private transcript state and read it back across restarts with cursor pagination?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the write/read contract for session-resume data that must survive worker crashes but stay invisible to frontend clients?

## Two event classes; cursor-paginated reads with null-normalized failure
**Path/Symbol:** `src/cli/transports/ccrClient.ts`: `InternalEvent`/:233-241, `writeInternalEvent`/:788-814, `flushInternalEvents`/:816-822, `readInternalEvents`/:836-844, `readSubagentInternalEvents`/:846-858, `paginatedGet`/:860-899, `getWithRetry`/:901-958; consumer wiring `src/cli/remoteIO.ts`:140-153.
**Signature:** `writeInternalEvent(eventType, payload, {isCompaction?, agentId?})`; readers return `Promise<InternalEvent[] | null>`; `getWithRetry<T>`: 10 attempts, backoff `Math.min(500 * 2**(attempt-1), 30_000) + Math.random()*500`.
**Data Shape:** InternalEvent = `{event_id, event_type, payload, event_metadata?, is_compaction, created_at, agent_id?}`; list response `{data: InternalEvent[], next_cursor?}`; subagent variant passes `{subagents: 'true'}`.

### Decisive source
```ts
// These events are NOT visible to frontend clients — they store worker-internal
// state (transcript messages, compaction markers) needed for session resume.
async writeInternalEvent(eventType, payload, {isCompaction=false, agentId}={}) {
  const event = {
    payload: { type: eventType, ...payload,
      uuid: typeof payload.uuid === 'string' ? payload.uuid : randomUUID() },
    ...(isCompaction && { is_compaction: true }),
    ...(agentId && { agent_id: agentId }),
  }
  await this.internalEventUploader.enqueue(event)
}
```
```ts
do {
  ...url.searchParams.set('cursor', cursor)...
  const page = await this.getWithRetry<ListInternalEventsResponse>(...)
  if (!page) return null          // retries exhausted ⇒ caller sees NO resume data
  allEvents.push(...(page.data ?? []))
  cursor = page.next_cursor
} while (cursor)
```

**Flow:** the REPL writes transcript entries/compaction markers via a sessionStorage indirection (`setInternalEventWriter` — remoteIO :143-145) so the rest of the codebase stays transport-blind; between turns and at shutdown callers `flushInternalEvents()` to force persistence. On resume remoteIO installs `setInternalEventReader(readInternalEvents, readSubagentInternalEvents)` (:150-153); foreground events come back from the LAST COMPACTION BOUNDARY, subagents merge ALL non-foreground agents each from ITS OWN compaction point. Control_requests are marked processed and never re-delivered on restart (:528-529) — that asymmetry is WHY the prior worker's state must be re-read (worker-state GET in the init handshake capsule).
**Invariant:** Failure normalizes to NULL everywhere — a failed resume read degrades to "fresh session", never throws into startup. Retry budget is per PAGE (each page gets fresh 10 attempts with exp+rand(500ms) backoff). 409 epoch mismatch is checked INSIDE getWithRetry's loop too. Spread-conditional fields (`...(x && {...})`) keep absent flags off the wire rather than sending false/undefined. UUID injection again makes uploads idempotent under retry.
**Probe:** `grep -n "NOT visible to frontend clients" src/cli/transports/ccrClient.ts` (`:790`), `grep -n "subagents: 'true'" src/cli/transports/ccrClient.ts` (`:855`), `grep -n "500 \* 2 \*\* (attempt - 1)" src/cli/transports/ccrClient.ts` (`:929,:948`), `grep -n "setInternalEventReader" src/cli/remoteIO.ts` (`:21,:150`). No upstream unit tests — deterministic anchors are the probe tier.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", name_pattern: "^(paginatedGet|readInternalEvents|readSubagentInternalEvents)$", limit: 5 });
// paginatedGet :864-899 · readInternalEvents :842-844 · readSubagentInternalEvents :852-858 (executed live pre-write)
```

## Verdict
Adopt for any resumable worker: private event channel + writer/reader indirection + compaction-boundary semantics. Adapt pagination params to your API's cursor shape. Omit the subagent merge only if your workers are single-agent.
