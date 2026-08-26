<!-- capsule-v2 -->
# Barrier primitive — what is the reusable rendezvous that keeps concurrent param resolution deadlock-free?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What contract makes this 55-line primitive safe to lift into any concurrent resolver?

## Barrier
**Path/Symbol:** `packages/core/helpers/barrier.ts:Barrier` (1-55).
**Signature:** `constructor(targetCount: number)`; `signal(): void`; `wait(): Promise<void>`; `signalAndWait(): Promise<void>`.
**Data Shape:** internal `currentCount`/`targetCount` and a single resolve function captured from a never-rejecting promise.

### Decisive source
```ts
constructor(targetCount: number) {
  this.currentCount = 0;
  this.targetCount = targetCount;
  this.promise = new Promise<void>(resolve => { this.resolve = resolve; });
  if (targetCount === 0) {
    this.resolve();               // empty party resolves IMMEDIATELY — no await hang
  }
}
public signal(): void {
  this.currentCount += 1;
  if (this.currentCount >= targetCount) this.resolve();
}
```

**Flow:** create with party size → each participant calls signal (or signalAndWait) → promise resolves once count ≥ target.
**Invariant:** The promise NEVER rejects; error paths must still call `signal()` unconditionally or the other participants' `signalAndWait()` awaits hang forever (Injector's catch blocks do exactly this). Zero-count construction self-resolves. Over-signaling is harmless (`>=`). Single-shot: no reset/reuse.
**Probe:** `packages/core/test/helpers/barrier.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "Barrier signalAndWait signal wait", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as-is for any fan-out where every participant must reach a checkpoint before a shared evaluation; adapt to resettable semantics only if you need reuse; omit nothing. Porting wrong: forgetting the zero-count fast path hangs empty dependency lists; skipping signal in error paths deadlocks siblings.
