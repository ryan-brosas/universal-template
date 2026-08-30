<!-- capsule-v2 -->
# Declarative method recovery from model fields — how can a YAML-declared flow lose a wrapped method to pydantic, and how is it recovered?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What happens when a flow method's NAME collides with a Flow base model field, and why does the definition builder scan `model_fields`?

## Field-default recovery sweep
**Path/Symbol:** `lib/crewai/src/crewai/flow/dsl/_utils.py` (`_iter_flow_methods` :393–440, recovery tail :431–439).
**Signature:** `_iter_flow_methods(flow_class: type) -> dict[str, Any]`.
**Data Shape:** returns ordered dict name → wrapper; sources: own namespace → inherited conversational-only methods (MRO-reversed) → recovered field defaults.

### Decisive source
```python
# A wrapped method whose name collides with a base Flow model field
# (e.g. ``checkpoint``) is absorbed by Pydantic as a field; the underlying
# function is preserved as the field default. Recover those so the
# definition still reflects every method once the class is built.
for field_name, field in getattr(flow_class, "model_fields", {}).items():
    if field_name in methods or field_name.startswith("_"):
        continue
    default = getattr(field, "default", None)
    if is_flow_method(default) and _should_include_flow_method(
        flow_class, default
    ):
        methods[field_name] = default
```

**Flow:** normal discovery walks `flow_class.__dict__` for FlowMethod wrappers and conversational-inherited callables → THEN any model FIELD whose default is itself a FlowMethod is treated as an absorbed method and re-registered under the field's name → validation errors during definition build are re-raised as plain ValueError with the first error message stripped of its "Value error, " prefix (`_flow_definition_validation_error` :443–456).
**Invariant:** Recovery is additive and last — explicit namespace methods always win over field defaults. The canonical collision is `checkpoint`: adding checkpointing fields to Flow silently swallowed user methods named `checkpoint` until this sweep existed. Porters who skip the sweep will ship flows whose definitions are missing methods with no error at build time.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow_definition.py::test_flow_definition_maps_dsl_to_static_contract" "lib/crewai/tests/test_flow_resumability_regression.py::test_conditional_start_with_resumption" -q` (expect 2 passed); static anchor: `grep -c "is_flow_method(default)" lib/crewai/src/crewai/flow/dsl/_utils.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_iter_flow_methods inherited conversational wrapped method field default recovery", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the post-sweep recovery pass whenever your model absorbs attributes; adapt naming rules to your field vocabulary; omit conversational inheritance if you have no mixin-based flows. Direct tests executed green at pin.
