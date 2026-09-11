<!-- capsule-v2 -->
# State id guarantee — how does every state shape (dict, BaseModel subclass, instance, generic parameter) end up with an `id` for persistence?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What is the full ladder that turns user-supplied initial state into a persistable keyed state?

## StateWithId mixin + uuid stamping ladder
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow._create_initial_state` :1637–1716, `_create_definition_state` :1718–1741; `FlowState` base :366–375; class-ref round-trip `_serialize_initial_state` :337–366).
**Signature:** `_create_initial_state(self) -> T`.
**Data Shape:** `FlowState.id: str = Field(default_factory=lambda: str(uuid4()))`; `_INITIAL_STATE_CLASS_MARKER = "__crewai_pydantic_class_schema__"`.

### Decisive source
```python
if isinstance(state_type, type):
    if issubclass(state_type, FlowState):
        ...
    if issubclass(state_type, BaseModel):
        class StateWithId(FlowState, state_type):  # type: ignore
            pass
        instance = StateWithId()
        if not getattr(instance, "id", None):
            object.__setattr__(instance, "id", str(uuid4()))
        return cast(T, instance)
    if state_type is dict:
        return cast(T, {"id": str(uuid4())})
...
if isinstance(init_state, BaseModel):
    model = init_state
    if hasattr(model, "id"):
        state_dict = model.model_dump()
        if not state_dict.get("id"):
            state_dict["id"] = str(uuid4())
        ...model_class(**state_dict)...
    class StateWithId(FlowState, type(model)):
        pass
```

**Flow:** no initial_state → extension state → generic `Flow[T]` param (TypeVar ⇒ None) → definition-declared state (pydantic/json_schema ref resolved; failure logs and falls back to dict) → explicit state: classes get id-bearing subclass or `{"id": uuid}`; dict instances are COPIED then stamped; pydantic instances dump-validate with id backfill; models WITHOUT any id field are re-based onto FlowState.
**Invariant:** Persistence requires `state.id` (decorator raises "must have an 'id' field"), so EVERY constructor path must terminate in a stamped id — missing one branch silently breaks resume only at first @persist. Class references serialize as JSON schema under the marker key and rebuild via `create_model_from_schema`; bare non-BaseModel types (e.g. plain `type`) serialize to None deliberately. `object.__setattr__` bypasses frozen/validated models.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_flow_uuid_unstructured" "lib/crewai/tests/test_flow.py::test_flow_uuid_structured" -q` (expect 2 passed); static anchors: `_INITIAL_STATE_CLASS_MARKER` ×4, `class StateWithId` ×3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_create_initial_state FlowState id uuid StateWithId BaseModel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exhaustive per-shape stamping with copy-before-mutate; adapt the mixin approach if your base already reserves an id; omit schema-marker serialization unless you accept class refs in configs. Direct tests executed green at pin.
