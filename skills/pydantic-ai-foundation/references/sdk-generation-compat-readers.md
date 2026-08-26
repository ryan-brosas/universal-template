<!-- capsule-v2 -->
# SDK-generation compat field readers — snake_case read with camelCase fallback and the silent-None trap

## Source / Question
`pydantic_ai_slim/pydantic_ai/_mcp_compat.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Your code reads fields off a vendor SDK model whose v1 generation used camelCase wire names and whose v2 renamed them to snake_case — how do you read either install without forking your code, and what's the failure mode when a field name is misspelled? A porter will branch on import success instead of distribution version and never notice that a wrong spelling reads as None, not an error.

## Path / Symbol
`_mcp_compat.py` — whole module (:1–56): `is_mcp_sdk_v2()` (:14–17), `wire_name()` (:20–23), `mcp_field_value()` (:26–33), `mcp_field()` (:36–40), `mcp_optional_field()` (:43–46), `mcp_validated_field()` (:49–56).

## Signature
```python
def is_mcp_sdk_v2() -> bool:            # regex-reads version('mcp'), >= (2,0,0)
def wire_name(name: str) -> str         # 'input_schema' -> 'inputSchema'
def mcp_field_value(value: BaseModel, name: str) -> object:
    return getattr(value, name if name in type(value).model_fields else wire_name(name), None)
def mcp_validated_field(value: BaseModel, name: str, adapter: TypeAdapter[T]) -> T | None
```

## Data Shape
Generation is detected from the installed DISTRIBUTION VERSION (`importlib.metadata.version('mcp')`), deliberately NOT from module shapes — v2.0.0 re-exported `mcp.types` so class-shape sniffing lies. Readers return `None` when neither spelling exists (field added in a later spec revision is picked up automatically once the SDK catches up).

### Decisive source — the getattr ladder + its documented trap
```python
def mcp_field_value(value: BaseModel, name: str) -> object:
    """Read the MCP model field `name` (snake_case) by whichever spelling the installed SDK uses.

    SDK v2 renamed the wire fields from camelCase to snake_case. A field the installed SDK
    doesn't define reads as `None`, so a field added in a later spec revision is picked up as
    soon as the SDK catches up."""
    return getattr(value, name if name in type(value).model_fields else wire_name(name), None)
```
And the test docstring that pins WHY spelling is load-bearing (`tests/test_mcp.py::test_compat_readers_name_real_sdk_v2_fields` :180): "a wrong snake_case spelling reads as `None` instead of raising — a mistyped `mime_type` would silently drop every media type once the pin widens."

**Flow:** generation gate (`is_mcp_sdk_v2`) decides constructor/wrapper shapes at call sites → every field READ goes through one of the three readers → snake_case preferred, derived camelCase alias fallback, else None → generic types (e.g. `dict[str, Any]`) validate through a TypeAdapter because isinstance can't narrow parameterized generics; required readers assert the expected type loudly.

**Invariant:** Never detect the SDK generation by importing or inspecting `mcp.types`; only the distribution version is a contract. Accept the silent-None semantics for forward-compat fields BUT pin every (class, field) pair the readers touch against real v2 models in tests — that test is the only thing standing between a typo and silently dropped data.

**Probe:** `tests/test_mcp.py` — `test_is_mcp_sdk_v2_reads_the_installed_distribution_version` (:136, parametrized 1.26.0/2.0.0a1/2.0.0/10.0.0 with monkeypatched version), `test_compat_readers_name_real_sdk_v2_fields` (:180, validates against the standalone `mcp-types` package), `test_sdk_v2_image_content_accepts_wire_field_name` (:203).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query '_mcp_compat is_mcp_sdk_v2 wire_name mcp_field_value'
```

## Verdict
**Adopt** version-gated compat + dual-spelling readers for ANY vendored SDK with a breaking rename. **Adopt** the "pin reader targets against the new-generation models in CI" pattern as mandatory compensation for the silent-None design. **Adapt** the field list to your SDK surface. **Omit** nothing — 56 lines, all load-bearing.
