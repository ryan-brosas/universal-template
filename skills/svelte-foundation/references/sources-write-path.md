<!-- capsule-v2 -->
# Sources write path — how does a write propagate dirtiness without recomputing anything?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** When `$state` is written, what exactly happens before any effect runs — and why can writes inside effects not lose their own scheduling?

## Write path: set → internal_set → mark_reactions
**Path/Symbol:** `packages/svelte/src/internal/client/reactivity/sources.js:internal_set` (:181-268) and `mark_reactions` (:343-399).
**Signature:** `internal_set(source, value, updated_during_traversal = null)`; `mark_reactions(signal, status, updated_during_traversal)`.
**Data Shape:** A Source is a plain object `{ f, v, reactions, equals, rv, wv }`; writes are gated by `source.equals(value)` (default `equals` is `===`-ish safe_not_equal semantics; mutable sources use `safe_equals`).

### Decisive source
```js
var batch = Batch.ensure();
batch.capture(source, value);
...
source.wv = increment_write_version();
mark_reactions(source, DIRTY, updated_during_traversal);

// It's possible that the current reaction might not have up-to-date dependencies
// whilst it's actively running. ... i.e: `$effect(() => x++)`
if (
	is_runes() &&
	active_effect !== null &&
	(active_effect.f & CLEAN) !== 0 &&
	(active_effect.f & (BRANCH_EFFECT | ROOT_EFFECT)) === 0
) {
	if (untracked_writes === null) {
		set_untracked_writes([source]);
	} else {
		untracked_writes.push(source);
	}
}
```

**Flow:** equality gate → record pre-flush value in `old_values` (only if absent — teardowns must see the value *before the first* write of this flush, not the last) → `Batch.ensure().capture()` → bump global write version → walk only **direct** `reactions`: effects get DIRTY + `schedule_effect`, deriveds recurse with MAYBE_DIRTY guarded by a WAS_MARKED flag so shared deriveds are visited once, EAGER_EFFECTs ($inspect/$state.eager) are collected into `eager_effects` and flushed immediately via `flush_eager_effects()` (which dirty-checks CLEAN ones with `is_dirty` instead of blind-firing to avoid overfiring). If the writer is itself a still-CLEAN running effect, the source goes to `untracked_writes` so `update_reaction` can adopt it as a dep when the effect finishes — this is what makes `$effect(() => { x++ })` re-run instead of silently losing the dependency.
**Invariant:** No reaction is ever *executed* by a write; writes only flip status bits and schedule. A DIRTY reaction must never be demoted to MAYBE_DIRTY (`if (not_dirty)` guard), because DIRTY means "a direct dep changed" and MAYBE_DIRTY checks would otherwise be skipped.
**Probe:** `packages/svelte/tests/runtime-runes/samples/effect-self-scheduling/main.svelte` + `_config.js` (`$effect(() => { if (power !== 10) power += 1 })` settles at 10 without infinite loop; every intermediate value renders under flushSync).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "internal_set untracked_writes eager effects", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the write contract: single equality gate, capture-then-mark, status-bit-only propagation, first-write-per-flush old-value snapshot, and the untracked-writes self-adoption latch. Adapt `flush_eager_effects`' immediate execution to your host's debug/eager primitives; omit DEV tracing (`source.updated` stack maps after 5 writes) unless porting devtools.
