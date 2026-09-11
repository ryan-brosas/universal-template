<!-- capsule-v2 -->
# Developer-fixed tool factory params — _UNSET sentinel + functools.partial with an explicit __signature__ excision

## Source / Question
`pydantic_ai_slim/pydantic_ai/common_tools/tavily.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A tool factory takes parameters the DEVELOPER should fix (API key, search depth, domain filters) and others the LLM may set per call — how do bound params vanish from the LLM-facing schema while unbound ones stay settable? The naive `functools.partial` keeps every parameter in the signature, so the schema still exposes fixed params. A porter will ship partial's full signature.

## Path / Symbol
`common_tools/tavily.py` — `_UNSET` sentinel (:21–22), `TavilySearchTool.__call__` (:57–88), `tavily_search_tool` overloads (:91–114) + implementation (:117–181), signature excision (:165–175).

## Signature
```python
_UNSET: Any = object()   # distinguishes "not provided" from None in factory kwargs
def tavily_search_tool(api_key=None, *, client=None, max_results=None,
    search_depth=_UNSET, topic=_UNSET, time_range=_UNSET,
    include_domains=_UNSET, exclude_domains=_UNSET) -> Tool[Any]
```

## Data Shape
`max_results` is ALWAYS developer-controlled (never in the LLM schema — it's a dataclass field on `TavilySearchTool`). Each optional param defaults to `_UNSET`, not None: a developer fixing `time_range=None` must get a BOUND None, not "leave it for the model". Result validation goes through a module-level `TypeAdapter(list[TavilySearchResult])` so vendor dict shapes become typed TypedDicts at the boundary.

### Decisive source — bind-then-excise (:153–175)
```python
if kwargs:
    original = func
    func = partial(func, **kwargs)
    func.__name__ = original.__name__
    func.__qualname__ = original.__qualname__
    # partial with keyword args only updates defaults, not removes params.
    # Set __signature__ explicitly to exclude bound params from the tool schema.
    orig_sig = signature(original)
    func.__signature__ = orig_sig.replace(
        parameters=[p for name, p in orig_sig.parameters.items() if name not in kwargs]
    )
```
Client acquisition ladder: explicit `client=` wins; else `api_key` required or `ValueError` ("Either api_key or client must be provided"). Overloads give type-checkers two disjoint call shapes (`api_key` positional vs `client=` keyword).

**Flow:** developer fixes params → partial binds them → `__signature__` rebuilt WITHOUT those names → schema generation (which introspects the signature) sees only `query` (+ any unbound optionals) → per call, model supplies only visible params.

**Invariant:** Sentinel-default ≠ None-default; bound params are removed from the SIGNATURE, not merely documented away; `__name__`/`__qualname__` preserved so registration metadata stays stable.

**Probe:** `tests/test_tavily.py::test_bound_params_hidden_from_schema` (:185, byte-exact schema snapshot showing only `query`), `test_no_params_bound_exposes_all_in_schema` (:123), `test_factory_with_bound_params` (:100, real network round-trip through FunctionSchema.call), `test_factory_requires_api_key_or_client` (:172).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'tavily_search_tool _UNSET partial __signature__'
```

## Verdict
**Adopt** the `_UNSET` sentinel + partial + explicit-signature-excision trio verbatim for any LLM-tool factory with developer-only knobs. **Adapt** param sets and result TypedDicts per provider; the same pattern is the portable core of exa's four deprecated factories. **Omit** the deprecation wrappers.
