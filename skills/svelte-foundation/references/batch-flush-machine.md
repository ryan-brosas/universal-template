<!-- capsule-v2 -->
# Batch flush machine — when do effects actually run relative to writes, and what bounds runaway loops?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** How does the runtime guarantee all writes in one tick coalesce into one effect pass, while writes made *by* effects still converge — and how does an infinite `$effect` loop die loudly?

## The Batch state machine
**Path/Symbol:** `packages/svelte/src/internal/client/reactivity/batch.js:Batch.ensure` (:859-873), `flush` (:610-638), `#process` (:276-426); `flushSync` (:1013-1040); `infinite_loop_guard` (:1042-1079).
**Signature:** `static ensure(): Batch`; `flush(): void`; private `#process(): void`; `export function flushSync(fn?): T`.
**Data Shape:** Module-level `current_batch`, doubly-linked batch list (`first_batch/last_batch/#prev/#next`), per-batch `#roots: Effect[]`, `#dirty_effects/#maybe_dirty_effects` sets, `flush_count` guard.

### Decisive source
```js
// #process, after traversing roots:
// any writes should take effect in a subsequent batch
current_batch = null;
...
previous_batch = this;
flush_queued_effects(render_effects);
flush_queued_effects(effects);
previous_batch = null;

this.#deferred?.resolve();
...
if (next_batch !== null) {
	old_values.clear();
	next_batch.#process();
}
```
and the guard:
```js
if (flush_count++ > 1000) {
	this.#unlink();
	infinite_loop_guard();
}
```

**Flow:** `Batch.ensure()` creates a batch on first write and queues a microtask that calls `flush()` (skipped while already processing or inside flushSync). `#process()` increments the loop counter (throwing `effect_update_depth_exceeded` past 1000, routed to the nearest boundary via `last_scheduled_effect`), reschedules deferred dirty sets, applies time-travel values, traverses each root collecting `render_effects[]`/`effects[]`, then **nulls `current_batch` before running queued effects** so any write performed by an effect opens a *fresh* batch instead of mutating the one being drained. Pre-effects (`$effect.pre`/render effects) run before user effects; commit callbacks fire between traversal and flushing. When done, if another batch exists it is chained via `next_batch.#process()`. `flushSync(fn)` first drains any current batch, runs `fn`, then loops `flush_tasks(); current_batch.flush()` until no batch remains.
**Invariant:** Effects scheduled during one flush never run inside the same batch's queue twice without their writes being visible: writes-during-effects land in a new batch which is processed only after this one commits. `old_values` is cleared at batch boundaries, not mid-flush. The 1000-flush budget is global per synchronous drain (`flush_count` reset in `flush`'s finally), not per batch.
**Probe:** `packages/svelte/tests/runtime-runes/samples/flush-sync-no-scheduled/_config.js` (a plain click with no flushSync converges via microtask — calling flushSync with nothing scheduled must not break reactivity); harness `tests/runtime-legacy/shared.ts` imports `clear` from `batch.js` purely to isolate batches between tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "Batch process flush infinite loop guard", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase shape: collect → null-the-current-context → run, plus chaining of subsequent batches, and a hard flush-count guard routed through error boundaries. Adapt the microtask transport (`queue_micro_task`/`flush_tasks`) to your host; omit legacy-mode `legacy_updates` re-queueing and DEV source-stack bookkeeping unless needed.
