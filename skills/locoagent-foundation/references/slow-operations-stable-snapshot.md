<!-- capsule-v2 -->
# slow-operations stable-snapshot — how does a 2fps dev-bar poll avoid re-rendering when nothing changed?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** A React state polled from outside the React lifecycle (TTL'd slow-op list) re-renders on every setState unless references stay stable — what's the allocation discipline?

## getSlowOperations: reference-stable reads over a TTL'd ring
**Path/Symbol:** `src/bootstrap/state.ts`:`MAX_SLOW_OPERATIONS`/`SLOW_OPERATION_TTL_MS` (`:1566-1567`), `addSlowOperation` (`:1569-1587`), `EMPTY_SLOW_OPERATIONS` (`:1589-1593`), `getSlowOperations` (`:1595-1621`).
**Signature:** `addSlowOperation(operation: string, durationMs: number): void`; `getSlowOperations(): ReadonlyArray<{ operation; durationMs; timestamp }>`.
**Data Shape:** Entries `{ operation, durationMs, timestamp }`; caps `MAX_SLOW_OPERATIONS = 10`, TTL `SLOW_OPERATION_TTL_MS = 10000` (both line-pinned :1566-1567). Sentinel shared frozen empty array for the common case.

### Decisive source
```ts
// :1570-1575 — intake filters
if (process.env.USER_TYPE !== 'ant') return
// Skip tracking for editor sessions (user editing a prompt file in $EDITOR)
// These are intentionally slow since the user is drafting text
if (operation.includes('exec') && operation.includes('claude-prompt-')) {
  return
}
// :1595-1621 — read path
export function getSlowOperations() {
  if (STATE.slowOperations.length === 0) {
    return EMPTY_SLOW_OPERATIONS          // stable ref → Object.is bails
  }
  const now = Date.now()
  // Only allocate a new array when something actually expired; otherwise keep
  // the reference stable across polls while ops are still fresh.
  if (STATE.slowOperations.some(op => now - op.timestamp >= SLOW_OPERATION_TTL_MS)) {
    STATE.slowOperations = STATE.slowOperations.filter(
      op => now - op.timestamp < SLOW_OPERATION_TTL_MS)
    if (STATE.slowOperations.length === 0) return EMPTY_SLOW_OPERATIONS
  }
  // Safe to return directly: addSlowOperation() reassigns STATE.slowOperations
  // before pushing, so the array held in React state is never mutated.
  return STATE.slowOperations
}
```

**Flow:** operations record via addSlowOperation (gated + editor-filtered) → dev bar polls getSlowOperations at ~2fps → poll passes the SAME array reference while nothing expired → caller's `setState(prev)` with Object.is equality skips the render → expiry or new entry produces a NEW array → exactly one render per real change.
**Invariant:** The contract between producer and React is: NEVER mutate an array that has escaped into state. Both write paths honor it — add filters-then-REASSIGNS before push, and the reader only reallocates when an entry actually crossed the TTL. The shared `EMPTY_SLOW_OPERATIONS` constant makes the most common poll (nothing tracked) allocation-free AND referentially identical. Intake gating (env channel check first, then intentional-slowness filter) keeps drafting-in-$EDITOR sessions from permanently occupying the 10-slot window.
**Probe:** Deterministic pins: `grep -n 'MAX_SLOW_OPERATIONS = ' src/bootstrap/state.ts` → `1566:`; `grep -cn 'return EMPTY_SLOW_OPERATIONS' src/bootstrap/state.ts` → `2` (:1603 + :1615); `grep -n 'never mutated' src/bootstrap/state.ts` → `1619:`; `grep -n 'claude-prompt-' src/bootstrap/state.ts` → `1573:`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "slowOperations dev bar getSlowOperations", limit: 10 });
```

## Verdict
Adopt reference-stable snapshot reads for any externally-polled store feeding React state (or any diff-by-identity consumer). Adapt caps/TTL to your UI. Omit the ant-channel intake gate — it's distribution-specific policy, not mechanism.
