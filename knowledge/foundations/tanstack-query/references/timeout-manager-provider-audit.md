<!-- capsule-v2 -->
# TimeoutManager swappable provider + audited tick-0 — how are thousands of timers kept swappable and auditable?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How does a library route ALL its timers through one backend so hosts can coalesce them — without breaking spy-based tests or cross-provider timer IDs?

## TimeoutManager class + systemSetTimeoutZero escape hatch
**Path/Symbol:** `packages/query-core/src/timeoutManager.ts:TimeoutManager` (:64–127), `defaultTimeoutProvider` (:33–51), `systemSetTimeoutZero` (:136–138); consumers `Removable.scheduleGc`, `utils.sleep`, observer stale/refetch timers.
**Signature:** `setTimeoutProvider(provider: TimeoutProvider<TTimerId>)`; provider shape `{ setTimeout, clearTimeout, setInterval, clearInterval }` with `ManagedTimerId = number | { [Symbol.toPrimitive]: () => number }`.
**Data Shape:** private `#provider` (defaults to platform globals), dev-only `#providerCalled` latch.

### Decisive source
```ts
// defaultTimeoutProvider — wrapper syntax is load-bearing:
setTimeout: (callback, delay) => setTimeout(callback, delay),
// If we use direct references here, then anything that wants to spy on or
// replace the global setTimeout ... won't work since we'll already
// have a hard reference to the original implementation at import time.

setTimeoutProvider(provider) {
  if (process.env.NODE_ENV !== 'production') {
    if (this.#providerCalled && provider !== this.#provider) {
      console.error(
        `[timeoutManager]: Switching provider after calls to previous provider might result in unexpected behavior.`,
      )
    }
  }
  this.#provider = provider
  ...
}

export function systemSetTimeoutZero(callback: TimeoutCallback): void {
  setTimeout(callback, 0)
}
```

**Flow:** gcTime/staleTime/refetchInterval/sleep all call timeoutManager.setTimeout → #provider. notifyManager deliberately does NOT go through it (`systemSetTimeoutZero` exists so an auditor can grep for direct event-loop usage and find exactly the sanctioned one).
**Invariant:** (1) wrapper functions keep global spies working after import; (2) switching providers mid-flight is warned about in dev because old timer IDs may collide with new ones (clearTimeout could cancel an arbitrary different timer) — documented in-source with two rejected mitigations; (3) ManagedTimerId accepts NodeJS-style objects via Symbol.toPrimitive; (4) TimeoutCallback type is `(_: void) => void` so `new Promise(r => timeoutManager.setTimeout(r, n))` type-checks.
**Probe:** `grep -n "systemSetTimeoutZero" packages/query-core/src/*.ts | grep -v timeoutManager.ts | head -3` (notifyManager.ts :3 import) and `grep -n "providerCalled" packages/query-core/src/timeoutManager.ts` (≥4 hits).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^TimeoutManager$|^defaultTimeoutProvider$", limit: 5 });
```

## Verdict
Adopt provider indirection for any timing-heavy library; copy the in-source comment rationale — it prevents regressions to direct references. Adapt provider implementations (coalescing heap timers for thousands-of-timeouts scalability, per in-source note). Omit setInterval plumbing if you have no interval needs.
