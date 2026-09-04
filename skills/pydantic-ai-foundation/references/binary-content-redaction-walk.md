<!-- capsule-v2 -->
# Binary-content redaction walk: path-scoped cycle detection + never-fail wrapper

## Source / Question
`pydantic_ai_slim/pydantic_ai/_instrumentation.py::redact_binary_content/_redact_binary_content` — How do you strip binary payloads from arbitrary tool-return/output/metadata values bound for span attributes, when those values may be self-referential, deeply nested, or hostile to traversal? Porters get two things wrong: treating repeated objects as cycles, and letting redaction exceptions kill the run.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/_instrumentation.py` — `redact_binary_content` (141–167), `_redact_binary_content` (170–217), `CIRCULAR_REFERENCE_PLACEHOLDER = '<circular reference>'` (138). Consumers: `capabilities/instrumentation.py` (final_result :201, metadata :261/:462, tool results :519/:589). Wire vocabulary twin: `_otel_messages.py` BinaryDataPart/BlobPart (78–98, modality only image/audio/video per GenAI spec; UriPart modality omitted for DocumentUrl :53–65).

## Signature
```python
def redact_binary_content(value: Any, settings: InstrumentationSettings) -> object
def _redact_binary_content(value: Any, active: set[int]) -> object  # active = ids on CURRENT path
```
Recognized containers: `BinaryContent | ToolReturn | DeferredToolRequests | Mapping | list | tuple`. Everything else returned as-is (including BinaryContent nested in a USER's own model — left alone deliberately).

## Data Shape
BinaryContent → dict keeping `media_type`, redacted `vendor_metadata`, `kind`, `identifier` — data dropped, metadata kept. ToolReturn → redacted return_value/content/metadata + verbatim `tools` (tool names never binary) + kind. DeferredToolRequests → redacted calls/approvals/metadata (run OUTPUT carries the same deferral metadata the tool's span already redacted). Mapping/list/tuple walked recursively preserving shape.

## Decisive source
Two asymmetric safety rules:
1. **Path-scoped, not global, visited-set** (:180–183): `active.add(identity)` / `finally: active.discard(identity)` — "Tracks the objects on the path currently being walked, not every object seen, so that the same `BinaryContent` appearing twice side by side is redacted twice rather than the second occurrence being mistaken for a cycle." Cycle → `CIRCULAR_REFERENCE_PLACEHOLDER`.
2. **Never-fail wrapper** (:158–167): if `include_binary_content` → return value untouched; else try the walk and on ANY exception return `'Unable to redact binary content: {type(e).__name__}'`. The comment pins both halves: "Instrumentation must not fail an otherwise-successful run", and only the exception TYPE is reported because "its message is user-controlled and can itself embed a `BinaryContent`" — str(e) would leak the very data being excluded. Callers fall back to `str(value)` otherwise, whose BinaryContent repr prints the data too — hence the sentinel string.

## Flow / Invariant
Attribute-bound value → `redact_binary_content(v, settings)` → walk recognized containers depth-first rebuilding them, replacing BinaryContent with metadata-only dicts → emit. Invariants: redaction happens UP FRONT on the Python value (cannot be pushed into BinaryContent's serializer — that serialization is public contract shared with message history and must not depend on instrumentation settings, :142–151); retained-field set here is BinaryContent's own and WIDER than the mime-type-only shape `_convert_binary_to_otel_part` keeps for spec-shaped message parts; a value the walk cannot traverse must degrade to a type-only sentinel, never raise.

## Probe (direct test)
`tests/test_include_binary_content.py`: `test_self_referential_output_is_recorded_without_its_binary` (:434 — asserts the literal `'<circular reference>'` placeholder), `test_output_the_walk_cannot_traverse_does_not_crash_the_run` (:456), `test_the_walks_own_failure_does_not_report_a_binary_carrying_message` (:484 — asserts type-only message), `test_binary_nested_in_a_user_type_is_not_redacted` (:513), `test_redacted_tool_return_keeps_the_tools_it_made_available` (:542), `test_redacted_shapes_keep_every_field_but_the_data` (:573).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --semantic-query '["redact binary content circular reference"]'`

## Verdict
**Adopt** the path-scoped visited-set (correct general-purpose cycle rule for DAG-heavy data) and the never-fail type-only wrapper for any telemetry sink. **Adapt** the recognized-container list and retained fields to your value vocabulary. **Omit** the DeferredToolRequests branch if your framework has no deferral envelope.
