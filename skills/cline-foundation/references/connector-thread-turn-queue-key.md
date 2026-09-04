<!-- capsule-v2 -->
# connector-thread-turn-queue-key — how do you key per-thread turn queues so two messages sharing one session can never run concurrently?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** What identity rule must the turn-queue key follow, and how does the queue chain promises without leaking entries?

## The queue key mirrors the binding lookup — DMs collapse to one key, channel threads keep their own; enqueue is a promise-chained Map with identity-checked self-deletion
**Path/Symbol:** `apps/cli/src/connectors/thread-bindings.ts:resolveThreadTurnQueueKey` (:165-174) and `apps/cli/src/connectors/chat-runtime.ts:enqueueThreadTurn` (:26-42).
**Signature:** `resolveThreadTurnQueueKey(thread: Pick<ConnectorBindingThreadIdentity, "id" | "channelId" | "isDM">): string`; `enqueueThreadTurn(threadQueues: Map<string, Promise<void>>, threadId: string, work: () => Promise<void>): Promise<void>`.
**Data Shape:** `threadQueues` maps queue key → tail promise. `enqueueThreadTurn` returns the awaited work promise; the Map entry is deleted when the tail settles, but only if it is still the same promise object.

### Decisive source
```ts
// thread-bindings.ts — the doc comment states the governing law:
// This has to follow the same identity rule as findBindingForThread,
// because whatever shares a session has to share a queue.
return thread.isDM ? `dm:${thread.channelId}` : thread.id;

// chat-runtime.ts
const previous = threadQueues.get(threadId) ?? Promise.resolve();
const current = previous
	.catch(() => {})
	.then(work)
	.finally(() => {
		if (threadQueues.get(threadId) === current) {
			threadQueues.delete(threadId);
		}
	});
threadQueues.set(threadId, current);
```

**Flow:** a DM reuses ONE binding — and therefore one runtime session — for every message in the channel, so keying the queue by thread id would let two messages in the same DM run against that one session concurrently; that surfaces as "SessionRuntime.shutdown called while a run is in progress" or as two conversations interleaved in one session's history ⇒ the key collapses DMs to `dm:${channelId}` while channel threads each own their binding and keep their own key ⇒ enqueue chains onto the previous tail with a `.catch(() => {})` barrier so one failed turn cannot poison the next, then registers the new tail BEFORE returning the awaited work promise ⇒ the finally block deletes the Map entry only under an identity check, so a newer enqueued turn is never deleted by an older tail settling late.
**Invariant:** Whatever shares a session must share a queue; a failed turn never breaks the chain; Map deletion is identity-guarded against out-of-order settlement.
**Probe:** `thread-turn-queue.test.ts` (5 cases; NOTE: no thread-turn-queue.ts exists — the test name is legacy, the implementation lives in chat-runtime.enqueueThreadTurn): "collapses every message in one DM onto a single key", "keeps separate DM channels separate", "runs two messages in the same DM one after the other", "runs two channel threads at the same time". Probes: `grep -cF 'dm:${thread.channelId}' thread-bindings.ts` → 1; `grep -cF 'threadQueues.delete(threadId)' chat-runtime.ts` → 1; `grep -cF 'collapses every message in one DM onto a single key' thread-turn-queue.test.ts` → 1.

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "resolveThreadTurnQueueKey enqueueThreadTurn dm channel queue serialization", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mirror-the-binding-identity queue key and the promise-chained Map with catch-barrier and identity-checked deletion. Adapt the `dm:` prefix and the Map-of-promises shape to your scheduler. Omit Cline's webhook-server helper in the same file (commodity node:http adapter). Coverage: both sources read whole at pin; 5-case direct suite read whole; the phantom `thread-turn-queue.ts` path is recorded as a naming trap.
