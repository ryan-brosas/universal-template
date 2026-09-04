<!-- capsule-v2 -->
# Dynamic workflow resource limits — how do you cap an orchestration script's own sandbox resources without accidentally disabling the cap through a typo'd key?

**Source:** pydantic-ai-harness Apache-2.0 `main@76db3dec8f6c97d8deb81a0be2f80aab1bb15dd5`; Codebase Memory `pydantic-ai-harness`. **Question:** Where do sandbox limits get validated and resolved so a partial user dict can't silently drop the one guard against a pure-CPU `while True`, and what does the duration cap actually measure?

## Strict-key resolve + await-exempt duration contract
**Path/Symbol:** `pydantic_ai_harness/dynamic_workflow/_toolset.py:_resolve_resource_limits` (:93-108), `_default_resource_limits` (:75-79), `_RESOURCE_LIMIT_KEYS` (:84), `WorkflowResourceLimits` TypedDict (:61-73), construction-time validation `DynamicWorkflowToolset.__post_init__` (:508), call-time resolution in `call_tool` (:725).
**Signature:** `_resolve_resource_limits(limits: WorkflowResourceLimits | Literal['unlimited'] | None) -> ResourceLimits`; `WorkflowResourceLimits(TypedDict, total=False)` with `max_duration_secs: float` and `max_memory: int`.
**Data Shape:** Public API accepts `None` (backstop), `'unlimited'` (empty), or a PARTIAL mapping merged onto the backstop `{max_memory: 256*1024*1024}`; resolved dict feeds `monty_pool.checkout(limits=...)`.

### Decisive source
```python
# _toolset.py:82-85 — a total=False TypedDict validates NOTHING at runtime
# The keys `WorkflowResourceLimits` accepts. A `total=False` TypedDict does not validate keys at
# runtime, so a typo (e.g. `max_durations_secs`) would otherwise merge through and be silently
# dropped -- quietly disabling the only guard against a pure-CPU `while True`. We reject unknowns.
_RESOURCE_LIMIT_KEYS = frozenset(WorkflowResourceLimits.__annotations__)

# _toolset.py:93-108 — three-way resolve: None→backstop, 'unlimited'→{}, partial→merge ONTO backstop
def _resolve_resource_limits(limits):
    if limits is None:
        return _default_resource_limits()
    if limits == 'unlimited':
        return {}
    unknown = set(limits) - _RESOURCE_LIMIT_KEYS
    if unknown:
        raise UserError(
            f'Unknown `resource_limits` key(s): {sorted(unknown)}. Valid keys are {sorted(_RESOURCE_LIMIT_KEYS)}.'
        )
    return {**_default_resource_limits(), **limits}
```

**Flow:** Construction (`__post_init__`) calls `_resolve_resource_limits(self.resource_limits)` purely to VALIDATE — a typo'd key raises `UserError` when the toolset is built, not at the first tool call (:508 comment "validate keys now, not at the first tool call"). At each `call_tool`, the same resolver produces the real limits handed to the Monty sandbox; the script then executes under `MontyExecutor(dispatch=dispatch, valid_names=...)` with sub-agents running concurrently.
**Invariant (strict keys):** unknown keys are REJECTED, never ignored — because a silently-dropped `max_duration_secs` disables the only defense against a CPU-spinning script. The error names the offending keys AND the valid set.
**Invariant (merge semantics):** a partial dict merges ONTO the backstop rather than replacing it — specifying only `max_duration_secs` keeps the 256 MiB memory floor; the direct test proves an explicit tiny `max_memory: 4096` actually reaches the sandbox (override enforced, not dropped).
**Invariant ('unlimited' is total):** the literal string resolves to `{}` — opting out of the duration cap ALSO opts out of the memory backstop; there is no "unlimited time, default memory" shape.
**Invariant (duration measures sandbox steps):** `max_duration_secs` bounds IN-SANDBOX execution counted per bytecode step by Monty; time spent `await`ing sub-agents — single await or a concurrent `asyncio.gather` batch — does NOT accrue, because during those waits the script is suspended on the host. There is NO default cap: unset means a pure-CPU `while True` burns a core unbounded, which is precisely the runaway sub-agent budgets cannot catch.
**Relation:** distinct from the replay twin `temporal-resource-limit-stripping.md` — THAT capsule nulls `max_duration_secs` under Temporal replay determinism; THIS one resolves+validates live user config. Same field name, opposite concerns.
**Probe:** `tests/dynamic_workflow/test_dynamic_workflow.py::test_runaway_loop_stopped_by_duration_cap` (:1209, `while True` trips ModelRetry under a 0.2s cap), `::test_awaiting_sub_agents_does_not_count_against_duration_cap` (:1224, three 0.2s-host-sleep sub-agents complete under a 0.1s cap), `::test_resource_limit_override_is_enforced_in_the_sandbox` (:1230, partial merge reaches sandbox), `::test_unlimited_runs_without_a_backstop` (:1238), `::test_unknown_resource_limit_key_raises_at_construction` (:1245, parametrized typos raise at construction).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "resolve resource limits workflow sandbox", limit: 10, fields: ["signature", "name", "file"] });
// rank #1 = _resolve_resource_limits :93-108 line-exact; rank #2 exposes the code_mode/_toolset.py:239-258 twin (same name, separate resolver)
```

## Verdict
Adopt the four-part pattern for ANY host exposing sandbox/resource knobs to users or models: derive the legal key set from the type itself, reject unknown keys loudly at construction, merge partial configs onto backstops instead of replacing them, and define duration caps to exclude host-side awaits. Adapt the backstop values (256 MiB) and the two-key vocabulary to your sandbox. Omit the Monty checkout mechanics if your runtime has its own enforcement. Caveat: full `tests/dynamic_workflow/` suite executed GREEN 107 passed at pin `76db3dec` in `/tmp/harness-p6-venv` (2026-08-24); coverage clean (`no_recorded_issue`) ×2 cited paths.
