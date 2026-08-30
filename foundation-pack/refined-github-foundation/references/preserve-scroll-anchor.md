<!-- capsule-v2 -->
# preserve-scroll-anchor — how do you keep the viewport stable when your own DOM mutations shift the layout?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** When a feature bulk-mutates the page (dimming rows, expanding collapsed items) and the content below the fold moves, how do you restore the user's exact scroll position without fighting their own scrolling?

## Capture anchor top now, restore delta next frame
**Path/Symbol:** `source/helpers/preserve-scroll.ts` — `preserveScroll` :1–15 (whole file 15 lines).
**Signature:** `preserveScroll(anchor?: Element): VoidFunction` (default anchor = element at viewport center).

### Decisive source
```ts
export default function preserveScroll(
	anchor: Element = document.elementFromPoint(window.innerWidth / 2, window.innerHeight / 2)!,
): VoidFunction {
	const originalPosition = anchor.getBoundingClientRect().top;
	/** Resets the previously-saved scroll */
	return () => {
		requestAnimationFrame(() => {
			const newPosition = anchor.getBoundingClientRect().top;
			window.scrollBy(0, newPosition - originalPosition);
		});
	};
}
```

**Flow:** caller captures a restore handle BEFORE mutating (anchor's viewport-relative top is read synchronously) → caller performs its layout-shifting mutation → caller invokes the handle → on the NEXT animation frame the new top is measured and `window.scrollBy(0, delta)` cancels exactly the shift. Default anchor (element under the viewport center) makes "keep what I was looking at" a zero-argument call.
**Invariant:** (1) capture-before-mutate / restore-after-mutate ordering is load-bearing — capturing after the mutation measures the already-shifted position and restores nothing; (2) the restore measurement is rAF-deferred so it sees POST-layout geometry (synchronous re-measure can read stale layout); (3) the anchor must OUTLIVE the mutation — `click-all.ts:25` anchors on `clickedItem.parentElement!` with the comment "`parentElement` is the anchor because `clickedItem` might be hidden/replaced after the click"; (4) delta-based `scrollBy` (not `scrollTo`) composes with any user scroll that happens between capture and restore.
**Probe:** no direct unit test (scroll/DOM-bound; standing browser-bound caveat). Executed pins: `grep -n "elementFromPoint|getBoundingClientRect|requestAnimationFrame|scrollBy" source/helpers/preserve-scroll.ts` → lines 2, 4, 10, 11, 12.
**Consumer evidence:** live `trace_path inbound preserveScroll` → callers_total 2 (`features.dim-bots`); `search_code "preserveScroll"` adds `source/helpers/click-all.ts:25`. dim-bots usage (`dim-bots.tsx:28-33`): `const resetScroll = preserveScroll(target)` → add `rgh-interacted` class to every dimmed bot row → `resetScroll()`. Cross-reference: click-all-batching.md (the alt-click fan-out this helper stabilizes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "preserveScroll", direction: "inbound", limit: 25 });
// callers_total: 2 → features.dim-bots (click-all.ts confirmed via search_code)
```
Executed 2026-08-27 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the 15-line capture-delta/rAF-restore shape as the standard companion to any bulk DOM mutation in an overlay extension — it is framework-agnostic and pairs with every batch operation (see click-all-batching.md). Adapt the default anchor heuristic to your host's reading position; omit nothing else — no host coupling. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no upstream direct test — deterministic source pins stand in.
