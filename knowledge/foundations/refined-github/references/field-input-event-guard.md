<!-- capsule-v2 -->
# field-input-event-guard — how do shortcuts observe text fields without fighting IME composition and autocomplete dropdowns?

**Source:** refined-github MIT `main@3187161079033cc1eda1731044ba8a2fdd7b69b4`; Codebase Memory `refined-github`. **Question:** How should delegated field keydown/input listeners skip "user is mid-something" states and avoid duplicate registration across features?

## ignoreInteractive guard ladder + memoized listener dedupe
**Path/Symbol:** `source/github-events/on-field-keydown.tsx` — `ignoreInteractive` :11–26, `deduplicateInteractiveFilter = memoize(...)` :33, `capture = true` :36, handlers `onCommentFieldKeydown` :38–45 / `onConversationTitleFieldKeydown` :47–63 (selector list incl. dated TODO removals :53–57) / `onCommitTitleFieldKeydown` :65–72. Input-event twin: `source/github-events/on-commit-title-update.ts:onCommitTitleUpdate` :10–16 (`fieldSelector` :3–8 covers mergebox text input + `#commit-message-input`).
**Signature:** `ignoreInteractive(callback: KeydownHandler): KeydownHandler`; handlers `(callback: KeydownHandler, signal: AbortSignal): void`.
**Data Shape:** `TextField = HTMLTextAreaElement | HTMLInputElement`; guard reads `event.isComposing`, attributes on `event.delegateTarget`, and queries the target's form.

### Decisive source
```ts
if (
	event.isComposing
	// New autocomplete dropdown
	|| field.hasAttribute('aria-autocomplete')
	// Classic autocomplete dropdown
	|| elementExists('.suggester', field.form!)
) {
	return;
}
callback(event);
…
const deduplicateInteractiveFilter = memoize((callback: KeydownHandler) => ignoreInteractive(callback));
// Support for `esc` key (where GitHub uses stopPropagation)
const capture = true;
```

**Flow:** feature init passes its keydown callback → memoized wrapper returns THE SAME wrapped function per callback reference → delegate-it deduplicates identical (selector, event, listener) triples so N features sharing a callback register one DOM listener → events fire only when no IME composition is active and no autocomplete dropdown owns the field.
**Invariant:** (1) composition/autocomplete states MUST swallow shortcuts or Enter-submits break mid-word; (2) wrapper identity must be stable — wrapping inline would multiply listeners; (3) capture phase is required because GitHub's own Esc handling calls stopPropagation in bubble phase; (4) legacy selectors carry dated TODO comments (2026-09-01/2027-01-01) — porters must re-verify them at their pin.
**Probe:** no direct unit test exists for this file (keyboard/DOM-bound; standing caveat). Executed pins: `grep 'isComposing|aria-autocomplete|suggester|memoize\(|const capture = true' source/github-events/on-field-keydown.tsx` → lines 15, 17, 19, 33, 36; twin pin `'input', callback` in on-commit-title-update.ts → line 15.

**Consumer evidence:** live traces — `onCommentFieldKeydown` ← one-key-formatting.init, tab-to-indent.init; `onConversationTitleFieldKeydown` ← esc-to-cancel.init, one-key-formatting.init; `onCommitTitleFieldKeydown` ← one-key-formatting.init; `search_code 'on-commit-title-update'` → suggest-commit-title-limit.tsx:7 import (+ sync-pr-commit-title module hit).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", qn_pattern: "refined-github\\.source\\.github-events\\..*", fields: ["lines", "signature"] });
// total: 20 rows across the four adapter files incl. KeydownHandler type fan-in 5,
// capture Variable :36 fan-out 16 consumers of the wrapped filter
```
Executed 2026-08-26 @ pin 3187161.

## Verdict
Adopt the three-condition guard ladder (composition → aria-autocomplete → form suggester), the memoized-wrapper listener dedupe trick, and capture-phase registration for shortcut surfaces. Adapt the selector lists to your host's fields and drop the dated legacy selectors only after checking your pin. Coverage caveat: both paths `no_recorded_issue` @ gen 2026-08-24T14:04:43Z; no upstream direct tests — deterministic source pins stand in.
