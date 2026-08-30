<!-- capsule-v2 -->
# Capability spec-loading context — ContextVar registry inheritance for nested from_spec

## Source / Question
`pydantic_ai_slim/pydantic_ai/agent/spec.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a YAML-declared wrapper capability (e.g. PrefixTools) must construct a NESTED capability from its own spec argument, how does the nested load see the outer call's custom-type registry and template context instead of falling back to defaults? A porter will re-resolve the registry per capability and silently drop custom nested types.

## Path / Symbol
`agent/spec.py` — `AgentSpec(BaseModel)` (:33–246), `capability_spec_context: ContextVar[CapabilitySpecContext | None]` (:303), `CapabilitySpecContext` (:287–300), `load_capability_from_nested_spec()` (:306–336), `get_capability_registry()` (:263–284), `_capabilities_from_spec()` in `agent/__init__.py` (:4059–4091).

## Signature
```python
capability_spec_context: ContextVar['CapabilitySpecContext | None'] = ContextVar(..., default=None)

def load_capability_from_nested_spec(spec: CapabilitySpec | dict | str) -> AbstractCapability:
    cap_spec = spec if isinstance(spec, CapabilitySpec) else CapabilitySpec.model_validate(spec)
    ctx = capability_spec_context.get()
    if ctx is not None:
        return load_from_registry(ctx.registry, cap_spec, label='capability',
                                  custom_types_param='custom_capability_types', instantiate=ctx.instantiate)
    # outside any spec load: default registry, plain cls.from_spec(*args, **kwargs)
```

## Data Shape
`CapabilitySpecContext(registry: Mapping[str, type], instantiate: Callable[[type, tuple, dict], AbstractCapability])`. The agent-side `_capabilities_from_spec` builds the registry once (custom types validated as dataclass subclasses of AbstractCapability), wraps `validate_from_spec_args` + `cap_cls.from_spec(*args, **kwargs)` into `_instantiate_cap`, sets the ContextVar for the duration of the loop, and resets it in `finally`.

### Decisive source — the set/reset bracket (agent/__init__.py :4080–4091)
```python
# Set context so nested from_spec calls (e.g. PrefixTools) can reuse the registry
ctx = _agent_spec.CapabilitySpecContext(registry=registry, instantiate=_instantiate_cap)
token = _agent_spec.capability_spec_context.set(ctx)
try:
    capabilities: list[AbstractCapability[Any]] = []
    for cap_spec in spec.capabilities:
        capability = load_from_registry(registry, cap_spec, label='capability',
                                        custom_types_param='custom_capability_types',
                                        instantiate=_instantiate_cap)
        capabilities.append(capability)
    return capabilities
finally:
    _agent_spec.capability_spec_context.reset(token)
```

**Flow:** Agent.from_spec → build registry → set ContextVar → each top-level CapabilitySpec loads through the SAME registry/instantiate pair; when a loaded wrapper's own `from_spec` hits a nested spec field it calls `load_capability_from_nested_spec`, which finds the ContextVar populated and inherits everything. Outside a load (programmatic construction) the ContextVar is None and the default-registry path applies.

**Invariant:** The reset MUST be in finally — a raise mid-load must not leak the registry into unrelated code on the same task. Nested loads reuse the OUTER registry identity (same object), so custom types registered once apply at every depth. Template validation (`validate_from_spec_args`) rides along inside `instantiate`, so nested specs get template-context checking too.

**Probe:** `tests/test_agent.py::test_from_spec_preserves_zero_retry_budgets` (:13334) pins from_spec override semantics; capability-spec round-trips exercised via `tests/test_capabilities.py`; `test_public_interface_contracts.py` guards the exported surface.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'capability_spec_context CapabilitySpecContext load_capability_from_nested_spec'
```

## Verdict
**Adopt** the ContextVar-scoped registry inheritance for ANY recursive plugin loader. **Adopt** the default-registry fallback so the same helper works both inside and outside a load. **Adapt** the instantiate callback to your construction pipeline (template validation, DI). **Omit** the JSON-schema generation plane of AgentSpec (editor tooling surface).
