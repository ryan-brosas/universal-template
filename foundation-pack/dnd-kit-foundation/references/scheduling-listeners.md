<!-- capsule-v2 -->
# Scheduling & listeners — rAF-coalesced task scheduler and the Listeners registry

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How do high-frequency drag writes stay frame-aligned, and how does listener teardown stay leak-proof across sensors?

## Scheduler / throttle / Listeners
**Path/Symbol:** `packages/dom/src/utilities/scheduling/scheduler.ts:3-45`, `scheduling/throttle.ts` (consumed by PositionObserver), `utilities/event-listeners/Listeners.ts`.
**Signature:** `scheduler.schedule(task): Promise<void>` — tasks dedupe into a Set, ONE rAF flush executes them in insertion order then resolves all waiters; `pending` latch prevents double-scheduling; module exports a singleton bound to `requestAnimationFrame` with a synchronous fallback when absent.
**Data Shape:** `tasks: Set<fn>` + `resolvers: Set<() => void>` snapshot-swapped at flush start (re-entrant schedules land in the NEXT frame).

### Decisive source
```ts
export class Scheduler<T extends (callback: Callback) => any> {
  private pending = false;
  private tasks: Set<() => void> = new Set();
  private resolvers: Set<() => void> = new Set();

  public schedule(task: () => void): Promise<void> {
    this.tasks.add(task);                    // Set dedupes identical fn refs
    if (!this.pending) {
      this.pending = true;
      this.scheduler(this.flush);            // one rAF per burst
    }
    return new Promise<void>((resolve) => this.resolvers.add(resolve));
  }

  public flush = () => {
    const {tasks, resolvers} = this;
    this.pending = false;
    this.tasks = new Set();      // swap FIRST so tasks can schedule follow-ups
    this.resolvers = new Set();
    for (const task of tasks) task();
    for (const resolve of resolvers) resolve();
  };
}
```

**Flow:** PointerSensor's move path stores `latest {event, coordinates}` and schedules `handleMove` (dedupe by reference = at most one apply per frame); AutoScroller wraps its interval tick; the a11y plugin batches attribute mutations; Scroller serializes scroll writes. The swap-then-run ordering means a task that schedules another task correctly targets the next frame instead of recursing. `Listeners.bind(targets, [{type, listener, options}])` returns one composite cleanup; sensors accumulate these in cleanup sets destroyed on stop/destroy — no ad-hoc removeEventListener pairs to forget.
**Invariant:** identical function references scheduled N times run ONCE per frame (idempotent apply pattern is required, which is why sensors keep `latest` state rather than closing over events); flush order preserves insertion (attribute mutations must not reorder relative to each other); every bind has exactly one owning cleanup.
**Probe:** scheduler exercised transitively by every upstream suite (139 tests GREEN through it); no dedicated unit file (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "Scheduler throttle", name_pattern: "^Scheduler$", limit: 10 });
```

## Verdict
Adopt the dedupe-by-reference frame scheduler verbatim (~45 lines); adapt rAF to your renderer's tick; omit the promise-returning surface if no caller awaits flush completion.
