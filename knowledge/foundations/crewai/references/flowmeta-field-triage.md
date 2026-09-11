<!-- capsule-v2 -->
# FlowMeta field-annotation triage — how does a metaclass let one class hold pydantic state fields, ClassVar constants, AND undecorated flow methods?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What annotation rules stop plain attributes and helper methods from colliding inside a BaseModel-based Flow?

## Namespace walk with parent-field and wrapper carve-outs
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`FlowMeta.__new__` :381–431; `Flow.model_config` :434–442 with `ignored_types=(StartMethod, ListenMethod, RouterMethod)`).
**Signature:** `FlowMeta.__new__(mcs, name, bases, namespace, **kwargs) -> type` over `ModelMetaclass`.
**Data Shape:** `_skip_types = (classmethod, staticmethod, property)`; three namespace buckets: annotated / underscore-prefixed / bare.

### Decisive source
```python
for attr_name, attr_value in list(namespace.items()):
    if attr_name in annotations or attr_name.startswith("_"):
        continue
    if attr_name in parent_fields:
        annotations[attr_name] = Any
        if isinstance(attr_value, BaseModel):
            namespace[attr_name] = Field(
                default_factory=lambda v=attr_value: v, exclude=True
            )
        continue
    if callable(attr_value) or isinstance(
        attr_value, (*_skip_types, FlowMethod)
    ):
        continue
    annotations[attr_name] = ClassVar[type(attr_value)]
```

**Flow:** inherited non-Model bases get their annotations re-stamped `ClassVar` so plain-class mixins don't become fields → properties shadowing base annotations likewise become ClassVar → bare attrs: already-annotated or `_`-prefixed are untouched; names COLLIDING WITH PARENT MODEL FIELDS become `Any`-annotated (BaseModel values wrapped as excluded default_factory so each instance shares-but-excludes); callables/properties/FlowMethod wrappers are left as methods; anything else is typed `ClassVar[type]`.
**Invariant:** The `lambda v=attr_value:` default-arg freeze is load-bearing — a naive closure would share ONE mutable instance across all instances of the class. Undecorated methods survive because they're callable; decorated ones survive because FlowMethod instances match the isinstance arm and the model ignores them. Definition building stays LAZY (`_flow_definition` built on first `flow_definition()` access :483–491) — eager parsing at import was the old cost.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_flow_with_custom_state" "lib/crewai/tests/test_flow_definition.py::test_flow_public_exports_are_explicit" -q` (expect 2 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "FlowMeta metaclass annotations ClassVar parent fields flow methods", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the triage order (explicit > underscore > parent-collision > callable > ClassVar) and frozen-default exclusion; adapt for dataclass hosts via `__set_name__`; omit lazy definition caching for tiny CLIs. Direct tests executed green at pin.
