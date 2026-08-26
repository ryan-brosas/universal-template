<!-- capsule-v2 -->
# DelayedPromise + isDeepEqualData — which two micro-contracts keep lazy result objects rejection-safe and partial streams dedup-quiet?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** How does the SDK expose seven awaitable properties on a lazily-started stream result without unhandled-rejection storms, and how does it decide two JSON values are "the same" for streaming dedup?

## DelayedPromise — status-first, promise-on-demand
**Path/Symbol:** `packages/provider-utils/src/delayed-promise.ts:DelayedPromise` (whole file, ~60L).
**Signature:** `class DelayedPromise<T> { get promise(): Promise<T>; resolve(value): void; reject(error): void; isResolved()/isRejected()/isPending(): boolean }`.
**Data Shape:** Internal `status` is set IMMEDIATELY on resolve/reject; the native Promise (and executors) is created only when `.promise` is first READ. On creation it replays a stored terminal status synchronously.

### Decisive source
```ts
get promise(): Promise<T> {
  if (this._promise) return this._promise;
  this._promise = new Promise<T>((resolve, reject) => {
    if (this.status.type === 'resolved') resolve(this.status.value);   // replay!
    else if (this.status.type === 'rejected') reject(this.status.error);
    this._resolve = resolve;   // future settles go through these
    this._reject = reject;
  });
  return this._promise;
}
resolve(value: T): void {
  this.status = { type: 'resolved', value };
  if (this._promise) this._resolve?.(value);   // only if someone is watching
}
```

**Flow:** stream-object holds SEVEN DelayedPromises (`_object`, `_usage`, `_providerMetadata`, `_warnings`, `_request`, `_response`, `_finishReason` — stream-object.ts :442–454). The producer resolves/rejects them as chunks arrive regardless of consumer interest; consumers `await result.object` whenever they like.
**Invariant:** A rejected result NOBODY awaits must not crash the process — the promise object doesn't exist until first read, so there's no eager rejection to go unhandled ("should not lead to unhandled promise rejections", stream-object.test.ts :564 pins exactly this with a schema-mismatched object). Late readers still get the stored outcome via replay. Porters who replace this with plain eagerly-created Promises per property reintroduce the crash this test guards against.

**Probe:** `packages/provider-utils/src/delayed-promise.test.ts` — dedicated direct suite (CORRECTION 2026-08-23, pass 6: an earlier revision of this capsule claimed no dedicated unit suite exists; it does, with fake-timer blocking assertions): :10/:18 ("resolve/reject when accessed after resolution/rejection" — the replay path), :26/:34 (access BEFORE settlement), :43/:56 (multiple accesses stable), :75/:96 (pending promises fan out on later resolve). Consumer-side crash guard additionally pinned by stream-object.test.ts :533/:564.

## isDeepEqualData — JSON-value equality with constructor guard
**Path/Symbol:** `packages/ai/src/util/is-deep-equal-data.ts:isDeepEqualData` (:8–48).
**Signature:** `function isDeepEqualData(obj1: any, obj2: any): boolean`.
**Data Shape:** Strict-equality fast path → null/undefined check (loose `==`, catches both) → constructor mismatch = false → Date special-case (getTime) → arrays length+indexwise → objects key-set equality then recursive values.

### Decisive source
```ts
if (obj1 === obj2) return true;
if (obj1 == null || obj2 == null) return false;           // loose ==: null AND undefined
if (obj1.constructor !== obj2.constructor) return false;  // Object vs Array vs Date never equal
if (obj1 instanceof Date && obj2 instanceof Date)
  return obj1.getTime() === obj2.getTime();
if (Array.isArray(obj1)) { /* length + elementwise recursion */ }
const keys1 = Object.keys(obj1), keys2 = Object.keys(obj2);
if (keys1.length !== keys2.length) return false;
```

**Flow:** serves as BOTH dedup gates in the legacy streamObject core loop (raw parsed value AND validated partial — cross-ref stream-object-pipeline.md) and general change detection across packages/ai utils.
**Invariant:** Key ORDER is irrelevant but key SET is not. The constructor guard makes an array↔object transition count as a CHANGE mid-stream even if contents coincide — a porter swapping in lodash.isEqual or structural-clone comparison would subtly change emission cadence.
**Probe:** `packages/ai/src/util/is-deep-equal-data.test.ts` (suite colocated); end-to-end cadence pinned by stream-object.test.ts :1048 partial-stream assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "DelayedPromise isDeepEqualData deep equal", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt both contracts verbatim (dependency-free, host-neutral); adapt naming/placement to host util conventions; omit the Date branch if your pipeline never carries Dates inside streamed JSON values. Coverage caveat: DelayedPromise has no dedicated upstream unit suite (contract pinned transitively); index best-effort; excerpts read at HEAD.
