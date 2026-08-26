<!-- capsule-v2 -->
# react-controlled-input-writers — how do you set a value in a React-controlled field (or any framework with synthetic onChange) so the host state actually updates?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** Why does `input.value = x` not work on React-managed inputs, and what is the minimal correct write sequence for input vs. textarea?

## Native-prototype setter + bubbling input event
**Path/Symbol:** `source/helpers/set-react-text-field-value.ts:setReactInputValue` / `setReactTextareaValue` (:3–11).
**Signature:** `setReactInputValue(target: HTMLInputElement, value: string): void`; `setReactTextareaValue(target: HTMLTextAreaElement, value: string): void`.
**Data Shape:** Fire-and-forget; no return, no error path.

### Decisive source
```ts
const nativeInputValueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!;
// https://stackoverflow.com/a/46012210
export function setReactInputValue(target: HTMLInputElement, value: string): void {
	nativeInputValueSetter.call(target, value);
	target.dispatchEvent(new Event('input', {bubbles: true}));
}

export function setReactTextareaValue(target: HTMLTextAreaElement, value: string): void {
	target.value = value; // textarea needs NO native-setter dance…
	target.dispatchEvent(new Event('input', {bubbles: true})); // …but still needs the event
}
```

**Flow:** (input) grab the PROTOTYPE's own value setter — bypassing React's instance-level property override that intercepts plain assignment and swallows the change → call it on the target → dispatch a real `input` Event with `bubbles: true` so React's delegated listener at the root sees it. (textarea) React does not shadow the textarea value the same way, so direct assignment suffices — but the bubbling event is still mandatory.
**Invariant:** Both halves are required for `<input>`: setter alone leaves React's virtual state stale (React re-renders the OLD value over yours); event alone doesn't change the DOM value past React's tracked value. The asymmetry between the two functions IS the porting trap — cargo-culting the prototype-setter dance to textarea is harmless but pointless, while skipping it on input silently fails.
**Probe:** No direct unit test (jsdom can't reproduce React's delegation faithfully here); caveat recorded. Behavior pinned by feature call sites that prefill GitHub's React comment/commit forms (e.g. `source/features/clear-pr-merge-commit-message.tsx`, which consumes `cleanCommitMessage`; the `cleanPrCommitTitle` twin is consumed by `sync-pr-commit-title.tsx`:12,:70 via `helpers/pr-commit-cleaner.ts`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "setReactInputValue", limit: 10 });
// → refined-github.source.helpers.set-react-text-field-value.setReactInputValue Function source/helpers/set-react-text-field-value.ts 3-6
```

## Verdict
Adopt both writers verbatim as the canonical "write into a React-controlled field from an extension/userscript" recipe (the SO-a/46012210 trick). Adapt the event name if the host framework listens to something else (Svelte uses `input` too; Vue 2 wanted `change` for checkbox-like components). Omit nothing else — this file has zero removable parts.
