<!-- capsule-v2 -->
# Keyed each reconciliation — how does a keyed list reorder, insert, and remove items with minimal DOM moves?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** When a keyed collection changes, how are existing item effects matched to new positions, what decides move-vs-destroy-vs-resume, and how do concurrent batches and transitions keep the block consistent?

## each = branch block + items Map + single-pass reconcile
**Path/Symbol:** `packages/svelte/src/internal/client/dom/blocks/each.js:each` (:181-408), `reconcile` (:432-658), `pause_effects` (:66-132), `destroy_effects` (:139-166), `create_item` (:672-702), `move` (:709-730) / `link` (:737-749).
**Signature:** `each(node, flags, get_collection, get_key, render_fn, fallback_fn?)`; flags = EACH_IS_CONTROLLED | EACH_IS_ANIMATED | EACH_ITEM_REACTIVE | EACH_ITEM_IMMUTABLE | EACH_INDEX_REACTIVE.
**Data Shape:** `EachState = { effect (BRANCH_EFFECT), flags, items: Map<key, {v, i, e}>, pending: Map<Batch, Set<key>>, outrogroups, fallback }`; per-item `v`/`i` are sources only when the reactive flags are set (`mutable_source` unless IMMUTABLE); item effect `e` is a `branch()` whose teardown deletes the key from `items`.

### Decisive source
```js
// block body, per existing item — BEFORE reconciliation:
if (item) {
	// update before reconciliation, to trigger any async updates
	if (item.v) internal_set(item.v, value);
	if (item.i) internal_set(item.i, index);
	...
} else {
	item = create_item(items, first_run ? anchor : (offscreen_anchor ??= create_text()), ...);
	if (!first_run) item.e.f |= EFFECT_OFFSCREEN;
	items.set(key, item);
}
...
if (!first_run) {
	pending.set(batch, keys);
	if (defer) {
		for (const [key, item] of items) if (!keys.has(key)) batch.skip_effect(item.e);
		batch.oncommit(commit);
		batch.ondiscard(discard);
	} else {
		commit(batch);
	}
}
```
and reconcile's move-minimization heuristic:
```js
if (seen !== undefined && seen.has(effect)) {
	if (matched.length < stashed.length) {
		// more efficient to move later items to the front
		...
	} else {
		// more efficient to move earlier items to the back
		seen.delete(effect);
		move(effect, current, anchor);
		link(state, effect.prev, effect.next);
		link(state, effect, prev === null ? state.effect.first : prev.next);
		link(state, prev, effect);
		prev = effect;
	}
	continue;
}
```

**Flow:** The collection is read through a `derived_safe_equal` (array identity + safe equality; stores can't use strict derived because mutation keeps the array identical). On change the branch body re-runs: existing items' value/index sources are written via `internal_set` **before** reconciliation so async updates triggered by the new value start immediately; new items render offscreen (EFFECT_OFFSCREEN flag, offscreen anchor text node). The key set is parked in `pending` under the current batch; when appends must be deferred (controlled blocks), removed items' effects are skipped and reconciliation defers to `batch.oncommit`. `reconcile` walks the NEW array once against the linked-list of child branch effects: INERT items (paused by an earlier removal whose transition may have finished or been cancelled) resume; OFFSCREEN items relink into place and move; out-of-order items trigger the matched/stashed/seen bookkeeping that chooses whichever direction needs fewer moves; leftovers (in `seen` or after the walk) go to `pause_effects` — which pauses each with an outro callback, groups them in `outrogroups` while transitions run, and only destroys when a group's pending set empties. Items still referenced by OTHER pending batches are not destroyed but moved offscreen (EFFECT_OFFSCREEN + DocumentFragment) so those batches' keys stay valid (#18610). The controlled-each fast path (no transitions, removing everything, no other batch pending) empties the parent element and re-appends the anchor instead of walking nodes. Duplicate keys throw (DEV computes details via `validate_each_keys`; prod uses the cheap `length > keys.size` check).
**Invariant:** Value/index sources must be updated before reconciliation or async effects see stale values for a tick. An item referenced by any other pending batch must never be destroyed, only moved offscreen. Reconciliation must be a single forward pass over the new array (the matched/stashed state machine depends on it), and every link() must fix both sibling pointers and the branch's first/last.
**Probe:** `packages/svelte/tests/runtime-runes/samples/each-updates/_config.js` (keyed add/change/reload cycles assert exact DOM order); `samples/each-keyed-child-effect/main.svelte` + `_config.js` (reverse() reorders items with nested `{#if}` children intact); `samples/async-each-keyed/main.svelte` (keyed each over an awaited promise across resets).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "each reconcile pause_effects EFFECT_OFFSCREEN outrogroups", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the items-Map + single-pass reconcile with the min-move heuristic, update-before-reconcile source writes, offscreen-preserve for cross-batch references, and outro-grouped destruction — this is the whole keyed-list contract. Adapt the DOM move/link primitives to your host's node model; omit hydration mismatch handling and the animated (FLIP measure/fix/apply) paths unless porting those planes. Caveat: MCP graph retrieval not executable in this session (daemon not connected); evidence is direct source/test reading at the pinned checkout (see work record verification.md).
