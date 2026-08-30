<!-- capsule-v2 -->
# url-hash-replacestate-cleanup — how do you use the URL hash as ephemeral UI state without polluting browser history?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** Features want to stash transient state in the URL hash (line selection, one-shot deep-link triggers). Setting `location.hash` adds a history entry the user never asked for. How do you clean the hash up without leaving a back-button artifact?

## replaceState with preserved history.state
**Path/Symbol:** `source/helpers/history.ts` — `removeHashFromUrlBar` :1–5 (whole file 5 lines).
**Signature:** `removeHashFromUrlBar(): void`.

### Decisive source
```ts
export default function removeHashFromUrlBar(): void {
	const url = new URL(location.href);
	url.hash = '';
	history.replaceState(history.state, '', url.href);
}
```

**Flow:** rebuild the current URL via the WHATWG URL parser → clear ONLY the hash component → `history.replaceState(history.state, '', url.href)` swaps the current history entry in place — no new entry, and the existing `history.state` object is passed through UNTOUCHED.
**Invariant:** (1) passing `history.state` (not `null`) is load-bearing — `replaceState(null, …)` would WIPE any state the host SPA stored on the current entry; (2) replaceState (not pushState) is what keeps the back button from gaining a phantom step; (3) using the URL parser to strip the hash (rather than string surgery) means query strings and credentials survive intact.
**Probe:** no direct unit test (history/DOM-bound). Executed pin: `grep -n "replaceState" source/helpers/history.ts` → line 4. GRAPH ANOMALY recorded: live `trace_path inbound removeHashFromUrlBar` reports callers_total 145 — a heuristic over-match; direct whole-repo grep finds EXACTLY 2 consumers (below). Source wins over graph.

## Consumer idiom 1: hash as selection state, cleaned after the action
**Path/Symbol:** `source/features/esc-to-deselect-line.tsx` — `isLineSelected` :8–14, `listener` :16–39 (call at :38).
**Signature:** keyup listener on `document.body`, gated by `pageDetect.hasCode`.

### Decisive source
```ts
function isLineSelected(): boolean {
	// Example hashes:
	// #L1
	// #L1-L7
	// #diff-1030ad175a393516333e18ea51c415caR1
	return /^#L|^#diff-[\da-f]+R\d+/.test(location.hash);
}
// …after deselecting (mousedown-dispatch trick or #no-line fallback):
removeHashFromUrlBar();
```

**Flow:** GitHub's own line-selection state lives IN the hash (`#L11`, `#L1-L7`, `#diff-…R1`) → Esc keyup while a line is selected and no editable element has focus → deselect via a synthetic mousedown on the highlighted line number (dataset saved/restored around it) or the legacy `#no-line` fallback → `removeHashFromUrlBar()` strips the now-stale hash in place.
**Invariant:** the hash regex is the feature's STATE MACHINE input — it must match exactly the host's selection-hash grammar; cleanup runs AFTER the deselect action (removing the hash first would make the host re-render and lose the target).
**Probe:** no direct unit test (browser-bound). Executed pins: `grep -n "location.hash" source/features/esc-to-deselect-line.tsx` → lines 13, 35; `grep -n "removeHashFromUrlBar()" source/features/esc-to-deselect-line.tsx` → line 38.

## Consumer idiom 2: hash as a one-shot deep-link trigger
**Path/Symbol:** `source/features/github-actions-indicators.tsx` — registration include gate :171–175, `openRunWorkflow` :157–162 (call at :158).
**Signature:** feature registered with `include: [() => location.hash === '#rgh-run-workflow']`.

### Decisive source
```ts
function openRunWorkflow(): void {
	removeHashFromUrlBar();
	// Note that the attribute is removed after the first opening, so the selector only matches it once
	const dropdown = $('details[data-deferred-details-content-url*="/actions/manual?workflow="]');
	dropdown.open = true;
}
// …registration:
}, {
	include: [
		() => location.hash === '#rgh-run-workflow',
	],
```

**Flow:** the SAME feature mints the trigger: for manually-dispatchable workflows on other pages it appends `url.hash = 'rgh-run-workflow'` to a "Trigger manually" link it injects (:94–105) → visiting that link makes the include predicate TRUE, so the feature boots → its action opens the workflow dropdown → `removeHashFromUrlBar()` runs FIRST so a reload of the same URL does NOT re-trigger the open (the hash was a one-shot trigger, not persistent state).
**Invariant:** the remove-before-act ordering is what makes the trigger one-shot — removing after would still work for reloads but leaves the hash visible during the interaction; the predicate reads `location.hash` LIVE (function form), so the gate re-evaluates on soft navigation.
**Probe:** no direct unit test (browser-bound). Executed pins: `grep -n "rgh-run-workflow" source/features/github-actions-indicators.tsx` → lines 98, 173 (link minting + include gate); `grep -n "removeHashFromUrlBar()" source/features/github-actions-indicators.tsx` → line 158.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "removeHashFromUrlBar", mode: "ids" });
// total: 1 → helpers.history.removeHashFromUrlBar 1-5 line-exact
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "removeHashFromUrlBar", direction: "inbound" });
// callers_total: 145 — HEURISTIC OVER-MATCH; direct grep confirms exactly 2 consumers (esc-to-deselect-line, github-actions-indicators)
```
Executed 2026-08-28 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the 5-line helper verbatim in spirit — URL-parser hash strip + `replaceState(history.state, …)` is the correct primitive for any ephemeral-hash state in an overlay extension, and both consumer idioms (selection-state cleanup, one-shot deep-link trigger) are directly portable patterns. Adapt the hash grammars (`#L…`, `#diff-…R…`, your own trigger names) to your host's conventions. Omit nothing else — no host coupling beyond the grammar strings. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z on all three paths; no upstream direct tests (browser-bound) — deterministic source pins stand in; graph inbound trace over-matched (145 vs actual 2) — recorded as a graph-quality data point. Cross-reference: react-page-update-signal.md (the other URL/navigation-state adapter), boot-manifest-esm-bootstrap.md (why features re-run per navigation and must not leak state across them).
