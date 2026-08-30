<!-- capsule-v2 -->
# Time-travelling batches — how do concurrent async batches coexist without corrupting each other's view of state?

**Source:** svelte MIT `main@15720b16a5ef33e3e1f4301c77b94ec375070e73`; Codebase Memory `svelte`. **Question:** When two async updates are in flight and the older one resolves last, how does the runtime keep reads consistent per batch — and who wins on commit?

## Per-batch value maps + read override
**Path/Symbol:** `packages/svelte/src/internal/client/reactivity/batch.js:capture` (:585-599), `apply` (:875-922), `#find_earlier_batch` (:480-497), `#merge` (:502-567), `#commit` (:659-784); read side `runtime.js:get` (:701-703).
**Signature:** `capture(source, value, is_derived = false)`; `apply(): void`; static `ensure(): Batch`; private `#commit()`.
**Data Shape:** Per batch: `current: Map<Value, [value, is_derived]>`, `previous: Map<Value, any>` (keys identical to current); module-level `batch_values: Map<Value, any> | null`.

### Decisive source
```js
// capture:
if (!this.is_fork) {
	source.v = value;
}
// get():
if (batch_values?.has(signal)) {
	return batch_values.get(signal);
}
```
and the rebase in #commit:
```js
for (const [source, [value, is_derived]] of this.current) {
	if (batch.current.has(source)) {
		var batch_value = batch.current.get(source)[0];
		if (is_earlier && value !== batch_value) {
			// bring the value up to date
			batch.current.set(source, [value, is_derived]);
		} else {
			continue;
		}
	}
	sources.push(source);
}
```

**Flow:** Every write is captured into the active batch (`source.v` written immediately for non-forks; errors never stored). While multiple batches exist, `apply()` installs `batch_values` = this batch's values plus non-intersecting earlier batches' *previous* values — so code running inside batch B sees B's world ("time travelling"). A younger batch that finishes while an older one still has pending async work is merged into it via `#find_earlier_batch`/`#merge` (transferring dirty sets and async-derived deferreds); at `#commit`, still-pending older batches are rebased: values newer than theirs are pushed down, and only async/block effects depending on sources changed in *both* worlds are re-marked DIRTY and re-run. Forks (`fork(fn)`) go further: they never write `source.v` during capture, only install batch_values, applying real writes at commit.
**Invariant:** The keys of `current` and `previous` stay identical; a batch's view of a source must be stable for its whole lifetime (reads consult `batch_values` before `signal.v`). Later batch wins on conflicting commits; earlier batches rebase rather than overwrite newer values. Deriveds participate specially — their captures carry `is_derived=true` and are excluded from intersection tests to avoid false positives when one batch triggered them and the other hasn't yet.
**Probe:** `packages/svelte/tests/runtime-runes/samples/fork-derived-dependency-rollback/_config.js` (a fork whose derived switches dependency mid-flight rolls back cleanly; later real increment shows through) — with samples `async-dont-rebase-new-batch-*`, `async-commit-preserve-new-batch` pinning the merge/rebase ladder.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "svelte", query: "batch_values time travelling capture previous commit rebase", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-transaction value maps with a read-time override layer, merge-younger-into-older semantics, and commit-time rebase that only re-runs effects touched by both transactions. Adapt fork semantics (speculative preload) only if your host needs speculative execution; omit SvelteKit-specific integration.
