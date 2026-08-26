<!-- capsule-v2 -->
# resumption-context-versioned-envelope — What exactly must be serialized so a paused workflow can resume in another process?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How is pause-state persisted without losing entity type, runtime state, or stream-filter state?

## Discriminated-union envelope with version field and optional new fields
**Path/Symbol:** `api/core/app/layers/pause_state_persist_layer.py:WorkflowResumptionContext` (:39-66), wrapper models (:23-36); written by `PauseStatePersistenceLayer.on_event` (:117-164).
**Signature:** `dumps() -> str` / `loads(value) -> Self` (pydantic JSON); `get_generate_entity() -> WorkflowAppGenerateEntity | AdvancedChatAppGenerateEntity`.
**Data Shape:** `version: Literal["1"]`; `generate_entity` = Annotated union discriminated on `type` (AppMode.WORKFLOW / ADVANCED_CHAT literal wrappers); `serialized_graph_runtime_state: str`; `serialized_response_stream_filter_state: str | None` — optional because it was added later.

### Decisive source
```python
class WorkflowResumptionContext(BaseModel):
    """WorkflowResumptionContext captures all state necessary for resumption."""
    version: Literal["1"] = "1"
    generate_entity: _GenerateEntityUnion
    serialized_graph_runtime_state: str
    # Optional so that a workflow run paused before this field existed still
    # loads: it just degrades to fresh-filter behavior on resume for that one
    # stale run.
    serialized_response_stream_filter_state: str | None = None

    def get_response_stream_filter(self) -> ResponseStreamFilter:
        response_stream_filter = ResponseStreamFilter()
        if self.serialized_response_stream_filter_state is not None:
            response_stream_filter.loads(self.serialized_response_stream_filter_state)
        return response_stream_filter
```

**Flow:** engine emits GraphRunPausedEvent → layer wraps the generate entity in the matching literal-type wrapper (discriminator survives JSON round-trip) → dumps graph runtime state + filter state → repository persists against the run id read from the variable pool's system variables. Resume path: `loads()` → discriminator rebuilds the right entity class → optional missing filter state degrades to a fresh filter.
**Invariant:** The envelope is versioned from day one (`Literal["1"]`) so future formats can branch; NEW fields must be Optional-with-default or old paused runs fail to load (the comment pins this contract); the entity union is closed — adding an app kind means adding a wrapper + extending the union, never bare dicts.
**Probe:** `grep -c 'state_owner_user_id' core/app/layers/pause_state_persist_layer.py` → 5; `grep -c 'serialized_response_stream_filter_state' …` → 4; direct test `tests/unit_tests/core/app/layers/test_pause_state_persist_layer.py::test_workflow_resumption_context_dumps_loads_roundtrip`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "WorkflowResumptionContext resumption generate entity wrapper discriminator", limit: 10 });
```

## Verdict
Adopt the versioned discriminated-envelope pattern and the "new fields must be optional" evolution rule. Adapt the entity union contents and what counts as resumable state. Omit the Dify-specific pause-reason enrichment that rides alongside (that layer is app-side).
