<!-- capsule-v2 -->
# Native-tool registry: auto-registration + discriminated union

## Source / Question
`pydantic_ai_slim/pydantic_ai/native_tools/__init__.py` — How does pydantic-ai register native tool classes and expose them as a pydantic discriminated union so they can ride in `ModelRequestParameters`? A porter must know the `__init_subclass__` registry and the `unique_id`/`optional` semantics.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/native_tools/__init__.py` — `NATIVE_TOOL_TYPES` (35), `AbstractNativeTool` (70–~125), `__init_subclass__` (107–110), `__get_pydantic_core_schema__` (112–125), `unique_id` (89–96), `optional` (80–88), `SUPPORTED_NATIVE_TOOLS` (767), `NATIVE_TOOLS_REQUIRING_CONFIG` (770).

## Signature
```python
NATIVE_TOOL_TYPES: dict[str, type[AbstractNativeTool]] = {}
class AbstractNativeTool(ABC):
    kind: str = 'unknown_native_tool'
    optional: bool = False
    def __init_subclass__(cls, **kwargs): NATIVE_TOOL_TYPES[cls.kind] = cls
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, handler) -> core_schema.CoreSchema
```

## Data Shape
`NATIVE_TOOL_TYPES` maps `kind` string → tool class, populated automatically at class-definition time. `SUPPORTED_NATIVE_TOOLS = frozenset(NATIVE_TOOL_TYPES.values())`. `NATIVE_TOOLS_REQUIRING_CONFIG` = tools needing external config. `unique_id` defaults to `kind` (subclasses override to distinguish multiple instances of the same tool).

## Decisive source
`__init_subclass__` (107–110) auto-registers every concrete subclass into `NATIVE_TOOL_TYPES[cls.kind]`. `__get_pydantic_core_schema__` (112–125): for the abstract base, builds a `pydantic.Discriminator(_tool_discriminator)`-tagged `Union` of all registered tool types (`Annotated[tool, pydantic.Tag(tool.kind)]`), so a `NativeTool`/`ModelRequestParameters.native_tools` field can deserialize any registered native tool by its `kind` discriminator.

## Flow / Invariant
1. **Auto-registration**: adding a native tool = subclass `AbstractNativeTool` + set `kind`; no manual registry edit. `NATIVE_TOOL_TYPES`/`SUPPORTED_NATIVE_TOOLS` stay in sync automatically.
2. **Discriminator**: the pydantic union is keyed on `kind` via `pydantic.Discriminator(_tool_discriminator)`, so serialization round-trips by kind string.
3. **`unique_id`**: defaults to `kind`; override to distinguish multiple instances of the same native tool passed to the model (e.g. two web-search tools with different scopes).
4. **`optional` semantics**: `True` = best-effort upgrade — silently dropped on a model that doesn't support it natively when no local fallback exists; `False` = hard requirement — the request ERRORS on a model that can't honor it (fail loudly rather than silently substituting different behavior). A test pins that one `optional` instance doesn't excuse another sharing its `unique_id`.
5. **`NATIVE_TOOLS_REQUIRING_CONFIG`** = the subset needing external config; used to gate which tools can be offered.

## Probe (direct test)
`tests/test_builtin_tools.py` (12 tests): `WebSearchTool` registry/discriminator usage (:18/:26/:82/:87), `unique_id`/`optional` interaction (:124–130), `supported_native_tools` profile gating (:166), multi-tool `native_tools=[WebSearchTool(), CodeExecutionTool()]` (:173). Also `tests/test_native_output_schema.py` for the native-output variant.

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'NATIVE_TOOL_TYPES AbstractNativeTool'` → `native_tools/__init__.py` `AbstractNativeTool` (70–125), `__init_subclass__` (107–110).

## Verdict
**Adopt** the `__init_subclass__` auto-registry + pydantic discriminated-union pattern — a clean way to make a polymorphic tool family extensible and wire-serializable without a central registry edit. **Adapt** the discriminator field to your schema framework.
