<!-- capsule-v2 -->
# in-memory error ring — where do recent errors live when you need them for bug reports but not forever?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Bug reports should include the last N errors, but error logging can't be allowed to grow unbounded or touch disk — what's the minimal structure?

## addToInMemoryErrorLog: fixed 100-entry shift-and-push ring
**Path/Symbol:** `src/bootstrap/state.ts`:`inMemoryErrorLog` decl `:124-125`, `addToInMemoryErrorLog` `:1215-1224`.
**Signature:** `addToInMemoryErrorLog(errorInfo: { error: string; timestamp: string }): void`; state field `inMemoryErrorLog: Array<{ error: string; timestamp: string }>`.
**Data Shape:** FIFO array capped at `MAX_IN_MEMORY_ERRORS = 100` (const lives INSIDE the function, :1219); entries are plain strings + ISO-ish timestamp string — no stack capture, no serialization.

### Decisive source
```ts
// :1215-1224
export function addToInMemoryErrorLog(errorInfo: {
  error: string
  timestamp: string
}): void {
  const MAX_IN_MEMORY_ERRORS = 100
  if (STATE.inMemoryErrorLog.length >= MAX_IN_MEMORY_ERRORS) {
    STATE.inMemoryErrorLog.shift() // Remove oldest error
  }
  STATE.inMemoryErrorLog.push(errorInfo)
}
```

**Flow:** any caught error path calls addToInMemoryErrorLog with a formatted message + timestamp → oldest silently evicted at cap → `/bug` (bug-report builder) reads the array and embeds recent errors verbatim.
**Invariant:** The ring is deliberately dumb: shift-then-push on a plain array (100 elements make O(n) shift irrelevant), no persistence, no dedup, no levels. It rides the global singleton so `resetStateForTests()` clears it automatically (:923 wholesale re-init) — a separate module-level store would need its own reset hook. Errors are captured for HUMAN diagnostics only; nothing programmatic consumes them, which is why there's no schema beyond `{error, timestamp}`.
**Probe:** Deterministic pins: `grep -n 'MAX_IN_MEMORY_ERRORS = 100' src/bootstrap/state.ts` → `1219:`; `grep -n 'Remove oldest error' src/bootstrap/state.ts` → `1221:`; `grep -n 'inMemoryErrorLog.shift()' src/bootstrap/state.ts` → `1221:`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "inMemoryErrorLog addToInMemoryErrorLog", limit: 10 });
```

## Verdict
Adopt the singleton-hosted bounded error ring for user-facing diagnostics. Adapt cap size and entry shape to your reporter. Omit persistence/levels unless something starts programmatically consuming it — that's the moment it stops being this pattern.
