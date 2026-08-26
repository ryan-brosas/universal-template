<!-- capsule-v2 -->
# Prefect value-addressed cache keys — hash by values, never pickle memo layout

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/prefect/_cache_policies.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A task framework hashes inputs to dedupe/replay work, but its fallback serializer (cloudpickle) digests object SHARING, not values — so a replayed model response (fresh deserialized strings) produces a different key than the live call, and non-idempotent tools re-run on every retry. How do you make task keys value-addressed and stable across attempts? A porter will hash the input objects as-is and ship a cache that silently never replays.

## Path / Symbol
`_cache_policies.py` — `_NON_SERIALIZABLE` sentinel (:13), `_cacheable_value` (:36–59), `_replace_run_context` hand-authored projection (:62–129), `_CACHE_EXCLUDED_FIELDS` (:132–133), `_strip_cache_excluded_fields` framework-only recursion (:136–168), `_replace_toolset_tools` value identity (:171–196), `PrefectAgentInputs.compute_key` pipeline (:206–221), `DEFAULT_PYDANTIC_AI_CACHE_POLICY = PrefectAgentInputs() + TASK_SOURCE + RUN_ID` (:224).

## Signature
```python
def compute_key(self, task_ctx, inputs, flow_parameters, **kwargs):
    if not inputs: return None
    inputs_without_toolset_tools = _replace_toolset_tools(inputs)      # live tool → {toolset_id, tool_def}
    inputs_with_hashable_context   = _replace_run_context(inputs)      # RunContext → projected dict
    filtered_inputs                = _strip_cache_excluded_fields(...) # drop per-run fields
    return INPUTS.compute_key(task_ctx, filtered_inputs, flow_parameters, **kwargs)
```

## Data Shape
The `ToolsetTool` replacement is THE fix for memo-layout hashing: `{toolset.id, _cacheable_value(tool_def)}` — both hash over the JSON path. The docstring records the failure mode verbatim: pickle emits memo references for repeated objects; first attempt shares one string object between `tool_name` and the def's name, retry doesn't → identity-sensitive key never replays.

### Decisive source — exhaustive hand-authored RunContext projection (:66–74)
```python
# This projection is hand-authored rather than derived from `fields(RunContext)`: most of what a
# `RunContext` holds is live run machinery that can't be hashed. Every field a task's work can
# depend on has to be listed here ...
# test_cache_key_run_context_projection_is_exhaustive fails when a new field is neither
# projected here nor consciously categorized as cache-irrelevant.
```
Projection rules worth porting verbatim: `tool_call_id` keyed VERBATIM (separates two parallel calls with identical args — while history's framework-generated ids are normalized to `<framework-generated>`); `messages` deliberately history-sensitive (a tool reading `ctx.messages` must not replay across histories; retries still replay because per-run fields strip value-identically); capability sets SORTED (sets have no stable iteration order); `capability_loaded` omitted as derived from `loaded_capability_ids`; deps/metadata/validation_context get `<non-serializable>` sentinel per-leaf so ONE live HTTP client doesn't kill hashing of its serializable siblings.

**Flow:** task call → replace live objects with value identity → project context to hashable dict → strip per-run fields (`timestamp`, `run_id`, `conversation_id`) but ONLY on pydantic_ai-owned dataclasses (user dataclass fields always fork) → framework INPUTS hash.

**Invariant:** Cache keys must be a pure function of task-relevant VALUES; every new context field must be consciously classified (projected or declared irrelevant) with a TEST enforcing exhaustiveness; framework-generated identifiers normalize, caller-supplied ones don't.

**Probe:** `tests/test_prefect.py::test_cache_key_run_context_projection_is_exhaustive` (:1929), `test_cache_policy_hashes_tools_by_value_not_object_identity` (:1695), `test_flow_retry_replays_tool_result` (:2053 — non-idempotent tool runs exactly once across a flow retry).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'PrefectAgentInputs compute_key cacheable ToolsetTool'
```

## Verdict
**Adopt** the value-addressing ladder and the exhaustiveness-test discipline for ANY content-addressed task cache. **Adapt** the projected field list to your context. **Omit** the Prefect policy-composition classes.
