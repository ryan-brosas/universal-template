<!-- capsule-v2 -->
# Decorator hook registry: entries, wrap chains, timeout wrapper, error-replacement ladder

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/hooks.py` — How does a flat dict-of-lists registry give an entire agent lifecycle (run/node/model-request/tool/output/event) before/after/wrap/on-error semantics with decorator ergonomics, sync auto-wrapping, per-hook timeouts, and predictable multi-registration order? Porters get the wrap-chain direction and the error-handler replacement rule wrong.

## Path / Symbol
`capabilities/hooks.py` — `_HookEntry` (79–85) / `_ToolHookEntry` (87–93, adds frozenset tools filter), `_call_entry` (231–249 timeout+sync-wrap), `_call_func` (251–256), `_filter_tool_entries` (262–269), `_bare_or_parameterized` (275–292), `_HookRegistration._r` registry writes (:354–745, every event key), `Hooks.__init__` kwargs→registry (:789–840), `on` cached_property (:849), dispatch overrides `before_run/wrap_run/on_run_error/before_node_run/wrap_run_event_stream/before_model_request/…` (:884–1000), `_make_wrap_link` (:1260–1290), `_event_callback_stream` (1300–1320), `HookTimeoutError(AgentRunError, TimeoutError)` (65–76).

## Signature
```python
_registry: dict[str, list[_HookEntry]]           # event key -> registration-order list

def _bare_or_parameterized(registry, key, func, *, timeout=None):
    # supports @hooks.on.x  AND  @hooks.on.x(timeout=…) — returns func or decorator

async def _call_entry(entry, hook_name, *args, **kwargs):
    if entry.timeout is not None:
        with anyio.fail_after(entry.timeout): return await _call_func(...)
    return await _call_func(func, *args, **kwargs)   # sync fns auto-awaited via isawaitable
```

## Data Shape
~30 event keys mirroring AbstractCapability hook points (`before_run`, `after_run`, `wrap_run`, `on_run_error`, `*_node_run`, `run_event_stream`, `_on_event` [private key so `event=` never satisfies public wrap gates], `before/after/wrap/on_error` × model_request, tool_validate, tool_execute, output_validate, output_process, plus `prepare_tools`/`prepare_output_tools` and `handle_deferred_tool_calls`). Tool hooks filter by `frozenset(tools)` at registration; `_filter_tool_entries` drops entries whose set excludes `call.tool_name`.

## Decisive source
1. **Wrap chains build REVERSED then run** (:888–894): `chain = handler; for entry in reversed(entries): chain = _make_wrap_link(entry, …, chain)` — first-registered becomes OUTERMOST, preserving natural decorator reading order. Empty registry short-circuits: `if not entries: return await handler()`.
2. **Timeout converts to a domain error** (:235–245): `anyio.fail_after` → catch `TimeoutError` → raise `HookTimeoutError(hook_name, func_name, timeout) from None` — dual-inherits `AgentRunError, TimeoutError` so callers can catch either; func_name from `getattr(func,'__name__',repr(func))`.
3. **Error handlers REPLACE the error, last one wins** (`on_run_error` :896–905): each entry runs in try; on success RETURN its result immediately (first successful recovery wins); on raise, `error = new_error` and the NEXT entry sees the REPLACED error; exhausted → `raise error` (the final replacement).
4. **Event-stream composition order** (`wrap_run_event_stream` :949–965): per-event callbacks innermost (`_on_event` → `_event_callback_stream`), explicit stream wrappers outermost chained in reverse; every layer appended to `wrapped_streams` and closed in REVERSE via `_utils.aclose_all(reversed(...))` in `finally` — no orphaned generators on early consumer exit.
5. **Serialization exclusion**: `get_serialization_name()` → None and hooks filtered from spec properties (:2285–2286 of test_capabilities) — runtime callbacks are never serializable config.

## Flow / Invariant
Registration (decorator or `Hooks(before_model_request=f)` kwarg) appends `_HookEntry(func, timeout)` to the key's list → capability dispatch methods iterate in insertion order → before-hooks thread their return value into the next call (`request_context = await _call_entry(...)`) → wrap-hooks form onion links around the real handler → on-error hooks act as a recovery ladder with error replacement. Invariants: registration order == execution order everywhere (no sorting by priority); timeouts only wrap the hook body, never the handler; a hook returning None from a transform hook passes None onward (no magic).

## Probe (direct test)
`tests/test_capabilities.py`: `test_timeout` (:12318 — asserts hook_name/func_name/timeout fields and dual isinstance), `test_sync_function_auto_wrapping` (:12300), `test_multiple_hooks_same_event` (:12210), `test_run_hook_order` (:5926), `test_hooks_before_model_request_swaps_model` (:6237), `test_all_hook_types_on_same_capability` (:6701), `test_deferred_hooks_do_not_fire_until_capability_is_loaded` (:2900), model-error recovery fixture at :12290 (recovering `model_request_error` returns 'recovered').

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'Hooks _HookEntry _make_wrap_link HookTimeoutError'`

## Verdict
**Adopt** the whole pattern as the cheap alternative to subclass-based plugin registries: dict[str, list[entry]] + reversed wrap chains + fail_after timeout + first-success error ladder. **Adapt** event keys and entry payload (tools filter) to your lifecycle. **Omit** the private `_on_event` key trick if you have no separate observe-only vs wrap stream distinction.
