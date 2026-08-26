<!-- capsule-v2 -->
# axClick/axType action pair — what is the minimal correct synthetic click, and why does locator-vs-ref dispatch matter?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** How do refs/locators become real input events at the right coordinates?

## backendNodeId → DOM.getBoxModel → center → pressed+released; axType = click-focus + insertText
**Path/Symbol:** `skills/cdp/sdk/repl.ts:resolveAxBackendId` (:47-57), `axClick` (:60-71), `axType` (:74-77).
**Signature:** `axClick(ref: number | string, refs?: Map<number, number> | string | null): Promise<void>` · `axType(ref, refs, text: string): Promise<void>`.
**Data Shape:** `ref` is either a ref number/`[n]` string (requires the refs map or view) OR a locator string (`role:`-prefixed — refs argument ignored/null); box model `content` quad's first two entries are x,y with `model.width/height`.

### Decisive source
```ts
const backendNodeId = extraHelpers.isLocatorString(ref)
  ? await extraHelpers.resolveLocator(ref as string)          // survives re-snapshots
  : resolveAxBackendId(ref, (refs as ...) ?? new Map());      // one-snapshot-only [n] slot
const { model } = await session.domains.DOM.getBoxModel({ backendNodeId });
const cx = model.content[0]! + model.width / 2;
const cy = model.content[1]! + model.height / 2;
await session.domains.Input.dispatchMouseEvent({ type: 'mousePressed',  x: cx, y: cy, button: 'left', clickCount: 1 });
await session.domains.Input.dispatchMouseEvent({ type: 'mouseReleased', x: cx, y: cy, button: 'left', clickCount: 1 });
```
and the stale-ref error text that teaches the protocol:
```ts
throw new Error(`Unknown ax ref [${n}] — re-snapshot; refs are only valid for one getFullAXTree`);
```

**Flow:** resolve to backendDOMNodeId (locator ladder or ref map; unknown slot = loud error demanding a re-snapshot) → box model in CSS pixels → center of the CONTENT box → synthetic left press+release pair. `axType` reuses `axClick` for focus then `Input.insertText({text})` (one call, no per-key timing).
**Invariant:** (1) clicks go through the REAL input pipeline (`Input.*`) — never `element.click()` via evaluate; recording classification and event fidelity both depend on it. (2) Locator vs ref dispatch is decided by STRING PREFIX, so passing a stale numeric ref with an empty Map fails loudly instead of clicking coordinates from a dead snapshot. (3) Center-of-content-box matches what a user aims at; border-box math drifts on padded elements.
**Probe:** no direct test (needs live layout). Deterministic probe: `grep -n "getBoxModel\|isLocatorString(ref)" skills/cdp/sdk/repl.ts` (:61-70).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "axClick", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the resolve→box→center→dispatch chain verbatim for any semantic-click helper; adapt to your geometry source if you skip CDP; omit nothing — the prefix-based dual dispatch plus loud stale-ref failure IS the safety story.
