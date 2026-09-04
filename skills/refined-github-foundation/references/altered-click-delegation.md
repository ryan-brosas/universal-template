<!-- capsule-v2 -->
# altered-click-delegation — how do you catch ctrl/cmd/middle-clicks on delegated targets across the click/auxclick split?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** Why does one "modified link click" feature need THREE delegated listeners, and which phases?

## Triple-delegation with middle-click autoscroll suppression
**Path/Symbol:** `source/helpers/on-altered-click.ts:onAlteredClick` (:9–35, whole file 35 lines; helpers `isMiddleClick` :5–7, `preventAutoScrolling` :26–30).
**Signature:** `onAlteredClick<Selector extends string>(selector: Selector | readonly Selector[], callback: DelegateEventHandler<PointerEvent, ParseSelector<Selector>>, options?: DelegateOptions): void`.
**Data Shape:** callback receives the original PointerEvent from whichever listener matched; all three listeners merge caller `options` under forced `{capture: true}`.

### Decisive source
```ts
const clickListener: typeof callback = event => {
	if (isAlteredClick(event)) { callback(event); }
};
const auxClickListener: typeof callback = event => {
	if (isMiddleClick(event)) { callback(event); }
};
const preventAutoScrolling = (event: MouseEvent): void => {
	if (isMiddleClick(event)) { event.preventDefault(); }
};

delegate(selector, 'click', clickListener, {capture: true, ...options});
delegate(selector, 'auxclick', auxClickListener, {capture: true, ...options});
delegate(selector, 'mousedown', preventAutoScrolling, {...options, capture: true});
```

**Flow:** modifier-click (ctrl/cmd/shift-alt per filter-altered-clicks) arrives as 'click' → first listener forwards it; middle-click never fires 'click' — it fires 'auxclick' → second listener forwards button===1 events; Firefox starts middle-click AUTOSCROLL on 'mousedown' → third listener preventDefaults it so the auxclick handler's navigation wins.
**Invariant:** (1) you cannot collapse to one listener — modified clicks and middle clicks live on different event types; (2) capture phase on ALL three is required so host page handlers can't stopPropagation first; (3) mousedown prevention must be scoped to middle clicks only, or normal text selection breaks; (4) callback sees a PointerEvent whose `button` distinguishes the path (0=modified, 1=middle).
**Probe:** no direct unit test exists for this file (pointer-event-bound; standing caveat). Executed pins: `grep 'delegate\(|isAlteredClick|event\.button === 1|preventDefault' source/helpers/on-altered-click.ts` → lines 2, 6, 15, 28, 32, 33, 34 (exactly three `delegate(` sites).
**Consumer evidence:** live `trace_path inbound onAlteredClick` → linkify-line-numbers.init, new-tab-links.{initIssueTemplate, initNewIssueOnce, initSearchResultsOnce}.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "onAlteredClick", direction: "inbound" });
// callers_total: 4 → features.linkify-line-numbers 1; features.new-tab-links 3
```
Executed 2026-08-26 @ pin 3187161.

## Verdict
Adopt the three-listener split + capture + middle-click autoscroll guard verbatim for any open-in-new-tab / copy-link surface. Adapt the alteration predicate (filter-altered-clicks semantics differ slightly per browser) and selector vocabulary. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no upstream direct test — deterministic source pins stand in.
