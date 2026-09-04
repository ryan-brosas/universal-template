<!-- capsule-v2 -->
# WebSearch subclass anatomy — named local strategies, native-only constraint fields, and the strategy-resolution UserError ladder

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/web_search.py` (+ twins `x_search.py`, `image_generation.py`) @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does a concrete NativeOrLocalTool subclass declare which config fields REQUIRE the native plane and resolve string strategies like `local='duckduckgo'` into concrete tools? A porter will let constraint fields ride on a local fallback that ignores them.

## Path / Symbol
`web_search.py` — `WebSearch(NativeOrLocalTool)` dataclass(init=False) (:18–123): native-only field docs (:33–49), `_default_native()` kwargs assembly skipping Nones (:81–95), `_native_unique_id → WebSearchTool.kind` (:97–98), `_resolve_local_strategy` duckduckgo import-guard (:100–115), `_requires_native` predicate (:117–123).

## Signature
```python
def _requires_native(self) -> bool:
    return (self.blocked_domains is not None or self.allowed_domains is not None
            or self.max_uses is not None or self.external_web_access is False)
```

## Data Shape
Native-only knobs: search_context_size ('low'|'medium'|'high'), user_location, blocked_domains, allowed_domains, max_uses, external_web_access — all ignored by local fallbacks by design (documented per-field). Strategy literal: `WebSearchLocalStrategy = Literal['duckduckgo']`; `local=True` resolves to 'duckduckgo'.

### Decisive source
The import-guard strategy resolution (:103–111):
```python
if strategy == 'duckduckgo':
    try:
        from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
    except ImportError as e:
        raise UserError("WebSearch(local='duckduckgo') requires the `duckduckgo` optional group — "
                        '`pip install "pydantic-ai-slim[duckduckgo]"`.') from e
    return duckduckgo_search_tool()
raise UserError(f'WebSearch(local={name!r}) is not a known strategy. Supported: ...')
```

**Flow:** Construction walks the base-class ladder (see native-or-local-tool-base): `native=True` builds `WebSearchTool(**{k: v for non-None knobs})`; any constraint field set ⇒ local suppressed + unsupported-model runs raise UserError instead of silently violating constraints; plain `local='duckduckgo'` lazily imports the optional extra with an instructive error naming the pip group. x_search/image_generation repeat the identical shape (their own native tool kinds, unique_id = kind, their own strategies/omissions).

**Invariant:** Constraint-expressing fields MUST route through `_requires_native()` so they can never appear honored while a local fallback actually served the request; unknown strategies fail loudly listing supported names.

**Probe:** `tests/test_capabilities.py` — native_or_local family pins the base mechanics this subclass relies on (:10965–11088); WebSearch-specific construction covered via those shared tests. Coverage caveat: no isolated WebSearch test class; strategy ImportError path pinned indirectly.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'WebSearch _requires_native _resolve_local_strategy duckduckgo'
```

## Verdict
**Adopt** the subclass anatomy: kind-as-unique_id, None-skipping kwargs assembly, lazy-import strategy resolution with pip-group-naming errors, and the constraint→requires-native predicate. **Adapt** strategy names/tools. **Omit** the provider-specific knob set; keep the FIELD-CLASSIFICATION discipline (native-only vs portable) whatever your knobs are.
