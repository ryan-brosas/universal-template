<!-- capsule-v2 -->
# Effect root scheduling — how is an effect scheduled exactly once per flush, at its root?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** When many leaf effects go dirty at once, why does the scheduler enqueue one root instead of N effects — and what stops double-flushing during traversal?

## Climb-to-root schedule
**Path/Symbol:** `packages/svelte/src/internal/client/reactivity/batch.js:Batch.schedule` (:928-979) + `#traverse` (:435-478); module `schedule_effect` (:1239-1241).
**Signature:** `schedule(effect: Effect): void`; private `#traverse(root, effects, render_effects)`.
**Data Shape:** Effect tree = doubly-linked lists (`first/last/next/prev/parent`); branch/root effects carry `BRANCH_EFFECT|ROOT_EFFECT` flags and CLEAN bit; `collected_effects` is a module-level array active only during traversal.

### Decisive source
```js
var e = effect;

while (e.parent !== null) {
	e = e.parent;
	var flags = e.f;

	if (collected_effects !== null && e === active_effect) {
		if (async_mode_flag) return;
		...
	}

	if ((flags & (ROOT_EFFECT | BRANCH_EFFECT)) !== 0) {
		if ((flags & CLEAN) === 0) {
			// branch is already dirty, bail
			return;
		}

		e.f ^= CLEAN;
	}
}

this.#roots.push(e);
```
and traversal:
```js
if (!skip && effect.fn !== null) {
	if (is_branch) {
		effect.f ^= CLEAN;
	} else if ((flags & EFFECT) !== 0) {
		effects.push(effect);
	} else if (async_mode_flag && (flags & (RENDER_EFFECT | MANAGED_EFFECT)) !== 0) {
		render_effects.push(effect);
	} else if (is_dirty(effect)) {
		if ((flags & BLOCK_EFFECT) !== 0) this.#maybe_dirty_effects.add(effect);
		update_effect(effect);
	}
	...
}
```

**Flow:** `mark_reactions` calls `schedule_effect(effect)` → `Batch.schedule`: climb parents, toggling each branch/root's CLEAN bit OFF via XOR. If any ancestor branch is already non-CLEAN its root is already queued — bail, no duplicate root. Roots accumulate in `#roots`; `#traverse` resets each root's clean bit (`root.f ^= CLEAN`) and walks the linked list iteratively (descend into `first`, else walk `next`, else pop to `parent`), executing block/render effects inline behind an `is_dirty` check while *deferring* plain user EFFECTs into ordered arrays flushed after traversal. Effects created *during* traversal go to `collected_effects` instead of the scheduling rigmarole, avoiding a second flush turn.
**Invariant:** One scheduled effect ⇒ at most one root pushed, regardless of how many of its dependencies changed; traversal visits each tree node exactly once because CLEAN bits gate re-entry; render/pre effects are partitioned ahead of user `$effect`s so pre-DOM work precedes DOM work.
**Probe:** `packages/svelte/tests/runtime-runes/samples/flush-sync-inside-attachment/_config.js` plus samples `new-branch-reschedule`/`async-reschedule-during-flush` (scheduling that occurs mid-traversal must not cause a second flush turn).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "schedule effect roots traverse branch clean", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt climb-to-root scheduling with a dirty-ancestor bail and XOR'd cleanliness bits — it is what makes write fan-out O(reactions) rather than O(effects × deps). Adapt the render/user partitioning to your host's phase model; omit pending-boundary deferral (`effect.b.defer_effect`) until porting async boundaries.
