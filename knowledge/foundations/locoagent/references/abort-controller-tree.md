<!-- capsule-v2 -->
# Abort-controller tree kit — how do child cancellations compose without leaks?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How are hierarchical abort signals built so children die with parents, selective aborts stay local, and abandoned controllers GC cleanly?

## createChildAbortController + createCombinedAbortSignal
**Path/Symbol:** `src/utils/abortController.ts` — `createChildAbortController` (:68-96), `propagateAbort` (:20-26), `removeAbortHandler` (:31-38); `src/utils/combinedAbortSignal.ts` — `createCombinedAbortSignal` (:15-48).
**Signature:** `createChildAbortController(parent, maxListeners?) → AbortController` (child aborts WITH parent; child abort does NOT touch parent); `createCombinedAbortSignal(signal?, {signalB?, timeoutMs?}) → {signal, cleanup}` (aborts on ANY input or timeout; caller MUST call cleanup).
**Data Shape:** WeakRef pair + bound module-scope handlers (no per-call closures retained); `{once:true}` on both directions.

### Decisive source
```ts
// WeakRef prevents the parent from keeping an abandoned child alive.
// If all strong references to child are dropped without aborting it,
// the child can still be GC'd — the parent only holds a dead WeakRef.
const weakChild = new WeakRef(child)
parent.signal.addEventListener('abort', handler, { once: true })
// Auto-cleanup: remove parent listener when child is aborted (from any source).
child.signal.addEventListener('abort', removeAbortHandler..., { once: true })

// combinedAbortSignal comment:
// Use `timeoutMs` instead of passing `AbortSignal.timeout(ms)` as a signal —
// under Bun, `AbortSignal.timeout` timers are finalized lazily and accumulate
// in native memory until they fire (measured ~2.4KB/call held for the full
// timeout duration).
timer.unref?.()   // timer cannot hold the process open
```

**Flow:** child creation fast-path: already-aborted parent ⇒ child.abort(parent.reason) immediately, no listeners; otherwise WeakRef-bound propagation listener ({once}) plus a child-side listener that detaches it on first child abort (any source) — three GC-safety properties: abandoned children collectible, dead handlers removable, no strong parent→child edge. Combined signal: pre-aborted inputs short-circuit with noop cleanup; timeout uses plain setTimeout + explicit clearTimeout in cleanup rather than AbortSignal.timeout (Bun lazy-finalization leak measured at ~2.4KB/call) and unrefs so pending waits never block process exit.

**Invariant:** (1) Direction asymmetry is the API contract — parent→child propagation, never child→parent (callers add their own bubble-back listener when a specific reason must escalate, cf. StreamingToolExecutor). (2) Reasons travel: child.abort inherits parent.signal.reason verbatim so downstream classifiers (interrupt vs sibling_error) see the original cause. (3) Every combined-signal consumer owes a cleanup call (finally/guard) or timers/listeners accumulate for the process lifetime. (4) maxListeners raised to 50 by default to silence MaxListenersExceededWarning on fan-out tools.

**Probe:** coverage caveat — no upstream tests. Deterministic pins: `grep -n "WeakRef prevents the parent" src/utils/abortController.ts` :80); `grep -n "2.4KB/call" src/utils/combinedAbortSignal.ts` :11); `grep -n "does NOT affect the parent" src/utils/abortController.ts` :56-58; graph resolves `src.utils.abortController.createChildAbortController` + `propagateAbort`/`removeAbortHandler` line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createChildAbortController createCombinedAbortSignal WeakRef", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the WeakRef child-controller pattern and manual-timeout combined signal wholesale (both are host-independent); adapt listener limits; omit nothing — this is the smallest capsule in the foundation and the easiest to port wrong. Porting trap: holding children in a plain array keeps every abandoned controller alive; using AbortSignal.timeout under Bun leaks native timers until they fire.
