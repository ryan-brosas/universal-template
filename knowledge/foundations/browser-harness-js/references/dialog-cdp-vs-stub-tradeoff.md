<!-- capsule-v2 -->
# dialog-cdp-vs-stub-tradeoff — how are blocking dialogs dismissed, and when is JS stubbing the wrong tool?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** Which dialog dismissal path survives frozen JS and stays antibot-undetectable?

## Reactive CDP vs proactive stub matrix
**Path/Symbol:** `skills/cdp/interaction-skills/dialogs.md` whole doc — reactive (:5–35), proactive stub (:37–59), beforeunload (:61–75).
**Signature:** `session.Page.enable()` + `session.Page.handleJavaScriptDialog({accept: bool, promptText?})`; wait via `waitFor('Page.javascriptDialogOpening', undefined, 10_000)`; subscribe-all via `onEvent`.
**Data Shape:** handles all four types (alert/confirm/prompt/beforeunload) even while page JS is FROZEN. Stub path (`window.alert = m => …`, confirm→true, prompt→default) records into `window.__dialogs__` but: lost on navigation (re-inject each navigate), confirm always true, DETECTABLE via `window.alert.toString()` non-native reveal, does NOT handle beforeunload.

### Decisive source
```md
Undetectable by antibot — no JS runs in the page.
...
- Does **not** handle `beforeunload`.
```

**Flow:** expect dialogs → Page.enable + either wait-for-one or subscribe-to-all handler → handleJavaScriptDialog(accept) → read ev.type/ev.message. beforeunload: navigate THEN accept ("Leave") in try/catch (no dialog = normal), or null out `window.onbeforeunload` pre-navigate (detectable).
**Invariant:** CDP dialog handling works at the browser layer — it is the only path that functions with a blocked main thread and leaves zero page-visible trace; stubbing mutates page-visible globals. This is the same detectability asymmetry as print-as-pdf's window.print interception.
**Probe:** `grep -cF 'handleJavaScriptDialog' skills/cdp/interaction-skills/dialogs.md` → 5; `grep -cF '__dialogs__' <same>` → 5; `grep -cF 'Does **not** handle `beforeunload`' <same>` → 1; `grep -cF 'Undetectable by antibot' <same>` → 1.
**Retrieve:** search_code --project browser-harness-js --pattern "javascriptDialogOpening" (Module node resolves line-exact).

## Verdict
Adopt reactive CDP handling as default + the stub tradeoff table for flows needing dialog CONTENT capture. Adapt timeout budgets. Omit stub injection entirely under antibot pressure.
