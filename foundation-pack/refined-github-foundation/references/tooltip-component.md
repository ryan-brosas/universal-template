<!-- capsule-v2 -->
# tooltip-component — how do you attach accessible tooltips to elements you don't own, that survive SPA re-renders?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** How can an overlay extension describe host buttons with real tooltips (keyboard/screen-reader reachable, shortcut chords) when the host framework re-renders those buttons constantly?

## Id-linked popover portaled to the surviving container
**Path/Symbol:** `source/components/tooltip.tsx` — `createTooltipFor` :12–28, `addTooltip` :34–43, `withTooltipRef` :49–58 (whole file 58 lines); `source/components/tooltip.svelte` — portal target :22–32, `<tool-tip>` :34–55.
**Signature:** `addTooltip(content: string | TooltipOptions, element: Element): void`; `withTooltipRef(content: string | TooltipOptions): (element: Element | null) => void`; `TooltipOptions = {label: string; shortcut?: string; direction?: 'n'|'ne'|'e'|'se'|'s'|'sw'|'w'|'nw'; type?: 'label'|'description'}`.

### Decisive source
```ts
function createTooltipFor(element: Element, content: string | TooltipOptions): void {
	// Ensure the element has an ID for the `for` attribute to link to
	element.id ||= crypto.randomUUID();
	const tooltipId = crypto.randomUUID();
	element.setAttribute('aria-labelledby', tooltipId);
	const options = typeof content === 'string' ? {label: content} : content;
	mount(Tooltip, {target: element, props: {id: tooltipId, htmlFor: element.id, ...options}});
}
// addTooltip guard:
if (!element.parentElement) {
	throw new Error('Element has no parent. Use `tooltipped` instead for elements not yet attached to a parent.');
}
// tooltip.svelte getTarget — "Align tooltip behavior with native" (PR #9668):
return lastElement(['#js-repo-pjax-container', '#js-pjax-container', '#repo-content-turbo-frame', '#repo-content-pjax-container', '[data-turbo-body]']);
// rendered node:
<tool-tip {id} for={htmlFor} class="sr-only position-absolute" popover="manual" data-direction={direction} role="tooltip" use:portal={getTarget}>
```

**Flow:** attach → target gets a stable id (`||=` keeps existing) + `aria-labelledby` pointing at a fresh UUID → Svelte component mounts INTO the target element but its `<tool-tip>` node is PORTALED out into the deepest pjax/turbo container (the subtree that survives soft navigation) → native popover semantics (`popover="manual"`, `role="tooltip"`, `for`/`htmlFor` pairing) give focus/hover behavior without any JS positioning; `shortcut` renders as `<kbd>` chords split on spaces.
**Invariant:** (1) the tooltip DOM lives OUTSIDE the described element's subtree — linkage is purely by ids, so host-framework re-renders of the button cannot destroy or duplicate the tooltip; (2) `addTooltip` requires an ATTACHED element (parentElement check throws with a pointer to the JSX alternative) — mounting into a detached tree would leave a dead id link; (3) the portal target list is ORDERED and `lastElement` picks the deepest match (repo containers before profile's `[data-turbo-body]`) — reordering silently changes which container owns tooltips on profile pages; (4) the ref callback tolerates `null` (unmount) and never unmounts the tooltip — persistence across re-renders is the point.
**Probe:** no direct unit test (DOM/popover-bound; standing browser-bound caveat). Executed pins: `grep -n "element.id ||=" source/components/tooltip.tsx` → 14; `grep -n "popover=|use:portal|lastElement(" source/components/tooltip.svelte` → 25, 38, 43. Lint enforcement: `eslint-rules/restricted-syntax.js:49-58` `byo/prefer-tooltipped` errors on any `data-hotkey` JSX element lacking `withTooltipRef`/`tooltipped()` — the tooltip contract is a BUILD ERROR, not a doc.
**Consumer evidence:** live `trace_path inbound withTooltipRef` → callers_total 22 (conflict-marker, default-branch-button, delete-branch, quick-repo-deletion, …); `addTooltip` callers_total 3 (jump-to-conversation-close-event, quick-repo-deletion, unread-anywhere). `quick-repo-deletion.tsx:81,90` shows both entry points side by side (imperative button + JSX ref).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "refined-github", function_name: "withTooltipRef", direction: "inbound", limit: 25 });
// callers_total: 22 across features/*
```
Executed 2026-08-27 @ pin 3187161 via vendor CLI (identical tool surface).

## Verdict
Adopt the id-linking + portal-to-surviving-container pattern for ANY annotation layer (tooltips, badges, callouts) over a re-rendering host: describe by id, render in the stable subtree, and let native popover/ARIA semantics do the interaction work. Adopt the lint-enforced contract (hotkey ⇒ tooltip mention) as the governance piece. Adapt the container selector list to your host's soft-nav boundaries; omit the octicon-free `<kbd>` styling details and the GitHub PR #9668 alignment comment. Coverage caveat: `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no upstream direct test — deterministic source pins + fan-in traces stand in.
