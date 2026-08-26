<!-- capsule-v2 -->
# Scheduler min-heap id tie-break — how do equal-priority tasks stay FIFO through a numeric binary heap?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** When two tasks get identical sortIndex (same priority scheduled at the same clock reading), what order must a port preserve, and how is cancellation represented in the heap?

## Array-based min-heap with two-key compare
**Path/Symbol:** `packages/scheduler/src/SchedulerMinHeap.js:compare` (:91–95), `pop` (:27–40); consumers `packages/scheduler/src/forks/Scheduler.js:push/pop/peek` imports (:24).
**Signature:** `function compare(a: Node, b: Node): number` over `Node = {id: number, sortIndex: number}`.
**Data Shape:** Heap is a plain `Array<T>`; nodes carry an incrementing `id` (`taskIdCounter`, Scheduler.js :83) and a numeric `sortIndex`. `peek` returns `null` on empty; `pop` returns the removed root or `null`.

### Decisive source
```js
function compare(a: Node, b: Node) {
  // Compare sort index first, then task id.
  const diff = a.sortIndex - b.sortIndex;
  return diff !== 0 ? diff : a.id - b.id;
}
```
And in `pop` — the last-element swap must not re-sift when the popped root was also the last element:
```js
const first = heap[0];
const last = heap.pop();
if (last !== first) {
  heap[0] = last;
  siftDown(heap, last, 0);
}
return first;
```

**Flow:** schedule assigns `id = taskIdCounter++` → push sifts up while parent compares > 0 → pop swaps last into root and sifts down → equal `sortIndex` falls through to the `id` comparison, so insertion order wins.
**Invariant:** For any two tasks whose sortIndex is written at the same instant (same expiration), execution order is strictly FIFO by scheduling call order. A port that drops the id tie-break (or uses a random/heap-internal counter for it) silently reorders same-priority work.

**Probe:** `packages/scheduler/src/__tests__/Scheduler-test.js` `'multiple tasks'` (:215–231) schedules A then B at NormalPriority and asserts log order `['Message Event', 'A', 'B']` — both share one expiration timestamp, so only the id tie-break yields A before B.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "SchedulerMinHeap compare sortIndex task id", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the two-key compare and the `last !== first` guard verbatim — they are pure data-structure contracts. Adapt the node shape to your language (keep both fields). Omit Flow types. Coverage caveat: `SchedulerMinHeap.js` is parse_partial at pin (ranges 10-11…89 recorded); every cited line above was read directly from source, which is authoritative.
