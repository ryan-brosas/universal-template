<!-- capsule-v2 -->
# element-attr-dual-plane — how Element forwards attribute access to HTML without losing Python state

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** What is the exact rule separating `elem.href` (HTML attr) from `elem._tab` (python field), and how are attrs parsed?

## Leading underscore = python; everything else = ContraDict attrs
**Path/Symbol:** `zendriver/core/element.py:Element.__setattr__` (:227-236), `__getattr__` (:193-202, deprecated), `_make_attrs` (:1169-1179); `zendriver/core/_contradict.py:ContraDict` (:14-58).
**Signature:** `def __setattr__(self, key: str, value: Any) -> None`; factory `create(node, tab, tree=None) -> Element`.
**Data Shape:** CDP nodes carry attributes as a flat list `["href", "https://...", "class", "btn", ...]`; `_make_attrs` pairs them into a ContraDict, renaming `class`→`class_`.

### Decisive source
```python
def __setattr__(self, key: str, value: typing.Any) -> None:
    if key[0] != "_":
        if key[1:] not in vars(self).keys():
            # we probably deal with an attribute of
            # the html element, so forward it
            self.attrs.__setattr__(key, value)
            return
    super().__setattr__(key, value)

def _make_attrs(self) -> None:
    sav = None
    if self.node.attributes:
        for i, a in enumerate(self.node.attributes):
            if i == 0 or i % 2 == 0:
                if a == "class":
                    a = "class_"
                sav = a
            else:
                if sav:
                    self.attrs[sav] = a
```

**Flow:** writes: underscore-prefixed keys and known instance fields go to the object; anything else is stored in `self.attrs`. Reads: `__getattr__` (deprecated) falls back to `attrs`, returning `None` instead of raising. ContraDict makes every dict key addressable as an attribute (`o.x == o['x']`) by aliasing `__dict__` to itself (`super().__setattr__("__dict__", self)` :41) and recursively wrapping nested mappings/lists; method-name collisions (`items`, `keys`, ...) stay reachable only via `[...]` lookup with an opt-in warning (`silent=True` at both call sites suppresses it).
**Invariant:** `update()` clears and rebuilds attrs from the refreshed node (:317-318), so stale attribute reads after DOM mutation are prevented only by calling update — Element never auto-syncs. And equality is `backend_node_id`-based (:1181-1188), not attr-based.
**Probe:** direct test pins attribute round-trip via `tests/core/test_tab.py::test_set_user_agent_sets_navigator_values` (page-level) and React fixture assertions reading `.value`; static anchor: `grep -c 'HTMLInputElement.prototype' zendriver/core/element.py` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "ContraDict attribute dict", limit: 5 });
```

## Verdict
Adopt the underscore rule + flat-list pairing + class_ rename exactly (subtle breakage otherwise); adapt ContraDict's warning list to your method surface; omit the deprecated `__getattr__` shim in new APIs — keep explicit `.get()`.
