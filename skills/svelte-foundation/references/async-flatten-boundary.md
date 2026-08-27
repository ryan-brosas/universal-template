<!-- capsule-v2 -->
# Async flatten/boundary plane — how do `await` expressions suspend a batch without losing the reactive context?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** When a template or effect contains `await`, what keeps the pre-await effect as the dependency owner, what gates the pending UI, and how are superseded async runs cancelled?

## flatten — the await-block kernel
**Path/Symbol:** `packages/svelte/src/internal/client/reactivity/async.js:flatten` (:36-115), `capture` (:130-157), `save` (:167-176), `run` (:286-356), `increment_pending` (:368-381); consumers `dom/blocks/async.js:async` (:20-69), `reactivity/effects.js:template_effect` (:390-396) / `deferred_template_effect` (:405-409), `deriveds.js:async_derived` (:114-290).
**Signature:** `flatten(blockers, sync, async, fn)`; `capture() => restore(activate_batch?)`; `save(promise) => Promise<() => T>`; `run(thunks) => Blocker[]`.
**Data Shape:** `blockers: {promise, settled}[]` (from outer awaits / `$effect` thunks); `sync: (() => any)[]`; `async: (() => Promise<any>)[]`; each async expression becomes an `async_derived` — an ASYNC|EFFECT_PRESERVED effect whose resolution is a `Source<V>` carrying the value.

### Decisive source
```js
// flatten: fast path + context-restoring finish
if (async.length === 0 && pending.length === 0) {
	fn(deriveds);
	return;
}
...
function finish(async) {
	if ((parent.f & DESTROYED) !== 0) return;
	restore();
	try {
		fn([...deriveds, ...async]);
	} catch (error) {
		invoke_error_boundary(error, parent);
	}
	unset_context();
}
```
and save/capture for `await a + b`:
```js
export async function save(promise) {
	var restore = capture();
	var value = await promise;
	return () => {
		restore();
		queue_micro_task(unset_context);
		return value;
	};
}
```

**Flow:** Sync expressions become deriveds (`derived` in runes mode, `derived_safe_equal` otherwise) so they stay live after the await. Already-settled blockers are filtered out. Each async expression runs inside `async_derived`: its promise resolves to a Source; superseded in-flight runs are rejected with OBSOLETE (eagerly while the boundary still shows pending, or via `batch.async_deriveds.get(effect)?.reject(OBSOLETE)` once rendered), and the final `internal_set(signal, value)` is wrapped in `batch.activate()/deactivate()` so the write lands in the right batch. `finish` restores the captured active_effect/reaction/component_context/current_batch **before** calling fn — so dependencies read inside the then-branch attach to the pre-await effect — and routes thrown errors to `invoke_error_boundary`. `capture()` also re-activates and re-applies the previous batch on restore (guarded by DESTROYED). The compiler rewrites `await a + b` to `(await $.save(a))() + b` (AwaitExpression.js:15) so `b`'s reads register against the pre-await effect. Pending accounting: `increment_pending()` pairs `boundary.update_pending_count(±1, batch)` with `batch.increment(blocking, effect)` where `blocking = boundary?.is_rendered()` — this is what shows/hides the boundary's pending UI. `run(thunks)` chains `$effect` thunks sequentially, each becoming its own blocker; a stale run throws STALE_REACTION, errors route to the boundary unless the effect aborted, and one extra microtask tick guarantees template effects run before user `$effect`s.
**Invariant:** Context must be restored BEFORE the continuation body runs (deps attach to the pre-await effect, not to nothing) and unset AFTER it (leaked context poisons the next synchronous work). A destroyed parent must never have its continuation applied. Superseded async runs must reject with OBSOLETE before their resolution can commit a stale value.
**Probe:** `packages/svelte/tests/runtime-runes/samples/async-await/main.svelte` + `_config.js` (reset/reject cycle through `{#await}` with boundary); `samples/async-block-rerun/_config.js` pins re-run of an async block when both override and promise change; `samples/async-state-eager-const/_config.js` exercises the teardown path of an eager derived across an await.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "flatten capture save increment_pending async_derived OBSOLETE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flatten contract (sync→deriveds, async→promise-of-source, restore-before-fn, error-to-boundary, settled-blocker filter) and the save/capture context sandwich — they are the whole trick that makes `await` composable with fine-grained signals. Adapt blocker/pending-count plumbing to your host's suspense primitive; omit the DEV reactivity-loss tracker and `for_await_track_reactivity_loss`. Caveat: MCP graph retrieval not executable in this session (daemon not connected); evidence is direct source/test reading at the pinned checkout (see work record verification.md).
