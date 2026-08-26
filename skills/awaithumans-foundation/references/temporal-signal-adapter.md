<!-- capsule-v2 -->
# Temporal Signal Adapter — how does a parked workflow resume on a human without polling or double-signalling?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you split an await across workflow sandbox, activity worker, and callback server so replays stay idempotent?

## Signal-name-as-idempotency-key with cached-terminal short-circuit
**Path/Symbol:** `packages/python/awaithumans/adapters/temporal/__init__.py` — `await_human` (:208–404), `awaithumans_create_task` activity (:141–198), `_activity_defn` lazy decorator (:117–138), `dispatch_signal` (:446–504), `_resolve_terminal` (:414–440).
**Signature:** signal = `"awaithumans:{idempotency_key}"`; default key `temporal:{workflow_id}`; `wait_condition(lambda: received, timeout=timeout_seconds)`.
**Data Shape:** frozen-dataclass `_CreateTaskInput` of plain types (Pydantic models don't cross the data-converter; schemas pre-serialized to JSON-Schema dicts on the WORKFLOW side).

### Decisive source
```python
existing_status = task_record.get("status") if isinstance(task_record, dict) else None
if existing_status in _TERMINAL_STATUS_VALUES:
    logger.warning("... already exists ... Returning cached response WITHOUT waiting for a "
                   "new signal. Pass a fresh idempotency_key= for a new attempt.")
    return _resolve_terminal(existing_status, task_record, response_schema, ...)
# wait_condition parks the workflow under BOTH branches — zero compute while idle:
try:
    await workflow.wait_condition(lambda: completed_status[0] is not None,
                                  timeout=timedelta(seconds=timeout_seconds))
except asyncio.TimeoutError as exc:
    raise TaskTimeoutError(task=task, timeout_seconds=timeout_seconds) from exc
```
Closure capture quirk:
```python
received: list[Any] = [None]        # Python closures can't rebind outer scalars;
completed_status: list[str|None] = [None]   # 1-element lists dodge it without a class
```

**Flow:** register signal handler → activity POSTs task (HTTP lives OUTSIDE the sandbox; Temporal auto-retries transient server errors) → terminal-in-create-response ⇒ resolve immediately (pre-#72 this parked 15 minutes for what was an instant cached return) else park on signal-or-timer → human finishes → server POSTs user's `callback_url` → their route calls `dispatch_signal(temporal_client, workflow_id, body, sig)`: PermissionError⇒401 / ValueError⇒400 / success⇒`handle.signal("awaithumans:{key}", payload)` → handler stores status+response → wait_condition releases → typed status branch.
**Invariant:** the SAME key is the server dedup gate AND the Temporal signal name AND the replay identity — replays produce identical keys so exactly one ticket and one signal ever exist. Default changed from `hash(task,payload)` to `workflow_id` because identical content across runs collided (#72). Import-safety ladder: `_require_temporal` fail-fast at call time; `_activity_defn()` no-op stand-in keeps the module importable without temporalio.
**Probe:** `tests/adapters/test_temporal_adapter.py` (:108–129 dispatch routes to correct workflow+signal, :177–190 missing-idempotency rejected, :373–424 activity POST shape); matrix `tests/adapters/test_idempotency_collision.py` (:52–128).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "temporal signal handler wait_condition", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt key-triple-reuse (dedup=signal=replay), terminal short-circuit before parking, closure-list capture, sandbox-safe import laddering, and framework-agnostic security helpers that own only HMAC/parse/signal. Adapt signal naming. Omit example worker/server wiring.
