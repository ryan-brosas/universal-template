<!-- capsule-v2 -->
# ACP recovered-session update queue — how do semantic updates and the prompt's own stop share one ordered stream after a session is restored?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** After resuming a lost process, how do you join asynchronous protocol updates with the prompt request's own resolution into one consumer queue without letting a stale error kill the next prompt?

## Buffered value/error queue with per-attempt error clearing
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/recovered-session.ts` — `createACPRecoveredSessionUpdates` (:107–170), `createACPRecoveredSession` (:38–105), `assertACPResumeCapability` (:17–36).
**Signature:** `{enqueue(value): void; reject(error): void; clearErrors(): void; fail(error): void; next(): Promise<ActiveSessionMessage>}`.
**Data Shape:** entries are `{type:'value', value}` or `{type:'error', error}` buffered in `values[]`; live waiters in `waiters[]`; one terminal `failure` latch.

### Decisive source
```ts
// recovered-session.ts:125–147 — buffer-ahead-of-waiter, latch-once terminal
enqueue(value) { if (failed) return; const waiter = waiters.shift();
  if (waiter == null) values.push({ type: 'value', value }); else waiter.resolve(value); },
reject(error)  { if (failed) return; const waiter = waiters.shift();
  if (waiter == null) values.push({ type: 'error', error }); else waiter.reject(error); },
clearErrors()  { for (let index = values.length - 1; index >= 0; index--)
                   if (values[index]?.type === 'error') values.splice(index, 1); },
fail(error)    { if (failed) return; failed = true; failure = error;
                 for (const waiter of waiters.splice(0)) waiter.reject(error); },
// :60–75 (session wrapper) — the prompt's own resolution enters the SAME queue
const response = agent.request(...session.prompt, { sessionId, prompt });
void response.then(value => { updates.enqueue({ kind: 'stop', response: value, stopReason: value.stopReason }); },
                   error => updates.reject(error));
```

**Flow:** restored session wraps the raw client: `prompt()` clears buffered errors from any PRIOR attempt, fires the prompt request, and routes its fulfillment to a `stop` entry and its rejection through `reject` — the same queue that receives asynchronous `session_update` notifications → `runTurn` loops on `nextUpdate()` until it sees the stop → `dispose()` latches terminal failure so pending and future readers reject with 'Recovered ACP session disposed.' Ordering is FIFO across BOTH sources because everything funnels through one buffer.
**Invariant:** one queue, two producers, strict arrival order; errors are DATA until consumed and are cleared at each new prompt attempt (a stale error from turn N must never fail turn N+1); terminal `fail` wins over everything and is idempotent; lossy rerun additionally requires the agent to advertise `sessionCapabilities.resume` (`assertACPResumeCapability`).
**Probe:** direct tests `packages/harness-acp/src/v1/bridge/recovered-session.test.ts:34–89` ("routes resumed-session updates and the prompt stop through one queue" — update before stop, dispose rejects `nextUpdate` with 'Recovered ACP session disposed.'), :91–116 (`promptWithMeta` sends `_meta` verbatim), :11–32 (missing resume capability ⇒ HarnessBridgeCapabilityUnsupportedError).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createACPRecoveredSessionUpdates enqueue clearErrors fail recoveredSessionUpdates", limit: 10 });
```

## Verdict
Adopt the single-buffer two-producer queue with per-attempt error clearing whenever an async protocol stream and a request resolution must merge post-recovery; adapt entry kinds; omit ACP method names. Caveat: none — all three behaviors unit-pinned.
