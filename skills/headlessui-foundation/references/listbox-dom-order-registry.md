<!-- capsule-v2 -->
# Listbox DOM-order registry — why sort options on a rAF after registering, and how does the active index survive re-sorting?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is the register → pendingShouldSort → rAF SortOptions pipeline and the identity-based active-index re-lookup?

## RegisterOptions / SortOptions / adjustOrderedState
**Path/Symbol:** `packages/@headlessui-react/src/components/listbox/listbox-machine.ts:100-127` (`adjustOrderedState`), `:362-391` (RegisterOptions), `:426-434` (SortOptions), `:469-476` (rAF hook in constructor).
**Signature:** `adjustOrderedState(state, adjustment? = i=>i): { options, activeOptionIndex | null }`; batched action `registerOption(id, dataRef)`.
**Data Shape:** `options: { id, dataRef }[]`; `dataRef.current.domRef.current` is the DOM node used for ordering; `pendingFocus` carries the open-intent focus target until options exist.

### Decisive source
```ts
[ActionTypes.RegisterOptions]: (state, action) => {
  let options = state.options.concat(action.options)
  let activeOptionIndex = state.activeOptionIndex
  if (state.pendingFocus.focus !== Focus.Nothing) {
    activeOptionIndex = calculateActiveIndex(state.pendingFocus, {...})   // resolve deferred focus intent
  }
  if (state.activeOptionIndex === null) {
    let idx = options.findIndex((o) => isSelected(o.dataRef.current.value))  // preselect selected
    if (idx !== -1) activeOptionIndex = idx
  }
  return { ...state, options, activeOptionIndex, pendingFocus: { focus: Focus.Nothing }, pendingShouldSort: true }
}
// constructor: registration order ≠ DOM order, so defer the expensive sort:
this.on(ActionTypes.RegisterOptions, () => {
  requestAnimationFrame(() => this.send({ type: ActionTypes.SortOptions }))
})
[ActionTypes.SortOptions]: (state) => {
  if (!state.pendingShouldSort) return state
  return { ...state, ...adjustOrderedState(state), pendingShouldSort: false }
}
function adjustOrderedState(state, adjustment = (i) => i) {
  let currentActiveOption = state.activeOptionIndex !== null ? state.options[state.activeOptionIndex] : null
  let sortedOptions = sortByDomNode(adjustment(state.options.slice()), (o) => o.dataRef.current.domRef.current)
  let adjustedActiveOptionIndex = currentActiveOption ? sortedOptions.indexOf(currentActiveOption) : null
  if (adjustedActiveOptionIndex === -1) adjustedActiveOptionIndex = null   // option was REMOVED
}
```

**Flow:** options register (batched per microtask) in MOUNT order → machine marks pendingShouldSort and resolves any pendingFocus/selected-value intent immediately → one rAF later SortOptions re-sorts by compareDocumentPosition so arrow-key navigation matches VISUAL order regardless of React render order → active index is re-derived by OBJECT IDENTITY lookup, not stored number.
**Invariant:** never store the active index across a sort — always re-find by option object (`indexOf(currentActiveOption)`); removed active ⇒ null; the rAF sort is render-invisible (pure internal ordering). Fast paths in GoToOption skip sorting entirely for Nothing/Specific and for adjacent-sibling moves (`previousElementSibling`/`nextElementSibling` checks).
**Probe:** direct tests: `listbox.test.tsx` Registration + Keyboard suites pin DOM-order navigation with conditionally-rendered/reordered options. Deterministic check: sortByDomNode uses compareDocumentPosition FOLLOWING/PRECEDING only (ties keep stable order).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "ListboxMachine", name_pattern: "^ListboxMachine.new$|^ListboxMachine.reduce$", limit: 5 });
```

## Verdict
Adopt the pendingShouldSort+rAF deferral and identity-based re-lookup verbatim — sorting synchronously during registration causes O(n²) thrash and torn indices under Suspense; adapt the trigger for your framework's post-commit hook; omit GoToOption fast paths only if your lists are tiny.
