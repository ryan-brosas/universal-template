<!-- capsule-v2 -->
# Autocomplete field detection + post-type guidance — how does typing into a combobox differ from a plain input?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does the input action detect JS-driven autocomplete fields and what behavioral nudges/delays follow?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/service.py` — `_is_autocomplete_field` (:464), input action autocomplete branch (:838-851), value-mismatch note (:831).
**Signature:** `_is_autocomplete_field(node: EnhancedDOMTreeNode) -> bool`.

### Decisive source
```python
def _is_autocomplete_field(node):
    attrs = node.attributes or {}
    if attrs.get('role') == 'combobox': return True
    aria_ac = attrs.get('aria-autocomplete', '')
    if aria_ac and aria_ac != 'none': return True
    if attrs.get('list'): return True                       # native <datalist>
    haspopup = attrs.get('aria-haspopup', '')
    if haspopup and haspopup != 'false' and (attrs.get('aria-controls') or attrs.get('aria-owns')):
        return True
    return False

# After TypeTextEvent succeeds:
if _is_autocomplete_field(node):
    msg += '\n💡 This is an autocomplete field. Wait for suggestions to appear, then click
            the correct suggestion instead of pressing Enter.'
    # Only delay for TRUE JS-driven autocomplete (combobox / aria-autocomplete),
    # NOT native <datalist> or loose aria-haspopup which the browser handles instantly
    if attrs.get('role') == 'combobox' or (attrs.get('aria-autocomplete', '') not in ('', 'none')):
        await asyncio.sleep(0.4)   # let JS dropdown populate before next action

# Value-mismatch feedback (non-sensitive only): handler returns actual_value in metadata;
# if it differs from typed text, tell the LLM the page reformatted/autocompleted its input.
```

**Flow:** four-signal detection (role=combobox / aria-autocomplete≠none / list attr / haspopup+controls-or-owns) → advisory message appended to ActionResult memory → 0.4s mechanical delay ONLY for the two JS-driven signals → actual-value mismatch surfaced as an explicit warning line.
**Invariant:** the delay is deliberately narrower than detection (datalist needs no wait); sensitive-data fields skip the actual-value comparison so real page values never echo secrets; `haspopup='false'` must be treated as absence.
**Probe:** `tests/ci/test_multi_act_guards.py` (input non-terminating :134); deterministic citation :464-:481 + :838-:851 (coverage caveat: no dedicated autocomplete test).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "_is_autocomplete_field combobox aria-autocomplete actual_value TypeTextEvent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-signal detector + delay-only-JS-driven split + mismatch surfacing; adapt the 0.4s constant; omit emoji copy.
