<!-- capsule-v2 -->
# shouldCancel default-prevention ladder — when must a trigger swallow the browser's native action?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** For which event/element pairs must htmx preventDefault, and which clicks must pass through untouched (anchors, reset buttons, ctrl-clicks, fragment links)?

## shouldCancel: submit-on-form and click-in-submit-button/link rules
**Path/Symbol:** `src/htmx.js:shouldCancel` (:2435-2456); explicit-cancel arm in addEventListener (`explicitCancel=true` from boostElement); pass-through guard `ignoreBoostedAnchorCtrlClick` (:2463-2467).
**Signature:** `function shouldCancel(evt, elt)` → true for (`submit` on FORM); for `click`: nearest `input[type=submit], button` WITH a form AND type==='submit', OR nearest `<a>` whose href does NOT start `#<chars>` (fragment anchors `/#foo/` navigate natively; bare `href="#"` IS cancelled to stop scroll-to-top).
**Data Shape:** The link test reads `link.getAttribute('href')` (the RAW value) against regex `/^#.+/, but navigates via `link.href` existence — so `<a href="#section">` inside boosted content still jumps locally while `<a href="#">` doesn't bounce the page.

### Decisive source
```js
if (evt.type === 'submit' && elt.tagName === 'FORM') { return true }
else if (evt.type === 'click') {
  const btn = elt.closest('input[type="submit"], button')
  // Do not cancel on buttons that 1) don't have a related form or 2) have a type attribute of 'reset'/'button'.
  if (btn && btn.form && btn.type === 'submit') { return true }
  const link = elt.closest('a')
  // Allow links with href="#fragment" ... Cancel default action for links with href="#" ...
  const samePageAnchor = /^#.+/
  if (link && link.href && !samePageAnchor.test(link.getAttribute('href'))) { return true }
}
return false
```

**Flow:** every registered trigger listener calls `explicitCancel || shouldCancel(evt, eltToListenOn)` BEFORE filters/once/changed gates — prevention happens even for events whose filter later drops them, because letting a native submit run after deciding not to fire would double-act.
**Invariant:** A naked-trigger element (hx-trigger without verb) registers NO-OP handlers but STILL cancels via this path — hx-trigger alone can suppress native behavior. Reset/button-type buttons never cancel (their forms must keep working). Ctrl/meta-click on BOOSTED anchors bypasses everything earlier in the listener (ignoreBoostedAnchorCtrlClick) so browser tab-opening semantics win; non-boosted links rely on the fragment rule instead.
**Flow:** the ladder's ordering explains regressions tests where "a button clicked inside an htmx enabled link will prevent the link from navigating" — closest() walks up from the deepest target, so inner buttons claim cancellation before outer links are consulted.

**Probe:** `test/core/regressions.js` :274 ("modified click on a form does not prevent other elements"), :324/:345/:366/:388 (button-inside-link/form nesting matrix), :410/:432/:454 (from:-trigger prevents native submission/navigation). Fragment-link semantics at hx-swap/hx-boost suites; anchor pass-through `test/attributes/hx-boost.js:210` ("ctrlKey mouse click does not boost"). Executed headless: n/a (DOM event semantics).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "shouldCancel preventDefault click submit link anchor", limit: 5 });
```

## Verdict
Adopt the ladder order (inner-most first) and both carve-outs verbatim; they encode the entire "does my app fight the browser" question. Adapt selector constants to your namespace. Omit the fragment-anchor nuance and users WILL report page-jump bugs.
