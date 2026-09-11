<!-- capsule-v2 -->
# CSS-Animation Selector Observer — how do you watch for elements appearing anywhere in a huge DOM without MutationObserver?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the animation-based observation mechanism, its dedup rule, and the abort/once/stopOnDomReady composition?

## Connected graph-selected seam
Second-highest fan-in in the graph (`helpers.selector-observer.observe`, 141 inbound edges) — the DOM-watching backbone of every feature.

**Path/Symbol:** `source/helpers/selector-observer.tsx:` `observe` (:29–113), `waitForElement` (:115–136), `registerAnimation` (:25–27).
**Signature:** `observe<Selector extends string>(selectors: string | readonly string[], listener: (element: ExpectedElement, options: SignalAsOptions) => void, {signal?, stopOnDomReady?, once?, ancestor?}): void`.
**Data Shape:** one `<style>` per observe() call: `:where(${selector}):not(.rgh-seen-${callerHash}) { animation: 1ms rgh-selector-observer; }`; keyframe registered ONCE globally via onetime.

### Decisive source
```ts
if (stopOnDomReady) {
	const delayedDomReady = signalFromPromise((async () => {
		await domLoaded;
		await delay(100); // Allow the animation and events to complete; Also adds support for ajaxed pages
	})());
	signal = mergeSignals(signal, delayedDomReady);
}
let onceController: AbortController | undefined;
if (once) { onceController = new AbortController(); signal = mergeSignals(signal, onceController.signal); }

const seenMark = 'rgh-seen-' + getCallerId(ancestor);
rule.textContent = css`:where(${selector}):not(.${seenMark}) { animation: 1ms ${animation}; }`;
document.body.prepend(rule);
signal?.addEventListener('abort', () => { rule.remove(); });

globalThis.addEventListener('animationstart', event => {
	if (event.animationName !== animation) return;
	const target = event.target as ExpectedElement;
	// The target can match a selector even if the animation actually happened on a
	// ::before pseudo-element, so it needs an explicit exclusion here
	if (target.classList.contains(seenMark) || !target.matches(selector)) return;
	wasCalled = true;
	target.classList.add(seenMark);   // removes THIS element from future matches
	listener(target, {signal});
	onceController?.abort();
}, {signal});
```

**Flow:** install rule → browser fires `animationstart` whenever a matching element renders → handler re-validates (pseudo-element false positives + seen-mark) → marks the element with the caller-scoped class so it never fires again → invokes listener with the merged signal → `once` aborts after first hit; aborting the merged signal removes the STYLE RULE (the actual observer).
**Invariant:** dedup is PER CALLSITE (hash of the stack line via `ancestor`), not global — two features observing the same selector each get their own seen-mark, and one element is delivered to both exactly once. The 100ms post-DOM-ready delay before stopping is required or late-firing animations are missed (#ajaxed pages). `waitForElement` must pass `ancestor: 4` — its extra wrapper frames shift the callsite identity. Elements matched while the listener body runs still carry their mark, so re-observing the same node requires removing the mark class.
**Probe:** no unit test (browser animation events); deterministic pins: rule text :68–72, pseudo-element exclusion comment :100–101, ancestor:4 at :129. Behavior is pinned by 141 call sites across the codebase. Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "selector-observer observe waitForElement rgh-seen animationstart", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any content script needing cheap appear-events across both initial render and SPA swaps — orders of magnitude cheaper than MutationObserver trees. Adapt the keyframe name/mark prefix; keep the re-validation guard. Omit stopOnDomReady if your host mutates after load forever. No direct test — caveat recorded.
