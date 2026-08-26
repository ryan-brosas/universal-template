<!-- capsule-v2 -->
# attachElement — how do you insert UI next to an anchor exactly once across soft navigations?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** When a feature must add an element before/after a page anchor on every page load, what contract keeps it idempotent when the feature re-runs after SPA soft navigation?

## Anchor-relative insertion with caller-ID dedupe marker
**Path/Symbol:** `source/helpers/attach-element.ts:attachElement` (:15–42); identity from `source/helpers/caller-id.ts:getCallerId`.
**Signature:** `attachElement<NewElement extends Element>(anchor: Element | undefined, {before?, after?}: RequireAtLeastOne<{className?: string; before: Callback; after: Callback}, 'before' | 'after'>): void` where `Callback = (anchor: Element) => NewElement`.
**Data Shape:** `anchor` may be `undefined` (callers pass `$optional(...)` results directly) → throws `'Element not found'`. `before`/`after` are factory callbacks receiving the anchor and returning the element synchronously. No return value.

### Decisive source
```ts
// NOTE: Do not turn the Callback into an async function or else the deduplication won't work.
// A placeholder element MUST be returned synchronously. The deduplication logic is DOM-based.
const className = 'rgh-attached-' + getCallerId();
if (elementExists('.' + className, anchor.parentElement!)) {
	return;
}
if (before) {
	const element = before(anchor);
	element.classList.add(className);
	anchor.before(element);
}
if (after) { /* same, anchor.after(element) */ }
```

**Flow:** resolve caller ID from stack → compute marker class → check `anchor.parentElement` for an existing `.rgh-attached-<id>` descendant → if present return silently; otherwise run each provided factory, tag its product with the marker class, and insert relative to the anchor (`anchor.before` / `anchor.after`, not parent-level append).
**Invariant:** The dedupe check runs against `anchor.parentElement` BEFORE any factory executes, so factories must be side-effect-free until their element is actually inserted; and the callback must return the element synchronously (no `await`) or the DOM-based check races and duplicates appear. Both callbacks share ONE marker class — running both still counts as "already attached" on re-run.
**Probe:** `source/helpers/caller-id.test.ts` pins the stack-line→ID mapping that feeds the marker class (incl. Firefox quirk #6032). No direct unit test for `attachElement` itself — behavior pinned via call sites (`source/features/show-names.tsx:67` passes only `{after}`, `clear-pr-merge-commit-message.tsx:43` uses both slots). Coverage caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "attachElement", limit: 10 });
// → refined-github.source.helpers.attach-element.attachElement Function source/helpers/attach-element.ts 15-42
```

## Verdict
Adopt the whole pattern for any extension inserting per-page UI under a soft-navigating host: caller-derived marker class + parent-scoped existence check + sync factory callbacks. Adapt the marker prefix (`rgh-attached-`) to your namespace and `getCallerId` to your stack-parse util (see `caller-id-dedupe.md`). Omit nothing — the async-callback prohibition is the porting trap; making the factory async silently breaks idempotency.
