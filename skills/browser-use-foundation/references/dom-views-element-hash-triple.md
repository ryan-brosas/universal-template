<!-- capsule-v2 -->
# Element hash triple — why element_hash, compute_stable_hash, and ax_name exist as three matching levels

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** When replaying history or re-finding an element after reload, which identity key survives dynamic CSS state, and how do the fallbacks cascade?

## SHA-256 over parent-branch-path + STATIC attributes + ax_name
**Path/Symbol:** `browser_use/dom/views.py:EnhancedDOMTreeNode.__hash__` (863-889), `compute_stable_hash` (830-858), `parent_branch_hash` (891), `_get_parent_branch_path` (901); vocabularies `STATIC_ATTRIBUTES` (84-136), `DYNAMIC_CLASS_PATTERNS` (139-162), `filter_dynamic_classes` (175); consumer `DOMInteractedElement.load_from_enhanced_dom_tree` (1023) + `MatchLevel` ladder (165).
**Signature:** `def __hash__(self) -> int` / `def compute_stable_hash(self) -> int` — both `int(hash_hex[:16], 16)`
**Data Shape:** combined string = `'/'.join(parent tags)|''.join(sorted k=v for k in STATIC_ATTRIBUTES)|ax_name=<name>`; stable variant filters class values through `filter_dynamic_classes` and drops empties.

### Decisive source
```python
DYNAMIC_CLASS_PATTERNS = frozenset({'focus','hover','active','selected','disabled','animation',
    'transition','loading','open','closed','expanded','collapsed','visible','hidden',
    'pressed','checked','highlighted','current','entering','leaving'})
def filter_dynamic_classes(class_str):
    classes = class_str.split()
    stable = [c for c in classes if not any(pattern in c.lower() for pattern in DYNAMIC_CLASS_PATTERNS)]
    return ' '.join(sorted(stable))     # sorted => deterministic hashing
...
# Include accessibility name (ax_name) if available - this helps distinguish
# elements that have identical structure and attributes but different visible text
ax_name = f'|ax_name={self.ax_node.name}'
combined_string = f'{parent_branch_path_string}|{attributes_string}{ax_name}'
```

**Flow:** at interaction-save time `load_from_enhanced_dom_tree` snapshots node_id/backend_node_id/frame_id/xpath AND both hashes + ax_name → on replay, matcher tries EXACT hash → STABLE hash (dynamic classes filtered; survives hover/focus/animation class churn) → XPATH → AX_NAME → ATTRIBUTE per `MatchLevel.EXACT..ATTRIBUTE` (values 1-5). XPath generation itself stops at iframe boundaries and passes through shadow roots (`xpath` :492-516).
**Invariant:** class tokens are filtered by SUBSTRING match against lowercase patterns (so `btn-primary-focused` is dropped too) and re-sorted before hashing — omitting the sort makes hashes order-dependent. ax_name participates in BOTH hashes: two structurally identical elements with different visible text hash differently. Hash truncation to 16 hex chars is deliberate (int-sized __hash__ contract).
**Probe:** `tests/ci/test_ax_name_matching.py` (:17 imports MatchLevel/DOMInteractedElement; :245-248 pins AX_NAME=4 < ATTRIBUTE=5 ordering; suite exercises hash→stable→xpath→ax_name cascade end-to-end). EXECUTED GREEN in gate 5 (11 passed incl. this file). Also `filter_dynamic_classes('zebra active mt-4 focus') == filter_dynamic_classes('mt-4 zebra focus active')`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "compute_stable_hash filter_dynamic_classes DOMInteractedElement", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the multi-level identity ladder for any DOM/UI replay engine; adapt the static/dynamic vocabularies to your framework's class conventions; omit MatchLevel.ATTRIBUTE if you have no unique-attribute source.
