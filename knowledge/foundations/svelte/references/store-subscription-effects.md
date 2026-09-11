<!-- capsule-v2 -->
# Store subscription effects — how do `$store` auto-subscriptions bridge a callback world onto the signal graph?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** When `$value` is read, what runtime object keeps the store and the reactive graph in sync — and how do reassignment, synchronous first-callback, unmount, and store-bound props each behave?

## Per-name entry: {store, source, unsubscribe}
**Path/Symbol:** `packages/svelte/src/internal/client/reactivity/store.js:store_get` (:36-87), `store_unsub` (:90-107), `setup_stores` (:130-148), `update_with_flag` (:155-163), `capture_store_binding` (:215-224).
**Signature:** `store_get(store, store_name, stores) => V`; `setup_stores() => [StoreReferencesContainer, cleanup]`.
**Data Shape:** Each component gets one `stores` container; each `$name` read site maps to `stores[name] = { store, source: mutable_source(undefined), unsubscribe }`. The signal is a **mutable** source (deep-mutation of the value must notify).

### Decisive source
```js
if (entry.store !== store && !(IS_UNMOUNTED in stores)) {
	entry.unsubscribe();
	entry.store = store ?? null;
	if (store == null) {
		entry.source.v = undefined;
		entry.unsubscribe = noop;
	} else {
		var is_synchronous_callback = true;
		entry.unsubscribe = subscribe_to_store(store, (v) => {
			if (is_synchronous_callback) {
				// If the first updates to the store value (possibly multiple of them) are synchronously
				// inside a derived, we will hit the `state_unsafe_mutation` error if we `set` the value
				entry.source.v = v;
			} else {
				set(entry.source, v);
			}
		});
		is_synchronous_callback = false;
	}
}
```

**Flow:** First `$value` read creates the entry and subscribes; the store's initial callback fires **synchronously during subscription**, so the latch writes `source.v` directly (a `set()` there would trip `state_unsafe_mutation`, because we may be inside a derived's own evaluation). Later callbacks go through `set()`. Reassigning the underlying store (`value = writable(...)`) is detected on the next read by `entry.store !== store`: unsubscribe old, subscribe new — and because the new subscription's first callback runs before `store_get` returns, reads in the same expression see the NEW store's value immediately (this is what makes chained reassignment work). If the component unmounted, an `IS_UNMOUNTED` marker (defined non-enumerably on the container by `setup_stores`' teardown) flips reads to plain `get_store(store)` — no signal, no leaked subscription. `store_unsub` covers the asymmetric case where a store was replaced but never read again: it unsubscribes without resetting `entry.store`, so a later `store_get` can resubscribe. Writes (`$value = x`, `$value++`, mutation) go through `update_with_flag`, which brackets `store.set(value)` with `legacy_is_updating_store = true` so legacy `$:` effects can distinguish store-driven updates. `capture_store_binding(fn)` wraps the initial prop read with a module-level `is_store_binding` flag (set by `mark_store_binding()` inside generated prop getters) so `<Child bind:x={$y}/>` treats the prop as mutable even in runes mode and skips the `binding_property_non_reactive` validation.
**Invariant:** The synchronous-first-callback latch must write `source.v` directly — using `set()` during subscription breaks any store whose initial value is computed inside a derived. Unsubscribe-before-resubscribe order is mandatory (old subscription must not fire into the new entry). After unmount, no new subscription may ever be created.
**Probe:** `packages/svelte/tests/runtime-legacy/samples/store-auto-resubscribe-immediate/main.svelte` + `_config.js` (reassignment mid-expression resubscribes immediately; final html `{"answer":4}`); `samples/binding-store/_config.js` pins two-way flow between input bindings and a writable store prop.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "store_get store_unsub IS_UNMOUNTED capture_store_binding", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-name entry table with unsubscribe-then-resubscribe on identity change, the synchronous-first-callback direct-write latch, and the unmounted-marker escape to plain `get()`. Adapt the `legacy_is_updating_store` global only if you port legacy `$:` semantics; omit `invalidate_store` (compiler-emitted for `$:` invalidation) unless porting that plane. Caveat: MCP graph retrieval not executable in this session (daemon not connected); evidence is direct source/test reading at the pinned checkout (see work record verification.md).
