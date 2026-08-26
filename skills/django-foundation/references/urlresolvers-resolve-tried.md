<!-- capsule-v2 -->
# URLResolver resolve + tried-path ledger — how does the resolver decide between nested matches and build the Resolver404 diagnostic?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** When multiple patterns could consume a path, which wins, what happens to captured kwargs across include() boundaries, and where does the famous "tried these patterns" list come from?

## Depth-first resolution with tried-ledger
**Path/Symbol:** `django/urls/resolvers.py:URLResolver.resolve` (670–717) with `_extend_tried` (650–655), `_join_route` (657–663), and `ResolverMatch` arg-merge semantics (34–105).
**Signature:** `resolve(self, path) -> ResolverMatch` or raises `Resolver404({"tried": [...], "path": ...})`.
**Data Shape:** `tried` accumulates one entry per candidate: `[pattern]` for failed endpoints, `[pattern, *sub_tried]` for failed subtrees; kwargs merge order outer→inner: `{outer_kwargs, **default_kwargs}` then `.update(sub_match.kwargs)`.

### Decisive source
```python
match = self.pattern.match(path)
if match:
    new_path, args, kwargs = match
    for pattern in self.url_patterns:
        try:
            sub_match = pattern.resolve(new_path)
        except Resolver404 as e:
            self._extend_tried(tried, pattern, e.args[0].get("tried"))
        else:
            if sub_match:
                sub_match_dict = {**kwargs, **self.default_kwargs}
                sub_match_dict.update(sub_match.kwargs)   # inner wins
                sub_match_args = sub_match.args
                if not sub_match_dict:
                    sub_match_args = args + sub_match.args
                ...
                return ResolverMatch(
                    sub_match.func, sub_match_args, sub_match_dict,
                    sub_match.url_name,
                    [self.app_name, *sub_match.app_names],
                    [self.namespace, *sub_match.namespaces],
                    self._join_route(current_route, sub_match.route),
                    tried, ...)
            tried.append([pattern])
    raise Resolver404({"tried": tried, "path": new_path})
raise Resolver404({"path": path})
```

**Flow:** prefix-match own pattern → iterate children IN ORDER → first successful subtree returns immediately (depth-first, first-wins) → each failure appends to `tried` (nested failures splice their child's ledger) → exhausted ⇒ raise carrying the full ledger for the debug 404 page.
**Invariant:** (1) First match in urlpatterns order wins; later duplicates never shadow it. (2) Named groups beat positional ones GLOBALLY: if any kwargs exist anywhere on the chain (`if not sub_match_dict`), positional args from outer prefixes are DISCARDED — mixing `<int:pk>` style captures with positional groups silently drops the positionals. (3) Inner kwargs override outer/default_kwargs at every include level. (4) Namespaces concatenate outermost-first into `namespace:path` view names.
**Probe:** `tests/urlpatterns/tests.py` + `tests/urlpatterns_reverse/tests.py::IncludeTests` (:1756) — direct suites pinning include() nesting, kwarg merging, and converter behavior; Resolver404 tried-list rendering is exercised by `tests/view_tests/tests/test_debug.py` (DebugViewTests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "URLResolver resolve Resolver404 tried", limit: 10 });
```

## Verdict
Adopt first-wins ordered matching plus the tried-ledger error shape (it is what makes Django's 404 debug page useful); adapt pattern grammar freely; be careful porting invariant (2) — most naive re-implementations keep both args and kwargs. Direct test modules cited executed green at this pin.
