<!-- capsule-v2 -->
# Enum params as typing.Literal for dynamic pydantic models — why does build_model fail on Literal and how do you fix it at both layers?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your OpenAPI-driven tool builder turns `{"type": "string", "enum": [...]}` into parameter types — how do you carry enums through to pydantic models without `build_model()` crashing, and what does that buy the LLM?

## _python_type_for_schema emits Literal[...]; build_model must ACCEPT Literal annotations (not isinstance-check them as types)
**Path/Symbol:** consumer tests `src/cuga/backend/tools_env/registry/tests/test_enum_handling.py` (whole suite pins the bug class); functions under test: `mcp_manager/adapter.py` — `build_model`, `_python_type_for_schema`, `extract_field_definitions`; parser: `mcp_manager/openapi_parser.py::SimpleOpenAPIParser`.
**Signature:** `_python_type_for_schema(schema) -> type | typing.Literal[...]` (enum ⇒ `Literal[tuple(values)]`, detected via `hasattr(result, '__origin__') and result.__origin__ is Literal`, NOT isinstance); `build_model(name, field_defs: dict[str, tuple[type, default]]) -> type[BaseModel]`.
**Data Shape:** field_defs values are `(annotation, default)` pairs; nested dicts of pairs become dynamically-named sub-models (`{name}Submodel...` naming asserted via `startswith`).

### Decisive source
```python
# test_enum_handling.py:36-60 — the two invariants in one probe
field_defs = {"color": (Literal[("charcoal","red","blue","green","orange","yellow")], None),
              "title": (str, None)}
model = build_model("TestModel", field_defs)          # must NOT raise
annotations = model.__annotations__
assert hasattr(annotations["color"], "__origin__")    # Literal preserved VERBATIM —
assert annotations["title"] == str                    # never flattened to str/int
# :108-178 integration: SimpleOpenAPIParser → extract_field_definitions →
# color/priority come out with __origin__ Literal, then build_model succeeds
```
**Flow:** OpenAPI property with `enum` list → extract_field_definitions asks _python_type_for_schema → Literal type built over the enum VALUES → build_model writes annotations verbatim into a fresh BaseModel subclass → StructuredTool argschema carries the enum so the LLM sees constrained values in tool schema (and validation rejects off-list strings at call time).
**Invariant:** (1) Anywhere build_model inspects annotations with `isinstance(ann, type)` it will MISCLASSIFY Literal (a typing form, not a class) — branch on `__origin__`. (2) Preserve Literal through nesting; flattening an enum param to `str` silently widens the tool's contract and the model starts inventing values. (3) Defaults ride beside the annotation — `Literal` fields with defaults must stay optional-compatible.

**Probe:** `tests/test_enum_handling.py` — `test_python_type_for_schema_with_enum` (:23), `test_build_model_with_literal_types` (:36), `test_build_model_with_mixed_types` (:62), `test_build_model_with_nested_models` (:87), `test_openapi_enum_processing_integration` (:108).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "build_model _python_type_for_schema Literal enum extract_field_definitions", limit: 8 });
```
## Verdict
Adopt for any spec-to-pydantic pipeline: emit Literal for enums and audit every annotation inspection for the isinstance trap. Pairs with schema-type-resolution (ambiguity⇒Any) on the same builder.
