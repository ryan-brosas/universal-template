<!-- capsule-v2 -->
# Session engine — event-sourced writes, paginated reads, graph-rewrite forks

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a long-lived agent conversation persist, fork, and survive abort without corrupting context?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/session/session.ts` (1,019 lines): `updateMessage` (:630-636), `updatePart` (:637-644), `messages()` (:830-853), `findMessage` (:890-907), `Session.fork` (:693-733), `Session.patch` (:736-753); `session/processor.ts` (718 lines): `SessionProcessor.handleEvent` (:296-537); `session/prompt.ts` (1,631 lines).
**Signature:** `messages()` pages 50 at a time, pushes items in reverse, then reverses once to restore chronological order; `fork` replays messages up to a target minting fresh ids while threading an `idMap` that rewrites every cross-reference.
**Data Shape:** conversation is a DAG of id references — `message.parentID`, `part.messageID`, compaction parts' `tail_start_id`; `Patch` fields are `Partial<…> | null` (absent=keep, null=clear).

### Decisive source
```ts
// updateMessage is literally just an event publish — no DB write
export function updateMessage(...) {
  return events.publish(SessionV1.Event.MessageUpdated, ...)  // :630-636
}
// fork rewrites every cross-reference, including the easy-to-miss compaction remap
if (p.type === "compaction" && p.tail_start_id) {
  p.tail_start_id = idMap.get(p.tail_start_id)  // :722-724
}
```

**Flow:** every mutation publishes an event (writes are events); reads paginate projections (cursor pagination, reverse-then-restore). Fork = graph rewrite (replay + idMap remap of all cross-refs). Patch = shallow merge with null=clear, all `set*` mutators derive from it. The stream processor is a total switch over LLM events with guards: doom-loop threshold (3 identical tool calls → permission ask, `DOOM_LOOP_THRESHOLD=3`), no-tools-in-summary, snapshot-before-stream-start (race guard :98-100), compaction as stream-control (`Stream.takeUntil(() => ctx.needsCompaction)` → Result "compact"|"stop"|"continue").
**Invariant:** abort is state-machine transitions with explicit tombstones (`interrupted:true`); consumers filter tombstones so a cancelled turn never poisons the next turn's context; a fork must remap every cross-reference or it silently corrupts on its next turn.
**Probe:** `packages/opencode/test/cli/run/session-replay.test.ts` + `session-data.test.ts` (fork mid-conversation with a compaction part; assert no clone part references an id outside the new session's set; cancel mid-stream → assistant carries AbortError, tool part `interrupted:true`, next prompt does not resend the orphaned tool_use).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Session fork idMap compaction patch event publish", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the event-sourced write / paginated-read model, graph-rewrite forking with cross-ref remapping, null=clear patch semantics, and tombstone-based abort; adapt the event bridge and cursor page size to host; omit the opencode-specific `Effect`/`Context.Service` wiring unless the target uses Effect.
