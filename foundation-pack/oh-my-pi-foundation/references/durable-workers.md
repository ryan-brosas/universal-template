<!-- capsule-v2 -->
# Durable workers — journaled child sessions, not in-memory promises

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory project `oh-my-pi`. **Path:** `packages/coding-agent/src/vibe/runtime.ts` (+ `state.ts`). **Question:** How do persistent workers survive reloads without crossing parent-session ownership?

## Source contract
**Path/Symbol:** `vibe/runtime.ts:VibeSessionRegistry` (408+): `rehydrate` (834–…), `send` (1040–1072), `wait` (1080–…), `#registerTurnJob` (1477).
**Signature:** `rehydrate(session: VibeParentSession): Promise<number>`; `send(session, { session, message }): Promise<VibeSendOutcome>`; `wait(session, { sessions?, timeoutMs?, signal? })`.
**Data Shape:** `ownerScope + parentSessionId + parentSessionFile`, journal lifecycle events, in-flight job snapshot, terminal tombstone (`state: "dead"`), send outcomes `{ mode: "steered" | "queued" | "turn", jobId? }`.

### Decisive source
```ts
if (record.state === "dead") throw new ToolError(`Vibe session "${record.id}" is dead. Spawn a new one.`);
if (AgentRegistry.global().get(record.id) && !registered) {
  throw new ToolError(`Vibe session "${record.id}" no longer resolves to this parent session.`);
}
if (record.turn) {
  const live = registered?.session;
  if (live?.isStreaming) { await live.steer(message); return { id: record.id, mode: "steered" }; }
  record.queue.push(message); return { id: record.id, mode: "queued" };
}
const jobId = this.#registerTurnJob(session, manager, record, message, { first: false });
return { id: record.id, mode: "turn", jobId };
```

**Flow:** persist spawn → reconstruct ONLY matching parent scope on rehydrate → per send: refuse dead sessions and foreign-owner agents, steer a streaming worker / queue behind an open turn / launch an idle worker → snapshot watched job IDs → acknowledge exactly settled deliveries so `wait()` results are never re-delivered as async follow-ups.

**Invariant:** a parent switch suspends the old scope without tombstoning it; ownership is checked against the live registry before any delivery; `wait()` cannot mistake a queued successor for the settled job it was asked to report.

**Probe:** direct `test/interactive-mode-vibe-toggle.test.ts:217–340` preserves same-session workers and suspends only the old parent; `test/sdk-session-isolation.test.ts:285–…` verifies exact owner-scope teardown.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "VibeSessionRegistry rehydrate send wait ownerScope", limit: 16, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.vibe.runtime.VibeSessionRegistry" });
```

## Verdict
Adopt journaled worker records with owner-scoped rehydration and steer→queue→turn delivery ladders; adapt the journal format and tombstone policy to host persistence; omit the vibe/hub tool naming unless porting the whole interactive layer. Coverage caveat: tests excluded from graph index by design.
