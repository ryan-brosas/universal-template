<!-- capsule-v2 -->
# NativeOrLocalTool base class — provider-adaptive tool pairing with the config-validation ladder and unless_native exclusion stamping

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/native_or_local.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When one logical capability exists as both a provider-native tool and a local fallback, how do you resolve the `native=`/`local=` configuration matrix at construction time so no combination yields a silent no-op or a silent constraint violation? A porter will let `native=False, local=None` construct successfully and ship a capability that contributes nothing.

## Path / Symbol
`capabilities/native_or_local.py` — `NativeOrLocalTool(AbstractCapability)` dataclass(init=False) (:17–195): both-False guard (:76–78), native=True → `_default_native()` resolution (:81–88), local resolution ladder None/True|str/False/callable→Tool (:90–98), constraint-check-precedes-no-local check (:100–104), native=False-without-local guard (:106–111), subclass hooks `_default_native/_native_unique_id/_default_local/_resolve_local_strategy/_requires_native` (:113–160), `get_native_tools` (:164–169), `get_toolset` with `_add_unless_native` PreparedToolset (:171–195).

## Signature
```python
def __post_init__(self) -> None   # resolves bool/string locals into concrete Tool | AbstractToolset
def get_toolset(self) -> AbstractToolset[AgentDepsT] | None
```

## Data Shape
`native: AgentNativeTool | bool` (True = subclass default, False = force local); `local: str | Tool | Callable | AbstractToolset | bool | None`. After `__post_init__`, native is always an instance (or False) and local is always Tool/AbstractToolset/False/None. Bare callables are wrapped `Tool(local)`; wrapped leaf FunctionToolsets carry `id=self.id` so durable execution can wrap by id; user-supplied AbstractToolsets keep their own id and are never overwritten (:176–184).

### Decisive source
The validation ladder ordering (:100–111):
```python
# Catch contradictory config: native disabled but constraint fields require it.
# Checked first because adding `local=` can't fix it — the user needs to either drop
# the constraint or re-enable native.
if self.native is False and self._requires_native():
    raise UserError(f'{type(self).__name__}: constraint fields require the native tool, but native=False')

# Disallow `native=False` without an explicit local — would produce a silent no-op capability.
if self.native is False and self.local is None:
    raise UserError(...)
```

**Flow:** Construction-time resolution (all UserErrors before any run): (1) both False → error; (2) `native=True` → subclass `_default_native()` must produce an instance else error naming the escape hatches; (3) local ladder — None→`_default_local()`, True/str→`_resolve_local_strategy(name)`, callable→Tool wrap; (4) constraint contradiction checked BEFORE missing-local because no `local=` choice can repair it; (5) `native=False, local=None` rejected as a would-be no-op. Run time: when native is active AND a local exists, the LOCAL toolset is returned wrapped in a PreparedToolset stamping `unless_native=<uid>` on every def — models supporting the native tool drop these defs; models that don't keep only the local. When `_requires_native()` is True the local is suppressed entirely (`get_toolset → None`) so an unsupported model raises rather than silently violating domain allow/block constraints.

**Invariant:** Exactly one of {native, local} is visible per model request, keyed by provider support via the `unless_native` uid; construction never completes in a state that would make the capability contribute zero tools while claiming success.

**Probe:** `tests/test_capabilities.py` — `test_native_or_local_constraint_check_precedes_no_local_check` (:10965), `test_native_or_local_base_no_default_native` (:11012), `test_native_or_local_base_unknown_strategy_raises` (:11067), `test_native_or_local_preserves_passed_tool_instance` (:11075), `test_native_or_local_stamps_id_on_local_toolset` (:2988 — asserts PreparedToolset-wrapped leaf FunctionToolset.id == 'search').

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'NativeOrLocalTool _requires_native unless_native _add_unless_native'
```

## Verdict
**Adopt** the five-step construction validation ladder (ordering matters), the unless_native mutual-exclusion mechanism, and the id stamping of synthesized leaf toolsets. **Adopt** the hook set (`_default_native/_default_local/_resolve_local_strategy/_requires_native/_native_unique_id`) as the subclass contract for WebSearch/WebFetch/ImageGeneration-style capabilities. **Omit** nothing — this is the reusable core; subclasses add only strategy names and constraint fields.
