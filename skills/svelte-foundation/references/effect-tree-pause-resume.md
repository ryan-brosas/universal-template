<!-- capsule-v2 -->
# Effect tree pause/resume — how does the runtime keep the effect tree as a linked list and swap branches safely?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** How are effects parented, pruned, and how can an `{#if}` branch disappear and come back (transitions!) without losing its subtree?

## Linked-list effect nodes
**Path/Symbol:** `packages/svelte/src/internal/client/reactivity/effects.js:create_effect` (:88-181), `destroy_effect` (:518-570), `unlink_effect` (:592-604), `pause_effect/pause_children` (:616-680), `resume_effect/resume_children` (:687-734).
**Signature:** `create_effect(type, fn): Effect`; `branch(fn)` = `create_effect(BRANCH_EFFECT | EFFECT_PRESERVED, fn)`; `pause_effect(effect, callback, destroy = true)`.
**Data Shape:** Effect = `{ f, first, last, next, prev, parent, deps, nodes, teardown, ac, b, ctx }` — a child-ordered doubly-linked list under each parent; flags include INERT, PAUSED, DESTROYING/DESTROYED, EFFECT_TRANSPARENT.

### Decisive source
```js
// create_effect: run render-type effects inline, then prune no-ops
if (
	e.deps === null &&
	e.teardown === null &&
	e.nodes === null &&
	e.first === e.last && // either `null`, or a singular child
	(e.f & EFFECT_PRESERVED) === 0
) {
	e = e.first;
	...
}
```
and resume_children:
```js
// If a dependency of this effect changed while it was paused,
// schedule the effect to update. we don't use `is_dirty`
// here because we don't want to eagerly recompute a derived like
// `{#if foo}{foo.bar()}{/if}` if `foo` is now `undefined
if ((effect.f & CLEAN) === 0) {
	set_signal_status(effect, DIRTY);
	Batch.ensure().schedule(effect);
}
```

**Flow:** Effects attach to `active_effect` via `push_effect` (tail insert) and inherit INERT from an inert parent at creation; render-type effects execute inline at creation while user `$effect`s defer to the batch scheduler. Effects that will never re-run (no deps/teardown/DOM/single child) are spliced out of the tree *at creation* and again in `flush_queued_effects`. Branch teardown is two-phase: `pause_effect` marks PAUSED, flips the subtree INERT, collects outro transitions and only destroys once all transitions complete (`--remaining || fn()`); if state flips back, `resume_effect` clears INERT bottom-up, re-marks any non-CLEAN effect DIRTY and schedules it — deliberately *not* calling `is_dirty`, which would eagerly evaluate deriveds of not-yet-visible branches. `destroy_effect` aborts AbortControllers (`STALE_REACTION`), removes reactions, runs teardown through error-boundary routing, unlinks, then nulls every field **except parent** so errors can still propagate upward.
**Invariant:** ROOT_EFFECT children become independent roots on parent destruction instead of dying with it; a paused subtree must stay inert to writes but keep its dependency links intact for resume; unlink must fix both `parent.first/last` and sibling pointers.
**Probe:** `packages/svelte/tests/runtime-runes/samples/effect-self-scheduling/main.svelte` pins that a re-scheduled effect settles; transition-aware pause/resume is exercised by runtime-runes samples with `{#if}` toggles under `runtime_suite`'s raf tick.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "pause_effect resume_children inert destroy_effect unlink", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt linked-list parenting with creation-time pruning, two-phase pause (INERT + outro gate) and dirty-on-resume scheduling without eager dirtiness evaluation. Adapt transition-manager integration to your host's animation system; omit Svelte's `nodes.t` TransitionManager plumbing specifics.
