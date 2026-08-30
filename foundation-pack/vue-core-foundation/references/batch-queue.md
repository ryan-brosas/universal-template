<!-- capsule-v2 -->
# Batch queue + trigger() — how are same-tick notifications coalesced, ordered, and drained exactly once?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** How does the kernel guarantee an effect runs once per synchronous mutation storm, in subscription order, even when triggers nest?

## LIFO batched lists drained at depth 0
**Path/Symbol:** `packages/reactivity/src/effect.ts:batch` (:251-260), `startBatch` (:265-267), `endBatch` (:273-310), `ReactiveEffect.notify` (:150-160); `packages/reactivity/src/dep.ts:Dep.notify` (:173-204), `trigger` fn (:294-389).
**Signature:** `batch(sub: Subscriber, isComputed = false): void`, `startBatch(): void`, `endBatch(): void`.
**Data Shape:** Module-local `batchDepth` counter plus two intrusive singly-linked stacks built through `sub.next`: `batchedSub` (effects) and `batchedComputed` (computeds). Membership flag is `EffectFlags.NOTIFIED`.

### Decisive source
```ts
// endBatch: computeds are only un-flagged; effects re-enter via trigger()
if (batchedComputed) {
  let e = batchedComputed; batchedComputed = undefined
  while (e) { const next = e.next; e.next = undefined; e.flags &= ~EffectFlags.NOTIFIED; e = next }
}
let error: unknown
while (batchedSub) {
  let e = batchedSub; batchedSub = undefined
  while (e) { const next = e.next; e.next = undefined; e.flags &= ~EffectFlags.NOTIFIED
    if (e.flags & EffectFlags.ACTIVE) { try { ;(e as ReactiveEffect).trigger() } catch (err) { if (!error) error = err } }
    e = next }
}
if (error) throw error
```

**Flow:** `Dep.trigger` bumps versions then `notify()` wraps fan-out in start/endBatch → each sub's `notify()` sets NOTIFIED and pushes onto a batch list only if not already NOTIFIED → outermost `endBatch` first clears computed flags, then drains effect stack (LIFO push ⇒ original subscription order out), routing each ACTIVE effect through `trigger()` (scheduler or runIfDirty) — so effects queued mid-drain land on a fresh stack and drain in the same tick.
**Invariant:** The NOTIFIED flag is the dedupe latch — pushing without checking it double-runs effects per flush; draining must clear `next` before invoking user code (a subscriber that mutates state re-enters notify and would otherwise corrupt the list being walked). First error is swallowed until all drained, then thrown (no lost failures).
**Probe:** `packages/reactivity/__tests__/watch.spec.ts:305` (`should ensure correct execution order in batch processing` — watcher writes n2 which wakes computed `sum`; output order pinned `[1, 2, 3]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "endBatch startBatch batchDepth", limit: 10 });
```

## Verdict
Adopt the depth-counted batch + two-lists + NOTIFIED-latch design as-is. Adapt `trigger()`'s PAUSED branch (`pausedQueueEffects` WeakSet re-queue on resume) to your scheduler's pause story. Omit the DEV-only subsHead/onTrigger ordering pass inside `Dep.notify`.
