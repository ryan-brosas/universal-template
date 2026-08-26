<!-- capsule-v2 -->

# Subprocess env split: bootstrap vs runtime — How do control-channel secrets reach the child without leaking into every grandchild?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** How do you hand a spawned run its supervisor channel env for startup only, and keep it out of the long-lived process environment?

## Two disjoint dicts from one merged env

**Path/Symbol:** `src/prefect/flow_engine.py:run_flow_in_subprocess (2271-2364)`; helpers `_runtime_subprocess_env (181-190)` + `_run_serialized_call_with_control_bootstrap (169-178)`; key set `_CONTROL_CHANNEL_ENV_KEYS = frozenset({"PREFECT__CONTROL_PORT", "PREFECT__CONTROL_TOKEN"}) (:164-166)`.

**Signature:** `run_flow_in_subprocess(flow, flow_run=None, parameters=None, wait_for=None, context=None, env=None) -> multiprocessing.context.SpawnProcess`.

**Data Shape:** Merge order is fixed: `settings_env | os.environ | {"PREFECT__ENABLE_CANCELLATION_AND_CRASHED_HOOKS": "false"} | user_env` → sanitized → partitioned into `startup_env` (ONLY the two CONTROL_* keys) and `runtime_env` (everything else). `env` values of `None` become a `remove_env` set that pops keys in the child.

### Decisive source
```python
def _runtime_subprocess_env(env):
    """Remove one-shot control-channel bootstrap vars from runtime child env."""
    ...
def _run_serialized_call_with_control_bootstrap(payload, startup_env=None):
    """Consume control-channel bootstrap env before deserializing payload."""
    if startup_env:
        os.environ.update(startup_env)
    configure_from_env()
    return _run_serialized_call(payload)

process = ctx.Process(
    target=_run_serialized_call_with_control_bootstrap,
    args=(cast(bytes, wrapped_call.args[0]), startup_env),
)
```

**Flow:** parent merges envs → sanitize → split into startup/runtime → child process starts with target = bootstrap wrapper → wrapper injects ONLY startup_env into os.environ → `configure_from_env()` consumes the one-shot vars (module latches port/token, they are never needed again) → deserialize + run the flow with runtime_env applied and None-keys removed → because configure already ran, the CONTROL_* keys need not stay in os.environ where every grandchild subprocess would inherit them.

**Invariant:** (1) The spawn target MUST be the bootstrap wrapper, not the flow call itself — deserialization happens after env consumption so flow-code imports can't observe or leak the token. (2) The two dicts are DISJOINT partitions of the same merge; adding a new one-shot var means extending `_CONTROL_CHANNEL_ENV_KEYS` exactly once. (3) Cancellation/crashed hooks are force-disabled in children via the merged constant `"false"` — the runner owns those transitions (see cancellation-ownership-gate).

**Probe:** `grep -c 'PREFECT__CONTROL_PORT' src/prefect/flow_engine.py` → 1. Direct test: `tests/test_flow_engine.py:5031 TestRunFlowInSubprocess.test_uses_control_bootstrap_wrapper_before_deserializing_payload` (fake Process captures target identity; asserts `args[1] == {"PREFECT__CONTROL_PORT": "4200", "PREFECT__CONTROL_TOKEN": "deadbeef"}`, `remove_env == set()`, and `wrapped_env` contains `UNRELATED` + hooks-disable flag but NO control keys).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "run_flow_in_subprocess control channel bootstrap env", "limit": 4}'
```

## Verdict
Adopt the merge→partition→bootstrap-consume pattern whenever a supervised child must receive short-lived credentials; adapt key names/transport; omit cloudpickle payload wrapping specifics.
