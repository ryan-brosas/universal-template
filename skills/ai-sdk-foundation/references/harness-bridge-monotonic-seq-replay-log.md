<!-- capsule-v2 -->
# Harness bridge replay log — how do per-turn memory bounds coexist with a client cursor that outlives turns?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** A reconnecting client resumes from `lastSeenEventId` across MANY turns — why must the server's seq counter never reset even though its in-memory event log is cleared every turn?

## Monotonic seq + turn-scoped log inside runBridge
**Path/Symbol:** `packages/harness/src/bridge/index.ts` — state comment (:396–401), `emit` (:522–536), synchronous `replay` (:538–544), clear-at-start (:667–671).
**Signature:** `emit(event: BridgeEvent): void`; `replay(ws, afterSeq: number): void`.
**Data Shape:** `seqCounter: number` (process-lifetime); `eventLog: Array<{seq, line}>` (current turn only); wire line = `JSON.stringify({...event, seq})`.

### Decisive source
```ts
// index.ts:396 — the two clocks are deliberately asymmetric
// `seq` is monotonic across the whole process — never reset — because the
// host's SandboxChannel cursor (`lastSeenEventId`) lives across turns. The
// log *contents* are cleared at the start of each turn to bound memory; the
// just-finished turn stays replayable until the next `start`.
let seqCounter = 0;
let eventLog: Array<{ seq: number; line: string }> = [];
...
const emit = (event: BridgeEvent): void => {
  const seq = ++seqCounter;
  const line = JSON.stringify({ ...event, seq });
  eventLog.push({ seq, line });          // log FIRST …
  if (activeSocket?.readyState === WS_OPEN) {
    try { activeSocket.send(line); } catch {}   // … send best-effort
  }
};
case 'start':
  eventLog = [];                    // clear previous turn; keep seqCounter monotonic
```

**Flow:** emit appends to the in-memory log (+disk mirror) BEFORE attempting the live send, so a dropped socket loses nothing — replay serves the tail on `resume`. At each `start` the log empties but numbering continues; a fresh client resuming from 0 therefore sees only the CURRENT turn's events, numbered e.g. [3,4] after two turns.
**Invariant:** `replay(ws, afterSeq)` is SYNCHRONOUS so no live event can slip ahead of the replayed tail; seq gaps across turns are legal and MUST be tolerated by resumers (cursor comparisons are `>`, never density checks); live sends are always allowed to fail.
**Probe:** direct test `packages/harness/src/bridge/index.test.ts:448–477` ("clears the log per turn but keeps seq monotonic across turns" — second turn emits seq 3,4; fresh resume{0} receives exactly `[3,4]`), :137–183 ("withholds live events from a replacement connection until replay completes" — B gets only seq 3,4 past cursor 2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "emit replay eventLog seqCounter", limit: 5 });
// verified live @9d9a73f — bridge.replay :538-544 rank#1; bridge.emit :522-536
```

## Verdict
Adopt the asymmetric pair (process-monotonic cursor space × turn-scoped replay buffer) plus append-before-send ordering for any resumable event stream; adapt buffer bounds/clear triggers to host retention policy; omit ndjson disk mirroring if you have no crash-recovery requirement (see harness-bridge-disk-replay-recovery.md for when you do). Caveat: none — both orderings are unit-pinned at this pin.
