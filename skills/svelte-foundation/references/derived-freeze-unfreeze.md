<!-- capsule-v2 -->
# Derived freeze/unfreeze — how do effects created inside a derived survive the derived losing all its readers?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** When a derived's last reaction goes away, its inner effects (e.g. `$state.eager` inside a computed) must stop running — but how does the runtime later know which effects to restart when a reader comes back?

## derived.effects + freeze on disconnect, unfreeze on reconnect
**Path/Symbol:** `packages/svelte/src/internal/client/reactivity/effects.js:create_effect` (:169-177 registration); `packages/svelte/src/internal/client/runtime.js:remove_reaction` (:367-427 disconnect), `get` (:680-699 unfreeze site), `reconnect` (:717-730); `packages/svelte/src/internal/client/reactivity/deriveds.js:freeze_derived_effects` (:447-471), `unfreeze_derived_effects` (:476-486).
**Signature:** `freeze_derived_effects(derived): void`; `unfreeze_derived_effects(derived): void`.
**Data Shape:** `Derived.effects: null | Effect[]` — "Effects created inside this signal. Used to destroy those effects when the derived reruns or is cleaned up" (types.d.ts:58-59). The freeze marker is `e.teardown = noop` (presence of a teardown function, not null-ness).

### Decisive source
```js
// freeze_derived_effects
if (e.teardown || e.ac) {
	e.teardown?.();
	if (e.ac !== null) {
		without_reactive_context(() => {
			/** @type {AbortController} */ (e.ac).abort(STALE_REACTION);
			e.ac = null;
		});
	}
	// make it a noop so it doesn't get called again if the derived
	// is unfrozen. we don't set it to `null`, because the existence
	// of a teardown function is what determines whether the
	// effect runs again during unfreezing (but not for teardown-only effects)
	if (e.fn !== null) e.teardown = noop;
	remove_reactions(e, 0);
	destroy_effect_children(e);
}
```
```js
// unfreeze_derived_effects
for (const e of derived.effects) {
	// if the effect was previously frozen — indicated by the presence
	// of a teardown function — unfreeze it
	if (e.teardown && e.fn !== null) {
		update_effect(e);
	}
}
```

**Flow:** Any non-root effect created while `active_reaction` is a DERIVED is pushed into `derived.effects` at creation. When `remove_reaction` drops a dependency's reaction list to null (and the dep isn't in the currently-updating parent's new_deps), the derived disconnects: it clears CONNECTED/WAS_MARKED, keeps itself DIRTY if it never produced a value, aborts its own AbortController with STALE_REACTION (so a re-read reruns instead of returning a stale rejected promise), then `freeze_derived_effects` — for each inner effect with a teardown or AC: run teardown, abort the AC outside reactive context, replace teardown with `noop` (the marker), remove its reactions, destroy its children. On the next read, `get` sees `should_connect && !is_new` (REACTION_RAN was set) and calls `unfreeze_derived_effects(derived)` + `reconnect(derived)`; unfreeze re-runs exactly the effects that were frozen (`teardown && fn !== null` — teardown-only effects like `teardown(fn)` helpers are excluded), and `reconnect` recursively walks disconnected derived deps, unfreezing theirs too, before re-pushing the derived onto each dep's reactions list.
**Invariant:** The freeze marker must be `noop`, never `null` — nulling it makes unfreeze unable to distinguish "was frozen" from "never had a teardown", and inner effects either double-run or never resume. A frozen subtree must be fully detached from the graph (reactions removed, children destroyed) or writes keep scheduling dead work. Reconnection must recurse through derived deps or nested eager effects stay frozen forever.
**Probe:** `packages/svelte/tests/runtime-runes/samples/async-state-eager-const/_config.js` — dev-mode test whose comment pins this exact seam: "testing that teardown effect in eager $.get(loaded) doesn't lead to a crash (because it means REACTION_RAN is set, which means unfreeze_derived runs)"; `samples/async-eager-derived/main.svelte` + `_config.js` pins `$state.eager` values tracking across an async derived's disconnect/reconnect cycle.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "freeze_derived_effects unfreeze_derived_effects reconnect derived effects", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the effects-on-derived registry plus the noop-teardown freeze marker and recursive reconnect — this is what lets computed values own side-effectful children (eager state, inspect) without leaking them past their last reader. Adapt the marker to your host's effect lifecycle (any idempotent "was torn down once" flag works); omit the STALE_REACTION abort interplay only if your async deriveds cannot reject. Caveat: MCP graph retrieval not executable in this session (daemon not connected); evidence is direct source/test reading at the pinned checkout (see work record verification.md).
