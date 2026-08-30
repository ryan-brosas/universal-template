<!-- capsule-v2 -->
# Pi-tools turn FSM — how do I structure a multi-request turn where the assistant message pauses mid-turn awaiting tool results?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** When a bridged agent's tool calls must be answered by the host's NEXT stream call, what state machine turns "one request = one assistant message" into a resumable multi-phase turn?

## Three phases on the pooled entry; continuation re-arms the SAME turn state
**Path/Symbol:** `src/pi-tools-mode.ts:PiToolsTurnState` (32-44), `attachPiStream` (70-81), `isAwaitingPiTools` (66-68), `runPiToolsConsumer` (90-145), `handleDroidEvent` (147-218); dispatch at `src/providers.ts:streamDroidPiTools` (448-548).
**Signature:** `type PiToolsPhase = "idle" | "streaming" | "awaiting-results"`; `runPiToolsConsumer(options: {session, board, turn, prompt, images, signal?, onUsage?}): Promise<void>`.
**Data Shape:** Per pool entry: `activeTurn: PiToolsTurnState | null` holding `{phase, piStream, output, model, indexOf, openTextKeys, openThinkingKeys, consumerAbort: AbortController, consumerDone: Promise<void>, error?}`.

### Decisive source
Dispatch — three outcomes ordered continuation → supersede → new turn:
```ts
// Continuation: Pi executed tools and is delivering results into the hanging MCP handlers.
if (isAwaitingPiTools(entry.activeTurn) && entry.board) {
  deliverPiToolResults(entry.board, context);
  attachPiStream(entry.activeTurn!, stream);      // fresh output envelope, same turn
  return;
}
// New user turn.
if (entry.activeTurn && entry.activeTurn.phase !== "idle") {
  entry.activeTurn.consumerAbort.abort();
  entry.board?.rejectAll("superseded by new pi-tools turn");
  entry.activeTurn = null;
}
```

`attachPiStream` starts a FRESH assistant message while keeping turn identity:
```ts
turn.output = createEmptyOutput(turn.model);   // Pi expects one message per streamSimple
turn.indexOf = new Map(); turn.openTextKeys = new Set(); turn.openThinkingKeys = new Set();
turn.phase = "streaming";
stream.push({ type: "start", partial: turn.output });
```

The ToolCall event suspends the Pi-visible stream and parks the phase:
```ts
board.noteToolCall(id, name);                    // id → board even if no host stream
closeOpenBlocks(turn);
turn.output.content.push(toolCall);
turn.output.stopReason = "toolUse";
stream.push({ type: "done", reason: "toolUse", message: turn.output });
stream.end(); turn.piStream = null;
turn.phase = "awaiting-results";                 // next request is a continuation
```

Consumer error path fails loud AND unblocks the board:
```ts
} catch (error) {
  // ... push {type:"error"} + end stream ...
  board.rejectAll(`pi-tools consumer stopped: ${message}`);
  turn.phase = "idle";
}
```

**Flow:** idle —(new user turn: beginTurn, start event, steer-prefixed prompt, launch consumer)→ streaming —(our ToolCall: close blocks, emit toolcall events + done(toolUse), end stream)→ awaiting-results —(next streamSimple: deliver results into board handlers, attachPiStream)→ streaming …; final pass through streaming without a ToolCall closes open blocks, emits done(stop|length), ends, phase=idle. Supersession aborts the old consumer and rejects pending handlers before nulling activeTurn.
**Invariant:** Exactly one live consumer per entry; each host stream sees exactly ONE assistant message (continuation swaps in a fresh envelope instead of appending across messages); every stream ends exactly once (`end()` on done, error, or suspend paths); the board is never left with pending handlers after supersede/error/teardown.
**Probe:** No dedicated upstream suite drives the full FSM (needs a Droid subprocess) — recorded caveat. Deterministic pins: providers.ts:472-484 (ordering), pi-tools-mode.ts:70-81 / 190-210 (envelope reset + suspend), 227-243 (error+rejectAll). The board plane beneath it IS directly tested (pi-tools-bridge.test.ts).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "PiToolsTurnState attachPiStream runPiToolsConsumer handleDroidEvent awaiting-results", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the phase enum living on the POOLED ENTRY (not the request), continuation-checked-before-supersede ordering, fresh-envelope-per-host-stream, and reject-all-on-teardown. Adapt event/stream vocabulary to your host. Omit the steer-prompt copy and the Droid SDK event enum.
