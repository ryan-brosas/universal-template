<!-- capsule-v2 -->
# History-Restore Deduplicator — how do you mark "this DOM is already processed" so re-running features after back-navigation can no-op?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What does the `rgh-deduplicator` meta-feature actually do and why must it run FIRST with a tick delay?

## Connected graph-selected seam
**Path/Symbol:** `source/features/rgh-deduplicator.tsx` (:1–28, whole file).
**Signature:** `features.add('rgh-deduplicator', {awaitDomReady: true, async init() {…}})` — private id (no `import.meta.url`).
**Data Shape:** two sentinel elements: `<has-rgh />` appended into the pjax containers (`#js-repo-pjax-container, #js-pjax-container`) and `<has-rgh-inner />` inside every `<turbo-frame>`.

### Decisive source
```tsx
/*
When navigating back and forth in history, GitHub will preserve the DOM changes;
This means that the old features will still be on the page and don't need to re-run.
*/
void features.add('rgh-deduplicator', {
	awaitDomReady: true,
	async init() {
		// `await` kicks it to the next tick, after the other features have checked for 'has-rgh', so they can run once.
		await Promise.resolve();
		$optional('has-rgh')?.remove();
		$optional(_`#js-repo-pjax-container, #js-pjax-container`)?.append(<has-rgh />);
		$optional(_`turbo-frame`)?.append(<has-rgh-inner />);
	},
});
```

**Flow:** entry point imports this file BEFORE all others (refined-github.ts :123, commented "Core feature that needs to run first; it serves the `deduplicate` key") → on each page load it wipes stale sentinels then re-plants them → features using the deprecated `deduplicate: 'selector'` loader option skip when the sentinel exists.
**Invariant:** the `await Promise.resolve()` tick-yield is load-bearing: without it the dedup marker lands before same-tick feature checks read it, so everything runs once anyway on first load but double-runs on restores. Sentinels are planted INSIDE pjax containers so GitHub's own navigation swaps carry/destroy them correctly. The `_()` wrapper routes selectors through the hotfix string channel (server-side fixable without a release).
**Probe:** no unit test; behavior pinned by import-order comment at refined-github.ts:122–123 and the tick comment at :16–17 of the file. Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "rgh-deduplicator has-rgh deduplicate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sentinel-element pattern for any SPA overlay whose host restores DOM on history navigation. Adapt container selectors + sentinel tag names. Omit only if your host fully recreates body content per navigation. No direct test — caveat recorded.
