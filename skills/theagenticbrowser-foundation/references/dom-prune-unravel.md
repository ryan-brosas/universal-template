<!-- capsule-v2 -->
# DOM-tree prune + unravel — how do you shrink an accessibility snapshot to interactive-only without orphaning children?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you cut a page tree down to what an agent may act on, while keeping parent→child paths intact for elements whose wrapper carries no semantics?

## Post-order prune with child-lifting, semantic interactivity filter
**Path/Symbol:** `core/utils/get_detailed_accessibility_tree.py`:`__prune_tree` (`:315-377`), `__should_prune_node` (`:380-435`).
**Signature:** `def __prune_tree(node: dict[str, Any], only_input_fields: bool) -> dict[str, Any] | None`.
**Data Shape:** Input is the reconciled a11y snapshot dict; deletion markers (`marked_for_deletion_by_mm` set during reconciliation) and unravel markers (`marked_for_unravel_children`) ride on nodes. Output is the same tree modified IN PLACE with dead branches removed; returns None when the node itself should be dropped by its parent.

### Decisive source
```python
if "marked_for_deletion_by_mm" in node:
    return None
if 'children' in node:
    i = 0
    while i < len(node['children']):
        child = node['children'][i]
        if 'marked_for_unravel_children' in child:
            if 'children' in child:
                node['children'] = node['children'][:i] + child['children'] + node['children'][i+1:]
                i += len(child['children']) - 1   # lift grandchildren up one level
            else:
                node['children'].pop(i); i -= 1   # unravel a childless wrapper = delete it
        else:
            pruned_child = __prune_tree(child, only_input_fields)
            if pruned_child is None:
                node['children'].pop(i); i -= 1
            else:
                node['children'][i] = pruned_child
        i += 1
    if not node['children']:
        del node['children']
return None if __should_prune_node(node, only_input_fields) else node
```
`__should_prune_node` keeps the root WebArea unconditionally. In fields mode (`only_input_fields=True`) interactivity is SEMANTIC: tag ∈ {input, button, textarea, a, select, form} OR role ∈ {button, link, textbox, combobox, searchbox, menuitem, menubar, option, radio, checkbox, tab, tablist, listbox, menuitemcheckbox, menuitemradio, slider, spinbutton, switch} OR `is_clickable == True` OR real tabindex OR aria-expanded/aria-selected/aria-checked present. Always pruned: separator/LineBreak roles, childless name-less generics; empty-ish nodes (only name+role left) survive ONLY as role=text with meaningful text (names shorter than 3 chars are blanked first).

**Flow:** reconcile (mark deletions) → post-order recursion → per-child: unravel-marker? lift children : recursive prune → drop emptied children arrays → apply own-node predicate → parent splices result.
**Invariant:** Manual index management in the while loop is load-bearing — after lifting N grandchildren you must advance the index past exactly those inserted children or they get re-pruned/double-visited. The tree is mutated in place, so no other code may hold references into it mid-prune. Pruning happens AFTER reconciliation so that mmid-bearing nodes deleted from DOM view don't leave dangling targets.
**Probe:** No test suite exists (coverage caveat). Deterministic check: the predicate's WebArea root guard plus the two marker strings are pinned in source at `:344`, `:351`, and `marked_for_deletion_by_mm` writer at `:287`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "prune tree unravel marked_for_deletion", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the post-order prune + unravel pattern for any LLM-facing tree minimization; adopt the semantic interactivity allowlists as a starting vocabulary. Adapt the tag/role sets to your target sites. Omit nothing in index arithmetic — off-by-one here silently deletes siblings.
