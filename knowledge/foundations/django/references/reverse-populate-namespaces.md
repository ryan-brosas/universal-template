<!-- capsule-v2 -->
# Reverse dictionary build + namespace resolution — how does reverse() walk namespaces and why are patterns populated in REVERSED order?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** How does URL name lookup handle duplicate names and instance namespaces, and what is the recursion guard during lazy population?

## Reversed-population reverse index
**Path/Symbol:** `django/urls/resolvers.py:URLResolver._populate` (545–627) + `django/urls/base.py:reverse` (28–108).
**Signature:** `_populate(self)`; `reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None, *, query=None, fragment=None)`.
**Data Shape:** per-language-code dicts `_reverse_dict/_namespace_dict/_app_dict` keyed by `get_language()`; lookups is a MultiValueDict from callback AND name → `(normalized_bits, pattern, default_args, converters)`; population guarded by thread-local `self._local.populating`.

### Decisive source
```python
if getattr(self._local, "populating", False):
    return                      # re-entrant call in this thread: short-circuit
try:
    self._local.populating = True
    ...
    for url_pattern in reversed(self.url_patterns):   # LAST pattern wins lookups
        if isinstance(url_pattern, URLPattern):
            self._callback_strs.add(url_pattern.lookup_str)
            lookups.appendlist(url_pattern.callback, (...))
            if url_pattern.name is not None:
                lookups.appendlist(url_pattern.name, (...))
        else:
            url_pattern._populate()                    # recursive, same guard
            ...merge child reverse_dict with p_pattern prefix...
finally:
    self._local.populating = False
```
and in `reverse()`: for each `ns` segment — if `current_ns` appears in that app's `app_list`, substitute the INSTANCE namespace; elif the name isn't an instance there either, fall back to `app_list[0]`; missing intermediate namespaces raise `NoReverseMatch("%s is not a registered namespace inside '%s'")`.

**Flow:** lazy populate on first reverse/resolve-error → iterate patterns REVERSED so MultiValueDict.appendlist puts the LAST registered name first in the possibilities list → recursion into includes with a thread-local re-entrancy latch → at reverse time walk `ns:` segments choosing instance-over-app namespaces via current_app.
**Invariant:** (1) Duplicate URL names resolve to the LAST pattern registered (reversed iteration + appendlist head-insertion); forward-order naive ports break existing apps. (2) The populating latch is per-thread (`asgiref.local.Local`) because concurrent threads must EACH complete population while a recursive call inside one thread must bail. (3) Reverse dicts are language-keyed — i18n routes rebuild per active language.
**Probe:** `tests/urlpatterns_reverse/tests.py::URLPatternReverse` (:437), `::ReverseShortcutTests` (:824), `::NamespaceTests` (:886, incl. current_app handling) — direct suites executed green at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "_reverse_with_prefix lookup_view", limit: 10 });
```

## Verdict
Adopt last-wins name registration and the per-thread re-entrancy latch; adapt the language-keying only if you have translated routes; omit app-dict instance fallback if you don't support multiple instances of one app. Direct suites cited executed green at this pin.
