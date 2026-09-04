<!-- capsule-v2 -->
# Derived versioned pull — how are deriveds lazily recomputed with O(deps) staleness checks?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** How can a derived be marked dirty cheaply on write, yet never recompute until actually read — and how does the runtime decide "still fresh" without running the fn?

## rv/wv version counters
**Path/Symbol:** `packages/svelte/src/internal/client/runtime.js:is_dirty` (:156-194) and `get` (:540-710); `packages/svelte/src/internal/client/reactivity/deriveds.js:update_derived` (:393-442).
**Signature:** `is_dirty(reaction): boolean`; `get(signal): V`; `update_derived(derived): void`.
**Data Shape:** Every Value carries `rv` (read-version stamp, per-reaction global `read_version` bumped each `update_reaction`) and `wv` (write-version stamp, global `write_version` incremented per accepted write).

### Decisive source
```js
// is_dirty, MAYBE_DIRTY branch:
for (var i = 0; i < length; i++) {
	var dependency = dependencies[i];

	if (is_dirty(dependency)) {
		update_derived(dependency);
	}

	if (dependency.wv > reaction.wv) {
		return true;
	}
}
```
and in update_derived:
```js
if (!derived.equals(value)) {
	derived.wv = increment_write_version();
	...
}
...
// deriveds without dependencies should never be recomputed
if (derived.deps === null) {
	set_signal_status(derived, CLEAN);
	return;
}
```

**Flow:** Writes bump only a counter; deriveds stay MAYBE_DIRTY. On read (`get`), if `is_dirty(derived)`: for MAYBE_DIRTY, recursively settle derived deps and compare each dep's write version against the reader's last-seen version — no fn execution needed to prove freshness. Only when some `dep.wv > reaction.wv` does `update_derived` → `execute_derived` → `update_reaction` actually rerun; the new value gets its own `wv`, is captured into current **and** previous batches during flush (both, or `#commit` rebasing sees stale derived state), and time-travel caches it in `batch_values` when tracking. Reads also dedupe deps via the `skipped_deps` fast path: if deps arrive in the same order as last run, the array is reused without allocation. Dep-less deriveds compute once and cache forever. During teardown reads, values come from `old_values` instead of current state.
**Invariant:** A derived's stored result must always be accompanied by the write-version at which it was computed; skipping recomputation requires proving every dep's `wv <= reaction.wv`. Never mark a derived CLEAN while `batch_values !== null` (other batches still traverse), and never mark clean inside a destroying effect (would cache a stale value).
**Probe:** `tests/runtime-legacy/shared.ts` `runtime_suite(true)` mounts samples with an initial flushSync; sample suites under `packages/svelte/tests/runtime-runes/samples/` exercise derived chains through assert-logs fixtures (e.g. `side-effect-derived-*` family pins that derived fns run exactly when read).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "is_dirty update_derived write version skipped_deps", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-counter staleness proofs (read-stamp + write-stamp) over eager invalidation graphs — this is the core of Svelte 5's fine-grained performance. Adapt the equals hook placement (post-compare decides whether dependents get marked); omit async-derived suspension and DEV self-reference stacks for a minimal port.
