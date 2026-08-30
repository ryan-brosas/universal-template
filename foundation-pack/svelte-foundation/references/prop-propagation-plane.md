<!-- capsule-v2 -->
# Prop propagation plane — how do component props stay in sync with parent state without being signals themselves?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** When a component declares `$props()`, what runtime object does each prop become — and how do spread, rest, binding, and local writes each route through it?

## prop() accessor factory — three return shapes
**Path/Symbol:** `packages/svelte/src/internal/client/reactivity/props.js:prop` (:276-433), `spread_props` (:262-263 + handler :187-256), `rest_props` (:93-94 + handler :54-74), `legacy_rest_props` (:165-179 + handler :101-141).
**Signature:** `prop(props, key, flags, fallback?) => () => V | ((v) => V) | ((v, mutation) => V)`; flags = PROPS_IS_BINDABLE | PROPS_IS_IMMUTABLE | PROPS_IS_LAZY_INITIAL | PROPS_IS_RUNES | PROPS_IS_UPDATED.
**Data Shape:** `props` is the `$$props` object (or a `spread_props` proxy); a prop is NOT a signal — it is a closure over `props[key]`. Bindable props may carry a setter descriptor on the parent side; entry props are detected via `STATE_SYMBOL in props || LEGACY_PROPS in props`.

### Decisive source
```js
// prop(): the three shapes
if (runes && (flags & PROPS_IS_UPDATED) === 0) {
	return getter; // read-only: plain closure over props[key] + fallback
}
if (setter) {
	// bound prop: writes go straight to the parent's slot
	return function (value, mutation) {
		if (arguments.length > 0) {
			if (!runes || !mutation || legacy_parent || is_store_sub) {
				setter(mutation ? getter() : value);
			}
			return value;
		}
		return getter();
	};
}
// written locally without a binding: derived override
var d = ((flags & PROPS_IS_IMMUTABLE) !== 0 ? derived : derived_safe_equal)(() => {
	overridden = false;
	return getter();
});
```
and the runes getter's fallback re-evaluation:
```js
getter = () => {
	var value = /** @type {V} */ (props[key]);
	if (value === undefined) return get_fallback();
	fallback_dirty = true;
	return value;
};
```

**Flow:** The compiler emits `$.prop($$props, 'name', flags, fallback)` per declared prop. Read: `props[key]`, falling back when undefined — in runes mode the fallback is re-evaluated on every undefined read (a lazy fallback becomes a real `derived`); in legacy mode the fallback latches to `undefined` after the first defined read (Svelte 4 semantics). Write with a parent binding: call the parent's setter directly, but suppress *mutation* notifications in runes mode (the parent's state proxy already tracks them) unless the parent is legacy or the prop is a store subscription (`is_store_sub` from `capture_store_binding`). Write without a binding: `set(d, new_value)` on the local derived and flip `overridden=true`; because the derived fn resets `overridden=false` on every run, the next parent-side change recomputes and the local override drops away. Teardown-time reads of an overridden prop return `d.v` directly (no recompute) so destroyed components don't resurrect values. Spread: `spread_props(...)` is a Proxy over an array of prop sources walked **backwards** (later spread wins); entries may be thunks re-evaluated per access; `has()` returns false for STATE_SYMBOL/LEGACY_PROPS so `prop()`'s entry-props detection isn't fooled by a spread; `getOwnPropertyDescriptor` forces `configurable=true` to avoid proxy invariant violations. Rest: `rest_props` excludes named keys via a Set (read-only in DEV); `legacy_rest_props` adds a coarse-grained `version` source bumped on every set/delete, and promotes a first-written key into a `special` map holding a real `prop()` created under the captured `parent_effect` so subsequent writes stay fine-grained.
**Invariant:** A prop read must always reflect the parent's current slot value unless a local write has overridden it in this flush; the `overridden` flag must be reset inside the derived fn (not outside) or stale overrides survive parent updates. Spread lookup order must stay backwards or `{...a} {...b}` precedence breaks.
**Probe:** `packages/svelte/tests/runtime-runes/samples/props-spread-fallback/main.svelte` + `_config.js` (fallback kept while spread prop is undefined, taken over when defined, restored when undefined again); `samples/props-bound-fallback/_config.js` pins the `props_invalid_value` error for `bind:count={undefined}` with a fallback; `samples/bind-and-spread/_config.js` pins two-way flow through `{...props} bind:value`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "prop spread_props rest_props legacy_rest_props overridden", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the accessor-factory model (props as closures, not signals) with the three-shape split, backwards spread-proxy lookup, and the reset-inside-fn override latch — these are what make bind/spread/local-write compose. Adapt the flag bits to your compiler's prop metadata; omit the legacy-mode fallback latch and `legacy_rest_props` version-source unless porting Svelte 4 compatibility. Caveat: MCP graph retrieval not executable in this session (daemon not connected); evidence is direct source/test reading at the pinned checkout (see work record verification.md).
