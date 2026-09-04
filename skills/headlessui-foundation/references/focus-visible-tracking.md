<!-- capsule-v2 -->
# Focus-visible tracking — how does the library know the last interaction was keyboard (for focus rings) without :focus-visible polyfills?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What are the exact global listeners that maintain `data-headlessui-focus-visible` on <html>?

## module-level keydown/click capture listeners
**Path/Symbol:** `packages/@headlessui-react/src/utils/focus-management.ts:156-195` (`ActivationMethod`, listener registration); consumer styling hooks read `document.documentElement.dataset.headlessuiFocusVisible`.
**Signature:** side-effect at module import: two `document.addEventListener(..., true)` registrations guarded by `typeof window !== 'undefined' && typeof document !== 'undefined'`.
**Data Shape:** attribute is PRESENT = keyboard-driven focus; ABSENT = pointer-driven. `event.detail`: 0 for synthetic/keyboard-triggered clicks, 1 for real mouse clicks.

### Decisive source
```ts
enum ActivationMethod { Keyboard = 0, Mouse = 1 }

document.addEventListener('keydown', (event) => {
  if (event.metaKey || event.altKey || event.ctrlKey) return   // shortcuts don't move focus
  document.documentElement.dataset.headlessuiFocusVisible = ''
}, true)

document.addEventListener('click', (event) => {
  if (event.detail === ActivationMethod.Mouse) {               // real mouse click: clear
    delete document.documentElement.dataset.headlessuiFocusVisible
  } else if (event.detail === ActivationMethod.Keyboard) {     // Enter/Space on a button: set
    document.documentElement.dataset.headlessuiFocusVisible = ''
  }
}, true)
```

**Flow:** any non-modifier keydown marks focus-visible → mouse click clears it → keyboard-activated click (detail===0) re-marks. Components style their focus ring against `[data-headlessui-focus-visible]` descendants instead of `:focus-visible` where browser support or shadow-DOM behavior is lacking.
**Invariant:** modifier-key keydowns are IGNORED (Cmd+Tab etc. shouldn't imply focus movement); the click handler must distinguish detail values — using truthiness would misclassify keyboard activation; capture phase so nothing can swallow the signal.
**Probe:** deterministic checks executed: modifier guard, detail===1 clear, detail===0 set. Direct coverage: transitive via component suites asserting focus-ring classes in jsdom.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "headlessuiFocusVisible", limit: 5 });
```

## Verdict
Adopt the two-listener protocol verbatim when your design system needs JS-readable focus-visible state; adapt the attribute name to your namespace; omit entirely on modern targets where CSS :focus-visible suffices.
