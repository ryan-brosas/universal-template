<!-- capsule-v2 -->
# UserWarning deprecation channel — visible-by-default warnings and one-warning composition for aggregators

## Source / Question
`pydantic_ai_slim/pydantic_ai/_warnings.py` + `common_tools/exa.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A library's `DeprecationWarning`s are invisible by default, so users never see them — and when an aggregator object internally calls the same deprecated factories it wraps, how do you warn ONCE instead of N times? A porter will subclass `DeprecationWarning` (silent in production) or emit a warning storm from the wrapper.

## Path / Symbol
`_warnings.py` — `PydanticAIDeprecationWarning` (:4–10), `CostCalculationFailedWarning` (:13–14), `CostNotFoundWarning` (:17–18); `exa.py` — per-factory `@deprecated(..., category=PydanticAIDeprecationWarning)` (e.g. :275–280), `ExaToolset.__init__` suppression block (:497–514).

## Signature
```python
class PydanticAIDeprecationWarning(UserWarning): ...   # UserWarning = visible by default
def exa_search_tool(...) -> Tool[Any]   # @deprecated(..., category=PydanticAIDeprecationWarning)
class ExaToolset(FunctionToolset):
    def __init__(self, api_key, *, include_search=True, ...) -> None
```

## Data Shape
Three warning classes with deliberate bases: the deprecation channel inherits **UserWarning** ("so that deprecations are visible by default at runtime", citing sethmlarson.dev/deprecations-via-warnings-dont-work-for-python-libraries); the two cost classes inherit bare `Warning` because they're diagnostics, not API-deprecation signals.

### Decisive source — aggregator suppresses its own internal re-warnings (:504–514)
```python
# The per-tool factories are deprecated alongside `ExaToolset`; constructing the toolset already
# warned, so suppress their redundant warnings here.
with warnings.catch_warnings():
    warnings.simplefilter('ignore', PydanticAIDeprecationWarning)
    if include_search:
        tools.append(exa_search_tool(client=client, ...))   # would otherwise warn again
    ...
super().__init__(tools, id=id)
```
Every deprecated surface carries a migration pointer IN the message (`...use the ExaSearch capability from the Pydantic AI Harness (pip install "pydantic-ai-harness[exa]", then from pydantic_ai_harness.exa import ExaSearch)`) plus a module-level TODO(v3) removal note.

**Flow:** user calls deprecated factory → runtime-visible warning names the replacement → aggregator constructor warns once itself → internal factory calls run under a catch_warnings/simplefilter('ignore') scope → user sees exactly one warning per entry point.

**Invariant:** Deprecation visibility must not depend on `-W` flags; an aggregator that internally uses deprecated surfaces must silence ONLY its own category inside the composition scope, never globally.

**Probe:** `tests/test_exa.py::test_exa_toolset_deprecated_emits_single_warning` (:36 — counts exactly 1 PydanticAIDeprecationWarning among records AND asserts all four tools landed), per-factory `pytest.warns(..., match=r'\`exa_*_tool\` is deprecated.*ExaSearch')` (:25–31); `tests/test_dbos.py::test_dbos_agent_construction_warns_deprecated` (:200).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'PydanticAIDeprecationWarning simplefilter ignore deprecated'
```

## Verdict
**Adopt** the UserWarning base rule, category-scoped suppression for internal reuse, replacement-pointer message anatomy, and the count-the-warnings test pattern. **Adapt** class/message wording. **Omit** the exa vendor specifics.
