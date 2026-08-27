<!-- capsule-v2 -->
# Circuit-breaker scoping — how is a shared breaker registry prevented from cross-agent contamination and stale-id reuse?

**Source:** praisonai MIT `main@d82364ec23a83fd9a6e2e849a5285442b4734ca3`; Codebase Memory `praisonai`. **Question:** When every agent instance shares one process-global circuit-breaker registry, how does a failing tool in agent A avoid tripping the breaker for agent B's same-named tool — and how is the CPython object-id reuse window (a new Agent at the same memory address inheriting a stale OPEN breaker) closed?

## ToolExecutionMixin._execute_tool_with_circuit_breaker_impl scoping
**Path/Symbol:** `src/praisonai-agents/praisonaiagents/agent/tool_execution.py` — `_execute_tool_with_circuit_breaker_impl` (lines 2222–2297), `_register_breaker_finalizer` (lines 2205–2220), `_remove_circuit_breaker` (lines 2194–2203).
**Signature:** `_execute_tool_with_circuit_breaker_impl(self, function_name, arguments)` → tool result, error dict, or degraded `{error, circuit_open: True, ...}` dict. Registry key: `f"tool_{id(self)}_{function_name}"`.

### Decisive source
```python
# Get or create circuit breaker for this tool.
# Scope the key to this Agent instance so one agent's failing tool
# cannot trip the breaker for another agent's same-named tool.
breaker_name = f"tool_{id(self)}_{function_name}"
config = CircuitBreakerConfig(
    failure_threshold=5,        # Open after 5 failures
    recovery_timeout=60.0,      # Wait 60s before trying half-open
    timeout=30.0,               # Tool call timeout
    graceful_degradation=True   # Return error instead of raising exception
)
breaker = get_circuit_breaker(breaker_name, config)

# Ensure the registry entry is removed the moment this Agent is
# actually garbage-collected, regardless of whether close()/aclose()
# was ever called. This closes the CPython id-reuse window where a
# new Agent at the same address could inherit a stale OPEN breaker.
self._register_breaker_finalizer(breaker_name)

def _tool_wrapper():
    result = self._execute_tool_impl(function_name, arguments)
    # Convert error dicts to exceptions so circuit breaker can detect failures
    # Don't treat approval/permission denials as circuit breaker failures
    if isinstance(result, dict) and result.get("error") and \
       not result.get("approval_denied") and not result.get("permission_denied") and \
       not result.get("approval_error") and not result.get("policy_denied") and \
       not result.get("guardrail_denied"):
        class _ToolFailure(Exception):
            def __init__(self, error_dict):
                self.error_dict = error_dict
                super().__init__(error_dict.get("error", "Tool execution failed"))
        raise _ToolFailure(result)
    return result

try:
    return breaker.call(_tool_wrapper)
except Exception as e:
    if hasattr(e, 'error_dict'):
        return e.error_dict  # Return the original error dict
    else:
        raise
...
except CircuitBreakerException as e:
    # Circuit breaker is open - return error dict instead of raising
    return {
        "error": f"Tool '{function_name}' circuit breaker open - too many recent failures",
        "circuit_open": True,
        "remediation": "Wait for recovery_timeout (60s) or investigate recent tool failures.",
    }
```

and the finalizer:

```python
def _register_breaker_finalizer(self, breaker_name):
    registered = self.__dict__.setdefault('_breaker_finalizer_names', set())
    if breaker_name in registered:
        return
    registered.add(breaker_name)
    finalizers = self.__dict__.setdefault('_breaker_finalizers', [])
    finalizers.append(weakref.finalize(self, self._remove_circuit_breaker, breaker_name))
```

**Flow:** build per-instance key `tool_{id(self)}_{fn}` → get-or-create breaker with fixed config (threshold 5 / recovery 60s / timeout 30s / graceful degradation) → register a `weakref.finalize(self, ...)` once per name so GC of the agent removes its registry entries even when `close()`/`aclose()` never ran → wrap execution so error *dicts* become a sentinel `_ToolFailure` exception (the breaker only counts exceptions as failures) EXCEPT denial-keyed dicts, which are policy outcomes, not reliability failures → on sentinel, unwrap back to the original error dict; on `CircuitBreakerException`, degrade gracefully into an error dict carrying `circuit_open: True` + remediation hint instead of raising; lazy import of the circuit_breaker module falls back to direct execution when unavailable.
**Invariant:** two live agents sharing a tool name can never share a breaker; a collected agent leaves no registry entry behind (the id-reuse window is closed by the finalizer, not by cooperative cleanup); denials never count toward the failure threshold; an OPEN breaker surfaces as data (`circuit_open` dict), which the retry ladder then short-circuits — the breaker degrades, it does not crash.
**Probe:** `tests/unit/test_circuit_breaker.py:235–260` (`test_global_registry`) pins the property the per-agent key protects — `get_circuit_breaker("service1")` returns the SAME instance twice and a different one for another name, with per-name stats isolation. The finalizer/id-reuse behavior itself has no direct test at the pin → deterministic-read caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "praisonai", query: "circuit breaker registry finalizer id reuse scope", name_pattern: "^_register_breaker_finalizer$|^get_circuit_breaker$|^CircuitBreakerConfig$", limit: 10 });
```

## Verdict
Adopt all three scoping moves together — they are one mechanism: instance-scoped keys (isolation), weakref finalizer removal (lifecycle without cooperative close), and denial-exempt failure counting (correct signal). Adopt graceful-degradation-to-data for the open state so upstream retry logic can short-circuit on a flag rather than catch an exception. Adapt the fixed config values to your host's SLOs and the `id(self)` key to your host's identity primitive (use a stable uuid if your runtime can reuse object ids across longer-lived objects). Omit praisonai's lazy-import fallback unless your breaker module is optional. Coverage: no recorded index issue on cited paths; registry identity is directly tested, the finalizer path is not.
