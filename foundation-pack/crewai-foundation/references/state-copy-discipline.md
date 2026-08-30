<!-- capsule-v2 -->
# State copy discipline — deep-copy-with-fallback for unpickleable objects and model-construct rescue

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How does flow state get snapshotted for events/persistence when it holds locks, generators, or otherwise unserializable values — without killing the run?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` — `_copy_state` (:1743), `_copy_and_serialize_state` (:3038), `_build_definition_state_model` (:186), `_create_initial_state` (:1637).
**Signature:** `_copy_state() -> T`; `_copy_and_serialize_state() -> dict[str, Any]`.
**Data Shape:** state = dict OR BaseModel subclass (FlowState mixin injects `id`); every MethodExecutionStarted/Finished event embeds a FULL serialized snapshot.

### Decisive source
```python
# :3038 serialize with graceful degradation
state_copy = self._copy_state()
if isinstance(state_copy, BaseModel):
    try:
        return state_copy.model_dump(mode="json")
    except Exception:
        return state_copy.model_dump()
else:
    return state_copy

# :227 definition-state rescue — missing-field ValidationErrors are tolerated
try:
    return model_class(**kwargs)
except ValidationError as e:
    if any(error.get("type") != "missing" for error in e.errors()):
        raise                      # real errors propagate
    return model_class.model_construct(**kwargs)   # bypass validators
```

**Flow:** each method boundary → `_copy_state` deep-copies (dict via deepcopy fallback ladder; pydantic via `model_copy(deep=True)` path) so later mutation can't corrupt emitted snapshots → serialize JSON-mode; on serialization failure fall back to python-mode dump rather than raising → snapshots ride events AND persistence writes. Unstructured dict states keep arbitrary values; structured states get FlowState-mixin `id` stamped (`_stamp_state_id`).
**Invariant:** Event payloads must be IMMUNE to post-emission state mutation (hence copy-before-serialize) but must NEVER crash the run over an unpickleable field (hence two-tier dump). The missing-only ValidationError carve-out lets declarative flows start with partial defaults without masking genuine type errors.
**Probe:** direct suites: `/tmp/crewai-p1-venv/bin/python -m pytest tests/test_flow.py -k 'copy_state' tests/test_flow_resumability_regression.py -q -p no:xdist -o addopts=''` → `8 passed`.
**Direct test:** `tests/test_flow.py::test_flow_copy_state_with_unpickleable_objects` (:1705), `::test_flow_copy_state_with_nested_unpickleable_objects` (:1733), `::test_flow_copy_state_with_dict_state` (:1794).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_copy_and_serialize_state model_dump snapshot", limit: 5 });
// → ext-crewAI...flow.runtime.Flow._copy_and_serialize_state Method 3038+
```

## Verdict
Adopt copy-before-snapshot + degrade-don't-crash serialization + missing-only validator carve-out. Adapt your state container. Omit crewai's json-schema state-ref resolution unless porting declarative flows.
