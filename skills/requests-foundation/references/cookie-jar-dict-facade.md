<!-- capsule-v2 -->
# RequestsCookieJar dict facade — which operations are O(n), how does None-deletion work, and what makes it picklable?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What are the collision/conflict semantics of the dict interface over a stdlib CookieJar?

## RequestsCookieJar
**Path/Symbol:** `src/requests/cookies.py:RequestsCookieJar` (:191-476); helpers `_find` (:401-421), `_find_no_duplicates` (:423-452), `remove_cookie_by_name` (:164-182).
**Signature:** `class RequestsCookieJar(CookieJar, MutableMapping[str, str | None])`.
**Data Shape:** Real storage stays CookieJar's internal cookie list; every "dict" op is an O(n) scan. Optional domain/path kwargs disambiguate same-name cookies.

### Decisive source
```python
def set(self, name, value, **kwargs):
    # support client code that unsets cookies by assignment of a None value:
    if value is None:
        remove_cookie_by_name(self, name,
                              domain=kwargs.get("domain"), path=kwargs.get("path"))
        return
    ...
def _find_no_duplicates(self, name, domain=None, path=None):
    toReturn = None
    for cookie in iter(self):
        if cookie.name == name and (domain is None or cookie.domain == domain) \
                and (path is None or cookie.path == path):
            if toReturn is not None:
                raise CookieConflictError(f"There are multiple cookies with name, {name!r}")
            toReturn = cookie.value
def __getstate__(self):
    state = self.__dict__.copy()
    state.pop("_cookies_lock")          # RLock is unpickleable — drop it
    return state
```

**Flow:** get/`__getitem__` → `_find_no_duplicates` raises CookieConflictError on ambiguity (get() swallows to default; `__contains__` converts conflict to True) → set with None deletes by name/domain/path via jar.clear triples → set_cookie unwraps DQUOTED values (`value.replace('\\"', "")`) before storing.
**Invariant:** requests itself never uses this dict interface internally (docstring says so) — it exists purely for client compatibility, so porters may keep their native jar and expose a similar facade. Pickling requires dropping `_cookies_lock` in `__getstate__` and re-creating the RLock in `__setstate__` when absent — omitting either half breaks threads or unpickles without locks. `create_cookie` defaults (`domain=""`, `path="/"`, `discard=True`, `rest={"HttpOnly": None}`) make dict-set cookies "supercookies" sent everywhere until a server-scoped cookie replaces them.
**Probe:** Direct tests: `tests/test_requests.py::test_cookie_quote_wrapped` (:406), `::test_request_cookies_not_persisted` (:425), `::test_generic_cookiejar_works` (:431), `::test_cookielib_cookiejar_on_redirect` (:450); `tests/test_utils.py::test_add_dict_to_cookiejar`. `grep -c "_cookies_lock" src/requests/cookies.py` → 3 hits (pop :458, restore :464-465, threading import).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "RequestsCookieJar _find_no_duplicates", limit: 10 });
```

## Verdict
Adopt conflict-vs-default semantics and None-means-unset; adopt the pickle dance only if host needs pickled jars. Adapt supercookie defaults consciously (security posture decision). Omit iterkeys/itervalues py2-era aliases unless clients need them.
