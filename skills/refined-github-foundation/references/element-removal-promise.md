<!-- capsule-v2 -->
# element-removal-promise — how do you await an element leaving the DOM without MutationObserver ancestor-walking?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** What is the cheapest reliable "resolve when this node is detached" primitive, and how must it behave under abort and repeated calls?

## Memoized ResizeObserver detachment promise
**Path/Symbol:** `source/helpers/on-element-removal.ts:onElementRemoval` (:3–29, whole file 31 lines).
**Signature:** `(async (element: Element, signal?: AbortSignal): Promise<void>)` wrapped in `memoize` (per-element promise cache).
**Data Shape:** resolves `void` on detachment OR abort (never rejects); memo key = element identity.

### Decisive source
```ts
const onElementRemoval = mem(async (element: Element, signal?: AbortSignal): Promise<void> => {
	if (signal?.aborted) { return; }
	return new Promise(resolve => {
		const observer = new ResizeObserver(([{target}]) => {
			if (target.isConnected) { return; }
			observer.disconnect();
			resolve();
		});
		if (signal) {
			signal.addEventListener('abort', () => {
				observer.disconnect();
				resolve();
			}, {once: true});
		}
		observer.observe(element);
	});
});
```

**Flow:** caller awaits per element → ResizeObserver fires when the node's box changes — INCLUDING the callback that runs once the node is disconnected → guard checks `target.isConnected`; only a false triggers disconnect+resolve → an aborted signal short-circuits to resolve with observer cleanup.
**Invariant:** (1) ResizeObserver still delivers one final callback after detach, which is what makes it cheaper than tracking ancestor chains with MutationObserver; (2) early-abort check precedes observation so an already-dead run never observes; (3) abort RESOLVES (not rejects) — `await` sites need no try/catch and treat "gone or cancelled" identically; (4) memoization means two features awaiting the same element share ONE observer.
**Probe:** no direct unit test exists for this file (standing browser-bound caveat). Executed pins: `grep 'mem\(|target\.isConnected|observer\.disconnect|once: true' source/helpers/on-element-removal.ts` → lines 3, 10, 14, 20, 23.
**Consumer evidence:** live `trace_path inbound onElementRemoval` → clean-conversation-sidebar.cleanReviewers + cleanSidebarLegacy, quick-comment-edit.addQuickEditButton.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "onElementRemoval", direction: "inbound" });
// callers_total: 3 → features.clean-conversation-sidebar ×2, features.quick-comment-edit ×1
```
Executed 2026-08-26 @ pin 3187161.

## Verdict
Adopt the ResizeObserver-detachment trick wholesale for teardown-await patterns (restore buttons after UI removal, cleanup after host swaps). Adapt the memoization scope if elements churn heavily (unbounded cache). Omit nothing else. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no upstream direct test — deterministic source pins stand in.
