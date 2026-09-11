<!-- capsule-v2 -->
# Harness bridge disk replay — how does a RESPAWNED runtime process serve a resume cursor for a turn it never saw?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The in-memory replay log dies with the bridge process — what exact reload protocol lets a fresh process replay the dead one's in-flight turn, including its terminal `finish`?

## NDJSON mirror + BRIDGE_REPLAY_FROM_DISK reload
**Path/Symbol:** `packages/harness/src/bridge/index.ts` — batched flush (:403–437), re-reading drain (`flushPendingEventsToDisk` :439–451), boot-time reload (:453–479), frozen rerun config (:507–519).
**Signature:** `scheduleEventFlush(): void`; `flushPendingEventsToDisk(): Promise<void>`; env gate `BRIDGE_REPLAY_FROM_DISK === '1'`.
**Data Shape:** `${bridgeStateDir}/event-log.ndjson` (one wire line per event); `rerun-start-config.json` (first-turn-only frozen copy of the start payload).

### Decisive source
```ts
// index.ts:461 — reload BEFORE accepting any connection
const replayFromDisk = procEnv.BRIDGE_REPLAY_FROM_DISK === '1';
if (replayFromDisk && existsSync(eventLogPath)) {
  try {
    const lines = readFileSync(eventLogPath, 'utf8').split('\n')
      .map(line => line.trim()).filter(Boolean);
    eventLog = lines.map(line => ({ seq: (JSON.parse(line)).seq, line }));
    seqCounter = eventLog.at(-1)?.seq ?? 0;  // cursor space stays aligned
  } catch {
    eventLog = [];   // corrupt/partial log: host degrades to `rerun`, never replays garbage
    seqCounter = 0;
  }
}
// :458 The file is NOT truncated in this mode — only a fresh `start` clears it.
```

**Flow:** every `emit` appends its line to `diskBuffer`; a setImmediate single-flight flush (`flushPromise`) drains it off the emit hot path; `flushPendingEventsToDisk` awaits each in-flight flush RE-READING `flushPromise` after every await because new buffer may have arrived while waiting; `stop`/`destroy` drain the socket first, then flush, then exit. A respawned bridge (same state dir, env flag set) loads the log pre-connection so the very first `resume{lastSeenEventId}` serves the tail.
**Invariant:** Reload happens BEFORE any connection is accepted; the restored `seqCounter` must come from the LAST persisted line so numbering stays aligned with the host's long-lived cursor; a corrupt log falls back to EMPTY (rerun recovery) rather than replaying a malformed tail; replay mode never truncates and never invokes `onStart`.
**Probe:** direct test `packages/harness/src/bridge/disk-replay.integration.test.ts:62–146` ("a respawned bridge replays a finished turn from event-log.ndjson" — second bridge's onStart THROWS if invoked; host seeded cursor 2 receives exactly `['three']` + finish, ends at lastSeenEventId 4).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "flushEventsToDisk scheduleEventFlush replayFromDisk", limit: 5 });
// verified live @9d9a73f — bridge.flushEventsToDisk :414-423; scheduleEventFlush :425-437; flushPendingEventsToDisk :439-451
```

## Verdict
Adopt write-behind ndjson mirroring + env-gated boot reload for any sandboxed process whose consumers hold durable cursors; adapt the flush trigger (setImmediate) to your loop; omit the frozen rerun-start-config unless you also need from-scratch rerun recovery. Caveat: integration test binds real sockets + filesystem and is excluded from edge runs upstream — read, not executed, in this lane.
