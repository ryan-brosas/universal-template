<!-- capsule-v2 -->
# MMID↔accessibility-tree reconciliation — how does the agent give the LLM stable element ids without shipping raw HTML?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa285d65584333e0c69b963360f8b74fd980f`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you number every element on a live page so the LLM can target them by id, when Playwright's accessibility snapshot carries NO link back to DOM nodes?

## Inject ids through an ARIA side-channel, read them back out of the tree
**Path/Symbol:** `core/utils/get_detailed_accessibility_tree.py`:`__inject_attributes` (`:32-55`), `is_space_delimited_mmid` (`:15-29`), `__fetch_dom_info` (`:58-292`).
**Signature:** `async def __inject_attributes(page: Page)`; `def is_space_delimited_mmid(s: str) -> bool`.
**Data Shape:** Every element gets two attributes set in ONE pass: sequential integer `mmid="N"` and `aria-keyshortcuts="<same N>"`. Pre-existing `aria-keyshortcuts` is preserved by renaming to `orig-aria-keyshortcuts` first. The JS returns the max id (`last_mmid`). In the tree, the id surfaces under the `keyshortcuts` property and may be space-delimited (`"123 456"` — page had its own shortcuts merged), so the reader splits on space and takes `[-1]`.

### Decisive source
```python
space_delimited_mmid = re.compile(r'^[\d ]+$')
# __inject_attributes (page.evaluate):
#   const origAriaAttribute = element.getAttribute('aria-keyshortcuts');
#   const mmid = `${++id}`;
#   element.setAttribute('mmid', mmid);
#   element.setAttribute('aria-keyshortcuts', mmid);
#   if (origAriaAttribute) element.setAttribute('orig-aria-keyshortcuts', origAriaAttribute);
# __fetch_dom_info reader:
if mmid_temp and is_space_delimited_mmid(mmid_temp):
    mmid_temp = mmid_temp.split(' ')[-1]
try:
    mmid = int(mmid_temp)
except (ValueError, TypeError):
    return node.get('name')   # node has no DOM counterpart -> left un-enhanced
```
Reconciliation walks the snapshot depth-first (children BEFORE parent at `:80-84`), and for each node carrying a valid keyshortcuts id runs a per-element `page.evaluate` that fetches tag name, clickability, `input type`, full `select` option lists (each option's own mmid/text/value/selected), whitelisted attributes (`name, aria-label, placeholder, mmid, id, for, data-testid, role, class, tabindex, href, target`), plus `innerText` for leaf nodes only (`should_fetch_inner_text = 'children' not in node`). Unresolvable nodes get `node["marked_for_deletion_by_mm"] = True` instead of being dropped inline.

**Flow:** cleanup previous injections (`__cleanup_dom` restores `orig-aria-keyshortcuts`, removes `mmid`) → inject mmid+aria-keyshortcuts over `document.querySelectorAll('*')` → `page.accessibility.snapshot(interesting_only=True)` → reconcile each tree node against `[mmid="N"]` in the DOM → mark unmatchable nodes for deletion → prune → serialize `str(enhanced_tree)` (raw and enriched trees are also written to `SOURCE_LOG_FOLDER_PATH/json_accessibility_dom{,_enriched}.json`).
**Invariant:** The mmid attribute is EPHEMERAL session state, not page data: it must be injected fresh before every snapshot and cleaned after, because the numbering restarts at 1 each time — any cached `[mmid='114']` selector from a previous snapshot may point at a different element. The system prompt bakes this in ("You must extract mmid value from the fetched DOM, do not conjure it up", `core/agents/browser_agent.py:47`). `aria-keyshortcuts` was chosen precisely because pages rarely use it; if your target pages DO use it, pick another side-channel attribute.
**Probe:** No dedicated test exists (repo ships no tests). Coverage caveat recorded; deterministic pin: `do_get_accessibility_info` has exactly 3 inbound graph edges — `get_dom_field_func` (fields path, `only_input_fields=True`) → `get_dom_fields` BA tool; `get_dom_with_accessibility_info` (public wrapper, itself uncalled = dead seam kept for parity); plus the fields caller chain pinned by `trace_path --function-name do_get_accessibility_info --direction inbound`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "inject attributes accessibility tree mmid", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the aria-keyshortcuts side-channel trick and the inject→snapshot→reconcile→prune pipeline wholesale — it is the cheapest known bridge between a11y snapshots and live DOM. Adapt the attribute whitelist/tags-to-ignore lists to your product surface. Omit nothing in the ordering: cleaning old injections AFTER reading the new snapshot would corrupt ids mid-flight.
