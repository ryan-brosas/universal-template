<!-- capsule-v2 -->
# Wrapped-method descriptor binding — how do decorator wrappers keep metadata when accessed as instance methods?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** Why do `@start`-decorated methods need a custom `__get__`, and which attributes must NOT be copied to the bound copy?

## FlowMethod descriptor with copy skip-set
**Path/Symbol:** `lib/crewai/src/crewai/flow/flow_wrappers.py` (`FlowMethod` :48–110, `unwrap` :104–109, `__get__` :112–145; StartMethod/ListenMethod/RouterMethod :148–155).
**Signature:** `__get__(self, instance: Any, owner: type | None = None) -> Self`; `__call__(self, *args: P.args, **kwargs: P.kwargs) -> R`.
**Data Shape:** `_meth` (raw function) + `_instance`; flow attrs preserved by name list: `__human_feedback_config__`, `__conversational_only__`, `__flow_persistence_config__`, `__flow_method_definition__`.

### Decisive source
```python
def __call__(self, *args, **kwargs):
    if self._instance is not None:
        return self._meth(self._instance, *args, **kwargs)
    return self._meth(*args, **kwargs)

def __get__(self, instance, owner=None):
    if instance is None:
        return self
    bound = type(self)(self._meth, instance)
    skip = {
        "_meth", "_instance", "__name__", "__doc__", "__signature__",
        "__self__", "_is_coroutine", "__module__", "__qualname__",
        "__annotations__", "__type_params__", "__wrapped__",
    }
    for attr, value in self.__dict__.items():
        if attr not in skip:
            setattr(bound, attr, value)
```

**Flow:** decorators wrap functions into typed FlowMethod instances carrying definition fragments → class access returns the wrapper itself (metadata inspectable pre-instantiation) → INSTANCE access builds a fresh wrapper bound via `_instance` so `self` is injected at call time → every non-dunder payload attribute (persist config, human-feedback config, DSL fragments) is cloned onto the bound copy.
**Invariant:** The skip-set prevents double-binding artifacts (`__self__` recursion) and keeps identity-sensitive fields per-instance. `functools.update_wrapper(self, meth, updated=[])` preserves name/doc while the explicit `FlowMethodName(self.__name__)` re-type happens once. Router return annotations are read from `_unwrap_function` chains — a porter losing `unwrap()` breaks Literal-based emit inference in `_router.py:37–75`.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow_definition.py::test_flow_definition_fragments_cover_start_listen_and_condition_sugar" "lib/crewai/tests/test_flow_definition.py::test_flow_definition_merges_stacked_listen_router" -q` (expect 2 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "FlowMethod wrapper descriptor __get__ bind instance unwrap metadata", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt bound-copy cloning with an explicit skip-set; adapt attribute lists to your decorator payloads; omit coroutine-marker fallbacks on Python ≥3.10 only. Coverage caveat: no dedicated unit test isolates `__get__` — behavior pinned through definition-building tests.
