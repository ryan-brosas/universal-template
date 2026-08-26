<!-- capsule-v2 -->
# Listbox typeahead — how does "type to jump" accumulate keystrokes and rotate the search window past the active option?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is the exact Search reducer: query accumulation, rotation offset, disabled skipping, and match==active handling?

## ActionTypes.Search / ClearSearch
**Path/Symbol:** `packages/@headlessui-react/src/components/listbox/listbox-machine.ts:308-345`; consumed via `actions.search(value)` from ListboxOptions keydown.
**Signature:** `Search(state, { value: string }): State` — appends lowercase char; `ClearSearch` resets when non-empty.
**Data Shape:** `searchQuery: string`; matching uses `option.dataRef.current.textValue?.startsWith(query)` where textValue comes from getTextValue (aria-label > aria-labelledby > innerText-minus-emoji).

### Decisive source
```ts
[ActionTypes.Search]: (state, action) => {
  let wasAlreadySearching = state.searchQuery !== ''
  let offset = wasAlreadySearching ? 0 : 1        // fresh key starts AFTER the active option
  let searchQuery = state.searchQuery + action.value.toLowerCase()
  let reOrderedOptions = state.activeOptionIndex !== null
    ? state.options.slice(state.activeOptionIndex + offset)
        .concat(state.options.slice(0, state.activeOptionIndex + offset))   // rotate
    : state.options
  let matchingOption = reOrderedOptions.find((option) =>
    !option.dataRef.current.disabled && option.dataRef.current.textValue?.startsWith(searchQuery))
  let matchIdx = matchingOption ? state.options.indexOf(matchingOption) : -1
  if (matchIdx === -1 || matchIdx === state.activeOptionIndex) return { ...state, searchQuery }
  return { ...state, searchQuery, activeOptionIndex: matchIdx, activationTrigger: Other }
}
```

**Flow:** keystroke → append to query → rotate the option array so the scan begins just after the active index (offset 1 only when NOT already mid-search, so continuing a word re-scans the active candidate too) → first non-disabled prefix match wins → move active; a miss (or matching the already-active option) keeps the position but PRESERVES the query so the next keystroke can complete the word. ClearSearch fires on navigation actions (GoToOption resets query in its base spread).
**Invariant:** rotation is the wrap mechanism — no separate modulo needed since find() scans the rotated order; textValue is computed OUTSIDE the machine per option and cached on dataRef; disabled options never match even if their text prefix-matches.
**Probe:** direct tests: `listbox.test.tsx:3174-3390` '`Any` key aka search' suite pins case-insensitive search, next-occurrence rotation ('should be possible to search for the next occurrence'), and disabled-option exclusion. Graph probe resolves getTextValue + LabelProvider line-exact.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "getTextValue emoji aria-label", name_pattern: "^getTextValue$", limit: 5 });
```

## Verdict
Adopt the rotation+offset semantics verbatim (the wasAlreadySearching ? 0 : 1 subtlety is what makes repeated prefixes work); adapt the textValue producer if you cache differently but keep aria-label priority and emoji stripping; omit ClearSearch coupling only if your navigation keys intentionally keep the query.
