<!-- capsule-v2 -->
# KernelArguments merge operators — new-object `|` with RHS-wins; in-place `|=`; per-service_id settings merge

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When two argument bags merge — e.g., caller defaults plus per-call overrides — who wins for values AND for execution settings, and is the merge destructive?

## `__or__` / `__ror__` / `__ior__` on a dict subclass
**Path/Symbol:** `python/semantic_kernel/functions/kernel_arguments.py:KernelArguments.__or__` (60–75), `.__ror__` (77–95), `.__ior__` (97–108), `.dumps` (110–122).
**Signature:** `def __or__(self, value: dict) -> "KernelArguments"` etc. KernelArguments subclasses `dict` but keeps execution settings OUT of the dict, in a parallel `execution_settings: dict[str, PromptExecutionSettings] | None` keyed by service_id (`"default"` when unset).
**Data Shape:** Non-dict operand ⇒ TypeError. Settings lists normalize via `{s.service_id or DEFAULT_SERVICE_NAME: s}`.

### Decisive source
```python
def __or__(self, value):
    if not isinstance(value, dict):
        raise TypeError(...)
    new_execution_settings = (self.execution_settings or {}).copy()
    if isinstance(value, KernelArguments) and value.execution_settings:
        new_execution_settings |= value.execution_settings      # RHS wins per service_id
    return KernelArguments(settings=new_execution_settings, **(dict(self) | dict(value)))  # RHS wins values

def __ror__(self, value):   # dict | ka  -> the KernelArguments side stays authoritative
    ...
    return KernelArguments(settings=new_execution_settings, **(dict(value) | dict(self)))
```

**Flow:** `|` always returns a NEW KernelArguments: plain values merge dict-style with the RIGHT side winning duplicates; settings dicts merge with right-side service_id entries replacing left-side ones; `__ror__` mirrors this so `plain_dict | kernel_args` still lets the KernelArguments side win its own keys/settings. `|=` mutates in place (`self.update(value)` plus settings update) preserving object identity.
**Invariant:** Merging never mixes settings into the value dict (they live on a separate field), and duplicate service_ids resolve to exactly one settings object — the RHS one. `bool()` is True when EITHER values or settings are non-empty, so an empty-looking bag with only settings still counts as configured.
**Probe:** `python/tests/unit/functions/test_kernel_arguments.py::test_kernel_arguments_or_operator` (78–86, cases at 55–76) pins RHS-wins duplicates and shared-service_id overwrite; `::test_kernel_arguments_inplace_merge` (114–124) pins identity preservation under `|=`; `::test_kernel_arguments_ror_operator` (166–174) pins dict-on-left ordering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "KernelArguments __or__ __ror__ execution_settings dumps", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-channel shape (value dict + keyed settings dict) and non-destructive `|` merging whenever hosts layer argument defaults under call-site overrides. Adapt key names/service-id vocabulary to your host; keep RHS-wins so override chains read naturally. Omit the pydantic-aware `dumps` default hook if your telemetry never serializes arbitrary model objects.
