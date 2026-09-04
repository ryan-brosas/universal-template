<!-- capsule-v2 -->
# Caller-ID Deduplication — how do you make "add this UI exactly once" safe across soft navigations without storing state?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** How can a pure function know whether IT (not just any code) already inserted an element somewhere?

## Connected graph-selected seam
**Path/Symbol:** `source/helpers/caller-id.ts:` `getCallerId` (:21–24), `getStackLine` (:8–14); consumers `source/helpers/attach-element.ts` (:294–321), `source/helpers/selector-observer.tsx` (:57); hash `source/helpers/hash-string.ts`.
**Signature:** `getCallerId(ancestor = 1): string` — hash of the `line:column` text at stack position `ancestor+1` (the +1 skips the function itself).
**Data Shape:** ID space = truncated JS hash (`(h<<5)-h + codePoint`, stringified) of the raw stack line. Unstable across builds BY DESIGN (it only needs stability within one loaded bundle).

### Decisive source
```ts
export default function getCallerId(ancestor = 1): string {
	/* +1 because the first line comes from this function */
	return hashString(getStackLine(new Error('Get stack').stack!, ancestor + 1));
}
```
```ts
// attach-element.ts — the DOM-based dedup pattern:
const className = 'rgh-attached-' + getCallerId();
if (elementExists('.' + className, anchor.parentElement!)) return;
const element = before(anchor);          // NOTE: callback must return the element SYNCHRONOUSLY
element.classList.add(className);
anchor.before(element);
```

**Flow:** callsite identity is extracted from `new Error().stack` → hashed → embedded into a DOM marker (class name on the inserted node, or `:not(.rgh-seen-<id>)` in an observer's CSS rule) → next invocation detects its own marker in the anchor's parentage and no-ops. Because the mark lives IN THE PAGE, history-restored DOM carries the evidence automatically — zero storage.
**Invariant:** the helper wrapping `getCallerId` shifts the stack, hence the `ancestor` parameter (`selector-observer.waitForElement` passes `ancestor: 4`). The attach callback MUST build the element synchronously ("A placeholder element MUST be returned synchronously. The deduplication logic is DOM-based" — attach-element.ts:287): awaiting before insertion breaks detection and duplicates UI. Class names are unhashed-prefixed (`rgh-attached-`, `rgh-seen-`) so `getClasses()` can strip them when comparing page classes.
**Probe:** `source/helpers/caller-id.test.ts` pins stack-line extraction incl. the Firefox missing-header quirk (`#6032`); `attachElement` itself is test-less (browser DOM) — behavior boundary recorded as caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "getCallerId attach-element rgh-attached", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for idempotent UI injection anywhere you control neither navigation nor DOM lifetime. Adapt the marker prefix and whether you need cross-build stability (re-hash per deploy is fine for extensions). Omit the `warn()` fallback randomness only if you can guarantee stack shape. Direct test covers stack parsing; DOM-side behavior is caveat-recorded.
