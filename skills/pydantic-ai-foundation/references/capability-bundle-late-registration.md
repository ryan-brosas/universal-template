<!-- capsule-v2 -->
# Capability bundling without subclassing — live empty toolset, id stamping, decorator registration

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/capability.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you give users a dataclass-style "bundle of instructions + tools + toolsets" capability while keeping late registration (decorators called after construction) working through an agent that wires the toolset in exactly once? A porter will return `None` from `get_toolset()` when the bundle is constructed empty and silently drop every later `@cap.tool`.

## Path / Symbol
`capabilities/capability.py` — `Capability(AbstractCapability)` dataclass(init=False) (:29–328): constructor (:62–102, id-stamping comment :98–101), `get_serialization_name → None` rationale (:104–109), `get_description/get_instructions` (:111–115), `get_toolset` composition ladder (:117–133), `tool_plain`/`tool` overloads delegating to `_function_toolset` (:135–273), `instructions` decorator with 5 overload shapes (:275–328).

## Signature
```python
def get_toolset(self) -> AgentToolset[AgentDepsT] | None:
    # [] → self._function_toolset  (the LIVE, possibly still-empty instance)
    # [x] → x ; [x,y,...] → CombinedToolset(materialized)
```

## Data Shape
Constructor takes keyword-only `instructions, toolsets, tools, id, description, defer_loading`. Static string descriptions are mirrored onto `.description` (instance attr read elsewhere); callable descriptions kept only in `_description` and served via `get_description()`. `_instructions: list[str | SystemPromptFunc]` seeded from `normalize_instructions(instructions)` and appended-to by the decorator.

### Decisive source
The live-toolset return (:122–127):
```python
if not toolsets:
    # Return the live (currently-empty) function toolset rather than `None` so tools
    # registered after construction via `@tool`/`@tool_plain` still surface: the agent
    # wires in this reference once, and `None` would drop it and hide late additions.
    return self._function_toolset
```

**Flow:** Construction stamps the capability's `id` onto its contributed FunctionToolset (durable execution wraps leaf toolsets by id at construction time); user-provided `toolsets=` keep their own ids and are never overwritten. `get_toolset()` materializes non-AbstractToolset entries as `DynamicToolset(toolset_func=...)` before combining. Decorators (`@cap.tool`, `@cap.tool_plain`) delegate to the SAME `_function_toolset` instance with the full Agent-parity parameter surface (retries/prepare/args_validator/docstring_format/schema_generator/strict/sequential/requires_approval/metadata/timeout/defer_loading/include_return_schema), so registration order relative to `Agent(...)` construction doesn't matter. `@cap.instructions` accepts ctx-or-no-arg × sync-or-async functions and appends to static instructions; serialization name is None because function tools/instructions/callable descriptions can't round-trip YAML/JSON specs.

**Invariant:** One identity per bundle: the FunctionToolset handed to the agent must be the same object later mutated by decorators — never rebuild or filter it in `get_toolset()`.

**Probe:** `tests/test_capabilities.py` — `test_deferred_capability_tool_registered_after_construction_defers_until_load` (:4100 — post-construction registration surfaces through the wired-in reference), spec-schema assertions pinning `Capability.get_serialization_name() is None` behavior around :1739; e2e `test_deferred_capability_loads_instructions_and_tools_e2e` (:3607).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'Capability get_toolset FunctionToolset instructions decorator'
```

## Verdict
**Adopt** the live-empty-toolset return, id stamping on synthesized (not user-supplied) toolsets, and the decorator-delegates-to-one-toolset pattern. **Adapt** the overload set to your host's tool parameter surface. **Omit** the spec-serialization commentary if your host has no YAML/JSON capability specs.
