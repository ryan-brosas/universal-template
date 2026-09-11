<!-- capsule-v2 -->
# Abortable settlement primitives — how do you race an operation against an AbortSignal and wait-for-all-within-timeout without leaking listeners or double-settling?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the repo's canonical abort/settle micro-kernel that every provider, proxy, and registry call funnels through?

## Single-flight settlement with guaranteed listener teardown
**Path/Symbol:** `src/async-settlement.ts` — `throwIfAborted` (:7-9), `raceWithAbort` (:11-33), `runAbortable` (:35-45), `settleWithin` (:47-65).
**Signature:** `runAbortable<T>(signal: AbortSignal | undefined, operation: () => T | PromiseLike<T>): Promise<T>`; `settleWithin(operations: Iterable<PromiseLike<unknown>>, timeoutMs: number): Promise<boolean>` (true = all settled in time).
**Data Shape:** no shared state — each call owns its `settled` latch and one `{once: true}` abort listener removed on ANY settlement path.

### Decisive source
```ts
return new Promise<T>((resolve, reject) => {
  let settled = false;
  const finish = (callback: () => void): void => {
    if (settled) return;                       // first settlement wins
    settled = true;
    signal.removeEventListener("abort", onAbort);   // never leak the listener
    callback();
  };
  const onAbort = (): void => finish(() => reject(abortError(signal)));
  signal.addEventListener("abort", onAbort, { once: true });
  Promise.resolve(operation).then(
    (value) => finish(() => resolve(value)),
    (error) => finish(() => reject(error)));
});
// settleWithin: allSettled raced against a timer; timer ALWAYS cleared:
return await Promise.race([
  Promise.allSettled(pending).then(() => true),
  new Promise<false>((resolve) => { timer = setTimeout(() => resolve(false), Math.max(0, timeoutMs)); }),
]);
```

**Flow:** `runAbortable` checks pre-aborted synchronously (throws the signal's reason as an Error), then races the operation against abort; the settled latch guarantees exactly one outcome and removes the listener whether the operation won, lost, or threw. `settleWithin` answers "did every promise finish within the budget" for grace-window teardown paths (guest kernel shutdown, scheduler barriers).
**Invariant:** the abort reason is preserved verbatim when it is an Error (never re-wrapped); listener count is invariant across outcomes; `settleWithin` resolves (never rejects) and always clears its timer. The underlying OPERATION is not cancelled — this is cooperative racing around already-started work.
**Probe:** exercised indirectly through every consumer — e.g. `tests/tool-result-proxy.test.ts:43+` (abortable emitToolResult), `tests/quickjs-runtime.test.ts` (grace-window teardown uses settleWithin), `tests/state-provider.test.ts:244` ("fails closed on spawn errors, timeouts, and cancellation"). No dedicated direct-test file exists for async-settlement.ts — coverage caveat noted.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "runAbortable settleWithin raceWithAbort throwIfAborted abort listener settled", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 40-line micro-kernel wholesale (it is host-independent); adapt nothing but names; omit Node-specific timer unref decisions if your runtime differs.
