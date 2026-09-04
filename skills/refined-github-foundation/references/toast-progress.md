<!-- capsule-v2 -->
# Toast Progress & Result — how do you report a long task's progress in-page and guarantee the result is readable before removal?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the toast lifecycle — spinner states, live message updates, display-time formula, and the rAF paint gate?

## Connected graph-selected seam
**Path/Symbol:** `source/github-helpers/toast.tsx:showToast` (:247–328 of file; graph QN `github-helpers.toast.showToast` fan-in 12).
**Signature:** `showToast(task: Promise | ((progress: (msg: string|JSX) => void) => Promise) | Error, {message?, doneMessage?: string|JSX|false}): Promise<void>`.
**Data Shape:** three visual states via class replacement `Toast--loading → Toast--success | Toast--error`; icon swap `<ToastSpinner/> → <CheckIcon/> | <StopIcon/>`; accepts pre-thrown `Error` to render a failure without work.

### Decisive source
```ts
// Without rAF the toast might be removed before the first page paint
await frame();
// Reading-time-scaled display: ~300ms per word, 3s for rich JSX, +2s base:
const displayTime = (typeof newMessage === 'string' ? newMessage.split(' ').length * 300 : 3000) + 2000;
await delay(displayTime);
toast.classList.replace('Toast--animateIn', 'Toast--animateOut');
await oneEvent(toast, 'animationend');
toast.remove();
```

**Flow:** build DOM (role="log", z-index 101) → append → **`await delay(30)`** ("Without this, the Toast doesn't appear in time") → run task (function form receives `updateToast` for live progress) → success path replaces loading→success, fires final update WITHOUT awaiting (`void finalUpdateToast(...)`) so the promise resolves as soon as the work is done → failure path swaps icon, rethrows AFTER scheduling the error toast.
**Invariant:** the initial 30ms delay and the pre-removal `frame()` are both race guards porters delete first and then ship flickering/never-visible toasts. `doneMessage: false` means "reuse the LAST progress message" (captured via `lastRawMessage`). Errors propagate to the caller even though the UI shows them — never swallow.
**Probe:** no unit test (visual/DOM); deterministic pins at :290–300 (rAF + formula), :304 (30ms), :317–327 (state transitions). Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "showToast finalUpdateToast updateToast", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any bulk-action feedback loop. Adapt classes/icons to your design system but keep the two timing gates and the rethrow contract. Omit JSX rich messages if plain-text only. No direct test — caveat recorded.
