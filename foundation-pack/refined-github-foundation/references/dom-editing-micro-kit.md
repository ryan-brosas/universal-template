<!-- capsule-v2 -->
# dom-editing-micro-kit — what are the small, sharp DOM-composition primitives (textarea block-wrap, JSX join, element type-swap, portal) that features reach for instead of ad-hoc code?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** Which micro-primitives encode non-obvious DOM rules a porter would otherwise re-derive wrongly?

## smartBlockWrap — two-newline isolation for injected content
**Path/Symbol:** `source/helpers/smart-block-wrap.ts:smartBlockWrap` (:4–21).
**Signature:** `smartBlockWrap(content: string, field: HTMLTextAreaElement): string` (PURE: returns the wrapped string; caller writes it back).
**Data Shape:** Reads `field.value` + current selection; output = content padded to ≥2 newlines on each side, but only where real content exists.

### Decisive source
```ts
const before = field.value.slice(0, field.selectionStart);
const after  = field.value.slice(field.selectionEnd);
const [whitespaceAtStart] = /\n*$/.exec(before)!;
const [whitespaceAtEnd]   = /^\n*/.exec(after)!;
const newlinesToPrepend = /\S/.test(before) && whitespaceAtStart.length < 2
	? '\n'.repeat(2 - whitespaceAtStart.length) : '';
```
**Flow:** split field text at the caret/selection → count trailing/leading newlines → pad content to two newlines ONLY if non-whitespace content exists on that side (`/\S/.test`) and fewer than two newlines already separate it.
**Invariant:** Never pads against an empty side (top-of-field insert gets no leading `\n\n`) and never exceeds two — idempotent under re-wrap. Adapted from GitHub's own source ("Code adapted from GitHub").
**Probe:** No direct unit test; pure function, caveat recorded.

## joinJsx — separator-between without trailing separators
**Path/Symbol:** `source/helpers/join-jsx.tsx:joinJsx` (:24–38).
**Signature:** `joinJsx(separator: React.ReactNode, items: readonly JSX.Element[]): JSX.Element`.
**Data Shape:** Fragment of `index > 0 && separator` + item pairs.
**Invariant:** The `index > 0` gate lives INSIDE the map — no trailing separator after the last item; fragments per item keep keys unnecessary. (No direct test; trivial.)

## replaceElementTypeInPlace — change a tag without losing children/handlers' position
**Path/Symbol:** `source/helpers/recreate-element.ts:replaceElementTypeInPlace` (:39–51).
**Signature:** `replaceElementTypeInPlace<Type extends keyof HTMLElementTagNameMap>(oldElement: Element, type: Type): HTMLElementTagNameMap[Type]`.
### Decisive source
```ts
const newElement = document.createElement(type);
for (const {name, value} of oldElement.attributes) newElement.setAttribute(name, value);
newElement.append(...oldElement.children);
oldElement.replaceWith(newElement);
return newElement;
```
**Flow:** fresh element ← copy ALL attributes ← move child nodes ← atomic `replaceWith`. **Invariant:** attributes are COPIED not moved; listeners on `oldElement` itself die (only children survive); return value is the NEW node — callers must rebind references. (No direct test; caveat recorded.)

## portal (Svelte action) — move-after-mount with timing guard
**Path/Symbol:** `source/helpers/portal.ts:portal` (:54–76).
**Signature:** `Action<HTMLElement, () => Element>` — Svelte action taking a target-getter.
### Decisive source
```ts
function move(): void {
	if (!node.isConnected) {
		// This is a requirement for `tool-tip` — PR #9668
		throw new Error('The element was not added to the document in time');
	}
	getTarget().append(node);
}
if (node.isConnected) { move(); } else { queueMicrotask(move); }
```
**Flow:** if already connected move NOW, else defer one microtask (Svelte mounts nodes before actions run in some orders); destroy() removes the node. **Invariant:** throws rather than silently failing when the node was never inserted — required by the `tool-tip` consumer (#9668), because appending a disconnected node drops it. (No direct test; caveat recorded.)

## Verdict
Adopt all four as a unit — they're the vocabulary the feature layer is written in. Adapt `smartBlockWrap`'s two-newline constant to your host's markdown rules; adapt portal's throw message/timing to your framework mount order; treat `replaceElementTypeInPlace`'s listener-loss as documented behavior, not a bug to fix.
