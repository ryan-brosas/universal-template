<!-- capsule-v2 -->
# Runtime toolset rejection — per-run executing toolsets bypass durable wrapping and would run un-checkpointed

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/_runtime_toolsets.py` + `durable_exec/_base.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Toolsets passed via `run(toolsets=...)` arrive AFTER the engine durably wrapped constructor toolsets — how do you stop an *executing* runtime toolset from silently running outside the checkpoint/replay protocol while still allowing non-executing ones? A porter will either block everything at runtime (breaking external-tool deferral) or allow everything (silent non-durable side effects).

## Path / Symbol
`_runtime_toolsets.py` — `reject_unsupported_runtime_toolsets` (:73–121), `_runtime_toolset_kind` (:52–70), `reject_cancellation_token` (:46–49); `_base.py` — `_reject_runtime_toolsets` (:124–161), `before_run` cancellation guard (:163–175).

## Signature
```python
RuntimeToolsetKind = Literal['function', 'mcp', 'dynamic']
def reject_unsupported_runtime_toolsets(toolsets, *, unsupported_kinds: frozenset[RuntimeToolsetKind],
    engine: str, tool_config_key: str | None = None) -> None
def _runtime_toolset_kind(toolset: AbstractToolset) -> RuntimeToolsetKind | None   # None = pass through
```

## Data Shape
Classification mirrors what the engines actually wrap: only leaf kinds they durabilize are rejected — `FunctionToolset`, `MCPToolset`, and `DynamicToolset` (contents uninspectable up front). A custom `AbstractToolset` leaf that executes I/O passes through: the SAME blind spot constructor-time wrapping already has, deliberately symmetric. Engine tables differ: DBOS omits `'function'` (runs function tools inline as steps), Temporal/Prefect reject all three. Per-capability metadata key (`'temporal'`/`'prefect'`) with explicit `False` opts async tools out of wrapping.

### Decisive source — identity-set diff of construction vs runtime leaves (_base.py :135–155)
```python
construction_leaves: set[int] = set()
for agent_toolset in self._agent.toolsets:
    agent_toolset.apply(lambda leaf: construction_leaves.add(id(leaf)))
def collect(leaf):
    if id(leaf) in construction_leaves:
        return
    if isinstance(leaf, CapabilityOwnedToolset):
        return          # non-executing packaging; its inner leaf is visited separately
    runtime_leaves.append(leaf)
toolset.apply(collect)
```
Outside a durable context (`in_durable_context` False) the whole check is transparent. The cancellation-token guard reads `ctx.__dict__.get('_cancellation')` so a restricted run-context subclass whose `__getattribute__` rejects absent fields doesn't raise a misleading error; tokens are rejected ONLY inside the container — a durable-capable agent used outside a workflow keeps accepting them.

**Flow:** before_run rejects same-process `CancellationToken` (non-deterministic if fired inside a workflow on replay) → per-run toolsets walk → identity-set diff isolates genuinely-new leaves → kind classification → any unsupported kind raises one aggregated `UserError` naming sorted labels + the metadata opt-out.

**Invariant:** Reject only what executes or is uninspectable; judge wrapper packaging transparently by walking through to real leaves; the error must teach the fix ("pass them to the agent constructor instead").

**Probe:** `tests/test_dbos.py::test_dbos_agent_run_in_workflow_with_runtime_external_toolset` (:1296 — ExternalToolset allowed), `test_dbos_agent_run_in_workflow_with_runtime_function_toolset` (:1335 — FunctionToolset allowed under DBOS specifically), `..._rejects_runtime_mcp_toolset` (:1358), `..._rejects_runtime_dynamic_toolset` (:1374, byte-exact snapshots); `tests/test_temporal.py::test_temporal_agent_run_in_workflow_with_executing_toolsets` (:3008).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'reject_unsupported_runtime_toolsets RuntimeToolsetKind construction_leaves'
```

## Verdict
**Adopt** the three-kind classification table, identity-set diff, capability-owned-wrapper transparency, opt-out metadata channel, and in-container-only enforcement. **Adapt** which kinds your engine can checkpoint. **Omit** nothing — 121 lines, every branch test-pinned upstream.
