<!-- capsule-v2 -->
# Adapter prefix mount — why must adapters stay sorted longest-prefix-first, and how is dispatch resolved?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** How does a Session choose which transport adapter handles a URL, and what ordering invariant does `mount` maintain?

## Session.mount / Session.get_adapter
**Path/Symbol:** `src/requests/sessions.py:Session.mount` (:888-897), `src/requests/sessions.py:Session.get_adapter` (:870-881), `src/requests/sessions.py:Session.__init__` (:501-503).
**Signature:** `mount(prefix: str, adapter: BaseAdapter) -> None`; `get_adapter(url: str) -> BaseAdapter`.
**Data Shape:** `self.adapters: MutableMapping[str, BaseAdapter]` (OrderedDict). Defaults mounted in order: `https://` then `http://`.

### Decisive source
```python
def mount(self, prefix, adapter):
    self.adapters[prefix] = adapter
    # Adapters are sorted in descending order by prefix length.
    keys_to_move = [k for k in self.adapters if len(k) < len(prefix)]
    for key in keys_to_move:
        self.adapters[key] = self.adapters.pop(key)

def get_adapter(self, url):
    for prefix, adapter in self.adapters.items():
        if url.lower().startswith(prefix.lower()):
            return adapter
    raise InvalidSchema(f"No connection adapters were found for {url!r}")
```

**Flow:** Insert/overwrite prefix → bubble every SHORTER prefix behind it (pop+reinsert moves to end) → iteration order is longest-prefix-first → dispatch is FIRST match wins via case-insensitive `startswith` → no match raises `InvalidSchema`.
**Invariant:** Longest-prefix-wins depends ENTIRELY on insertion-order maintenance, not on any sort call — a porter who appends new adapters naively breaks `s.mount("https://specific.host", custom)` over the default `https://`. Dispatch matches the URL PREFIX textually (scheme + `//host` when present), so mounting `https://api.example.com` routes only URLs starting with exactly that string. Note `get_adapter` lowercases both sides but `mount` does NOT normalize the stored prefix key — mixed-case prefixes still work only because of the `.lower()` at dispatch time.
**Probe:** Direct tests: `tests/test_requests.py::TestRequests::test_session_get_adapter_prefix_matching` (:1685), `_mixed_case` (:1709), `_is_case_insensitive` (:1719), and `test_session_get_adapter_prefix_with_trailing_slash` pin dispatch semantics incl. case handling. `grep -c "keys_to_move" src/requests/sessions.py` → 2 hits (:894, :896).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "mount adapter prefix", limit: 10 });
```
(BM25 surfaces the three test methods rank-1..3; the source method itself resolves via `search_code --pattern 'keys_to_move'` → `Session.mount` :888-897.)

## Verdict
Adopt the reorder-by-length invariant and first-match dispatch. Adapt the mapping type to host conventions (any insertion-ordered mapping works). Omit the InvalidSchema message formatting details.
