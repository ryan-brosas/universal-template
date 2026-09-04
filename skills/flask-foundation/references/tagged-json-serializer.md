<!-- capsule-v2 -->
# Tagged JSON serializer — how do non-JSON Python types survive a round-trip through the session cookie?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What is the tagging grammar, and why does registration ORDER matter?

## TaggedJSONSerializer tag/untag walks
**Path/Symbol:** `src/flask/json/tag.py:TaggedJSONSerializer` (219–327) + eight default tags (93–216).
**Signature:** `tag(value) -> tagged`; `untag(value: dict)`; `_untag_scan(value)`; `register(tag_class, force=False, index=None)`; `dumps/loads`.
**Data Shape:** tags keyed by single-char strings with LEADING SPACE (`" t"`, `" b"`, `" m"`, `" u"`, `" d"`, `" di"`); TagDict rewrites the key with TRAILING `__` inside the payload.

### Decisive source
```python
def tag(self, value):
    for tag in self.order:                 # FIRST matching tag wins
        if tag.check(value): return tag.tag(value)
    return value

def _untag_scan(self, value):
    if isinstance(value, dict):
        value = {k: self._untag_scan(v) for k, v in value.items()}  # children first
        value = self.untag(value)          # then the dict itself
    elif isinstance(value, list):
        value = [self._untag_scan(item) for item in value]
    return value
```
TagDict.check matches a 1-key dict whose key IS a registered tag → `to_json` = `{f"{key}__": ...}` so plain user data like `{" t": "not-a-tuple"}` round-trips unchanged (payload key becomes `" t__"`, untag ignores it).

**Flow:** dumps: recursive tag pass (dicts walked by PassDict BEFORE TagTuple can see their items — order list: TagDict, PassDict, TagTuple, PassList, Bytes, Markup, UUID, DateTime) → compact JSON. loads: parse → bottom-up untag scan. Custom tags register with `index=0` when they must precede an existing tag (OrderedDict-before-dict example), `force=True` to replace a key.
**Invariant:** duplicate tag keys raise KeyError without `force`; `untag` only fires on len-1 dicts whose single key is a registered tag; children are always untagged before parents.
**Probe:** `grep -Fc '{f"{key}__": self.serializer.tag(value[key])}' src/flask/json/tag.py` = 1; `grep -Fc 'if len(value) != 1:' src/flask/json/tag.py` = 1; tests `tests/test_json_tag.py::test_dump_load_unchanged` (:27 parametrized incl. ambiguous `{" di": " di"}`), `::test_duplicate_tag` (:32); `tests/test_basic.py::test_session_special_types` (:470).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "TaggedJSONSerializer tag untag session serializer", limit: 8 });
```

## Verdict
Adopt the leading-space tag vocabulary + trailing-`__` escape + child-first untag. Adapt the type set to your domain. Omit nothing — this is also the reference design for any lossless JSON extender.
