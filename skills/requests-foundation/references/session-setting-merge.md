<!-- capsule-v2 -->
# Session setting merge — how do per-request settings override session defaults without losing dict keys or None-means-delete?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** When merging Request-level settings with Session-level settings, what are the exact precedence rules for scalars, dicts, and None values?

## merge_setting / merge_hooks
**Path/Symbol:** `src/requests/sessions.py:merge_setting` (:76-105), `src/requests/sessions.py:merge_hooks` (:108-124).
**Signature:** `merge_setting(request_setting, session_setting, dict_class=OrderedDict) -> Any`; `merge_hooks(request_hooks, session_hooks, dict_class=OrderedDict)`.
**Data Shape:** Both args may be None, a scalar (e.g. `verify=True`, an auth tuple), or a Mapping. Returns the winner, or a merged `dict_class` instance.

### Decisive source
```python
if session_setting is None:
    return request_setting
if request_setting is None:
    return session_setting
# Bypass if not a dictionary (e.g. verify)
if not (isinstance(session_setting, Mapping) and isinstance(request_setting, Mapping)):
    return request_setting          # request wins for non-dict values
merged = dict_class(to_key_val_list(session_setting))
merged.update(to_key_val_list(request_setting))   # request keys win per-key
none_keys = [k for (k, v) in merged.items() if v is None]
for key in none_keys:
    del merged[key]                 # None value = DELETE that key entirely
```

**Flow:** None-on-either-side → other side wins wholesale → both non-None non-Mapping → request wins → both Mapping → session base, request overlay → strip every key whose final value is None.
**Invariant:** A header set to `None` in either layer is REMOVED from the output rather than sent as `"None"` — this is the documented "headers with None values are not sent" behavior (`tests/test_requests.py::TestRequests::test_headers_on_session_with_None_are_not_sent`). Hooks have a special guard (`merge_hooks`): if EITHER side's `response` list is empty (`[]`), that empty list means "explicitly no hooks" and wins over merging — without this, `{response: []}` at request level would resurrect session hooks.
**Probe:** Direct tests: `tests/test_requests.py::test_headers_on_session_with_None_are_not_sent` (:496, httpbin), `::test_session_hooks_are_overridden_by_request_hooks` (:1211) pins the merge_hooks suppression side. `grep -n "none_keys" src/requests/sessions.py` → 2 lines (:101 comprehension, :103 del).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "merge_setting session setting", limit: 10 });
```

## Verdict
Adopt the four-arm precedence ladder and None-strips-key semantics verbatim — porters routinely send literal "None" headers by skipping the none_keys sweep. Adapt `dict_class` injection if your host uses a different ordered mapping. Omit the Python-2 OrderedDict import dance.
