<!-- capsule-v2 -->
# Dropdown option extraction & selection — native select / ARIA menu / combobox / custom

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does an agent enumerate and select options across native `<select>`, ARIA menus/listboxes, ARIA comboboxes, and Semantic-UI custom dropdowns?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/browser/watchdogs/default_action_watchdog.py`: `on_GetDropdownOptionsEvent` (:2812-3080), `_handle_aria_combobox_options` (:3082-3286), `on_SelectDropdownOptionEvent` (:3288-3746).
**Signature:** `on_GetDropdownOptionsEvent(event) -> dict[str,str]`; `on_SelectDropdownOptionEvent(event) -> dict[str,str]` returning `{'success','message','value','backend_node_id','selector_index'}`.

### Decisive source
```python
# Extraction: JS checks target then children (depth 4) for dropdown types:
#  - native <select>: Array.from(element.options) -> {text,value,index,selected}
#  - role menu/listbox: querySelectorAll [role=menuitem],[role=option]
#  - Semantic-UI: class .dropdown/.ui + .item/.option/[data-value]
#  - ARIA combobox (role=combobox + aria-controls): expand (focus+click+mousedown) if collapsed,
#     find listbox by aria-controls id, extract [role=option], then collapse (blur+Escape)
# Selection (case-insensitive match on text OR value):
#  - native select: focus FIRST (Svelte/Vue/React), set value + option.selected + selectedIndex,
#     dispatch input/change/blur; VERIFY element.value===expected else selectionReverted -> click fallback
#  - ARIA/menu: clear prior aria-selected, set item, item.click() + MouseEvent
#  - lazy-populated: if all options empty, focus() (no synthetic mouse) + retry once after 1s
```

**Flow:** resolve objectId → combobox check → extraction (target → children depth 4) → format options with JSON-encoded text/value for exact matching → selection: focus-then-set + verify for native select, click for ARIA, revert-detection + click fallback, lazy-load focus+retry.
**Invariant:** selection sets value via multiple methods (value + option.selected + selectedIndex) AND dispatches input/change/blur for reactive frameworks; **verification is mandatory** — if the framework reverts the value, fall back to a click; lazy dropdowns get one focus-then-retry; the `success` field is string `'true'`/`'false'` (not bool).
**Probe:** `tests/ci/interactions/test_dropdown_aria_menus.py`, `tests/ci/interactions/test_dropdown_native.py`, `tests/ci/interactions/test_autocomplete_interaction.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "on_GetDropdownOptionsEvent on_SelectDropdownOptionEvent aria-controls combobox selectionReverted", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the multi-type dropdown dispatch, the focus-then-set-with-verification selection contract, the revert→click fallback, and the lazy-load retry. Adapt to host's DOM query helpers.
