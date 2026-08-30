<!-- capsule-v2 -->
# Terminal-Echo Idempotency Short-Circuit — what happens when a durable workflow replays after the human already answered?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you prevent a durable adapter (Temporal/LangGraph) from parking forever on an interrupt whose webhook already fired?

## Create-first, then check the echoed status BEFORE pausing
**Path/Symbol:** `packages/typescript-sdk/src/adapters/langgraph/index.ts` — terminal check (:218–238), `resolveTerminal` (:275–304), `TERMINAL_STATUS_VALUES` (:263–268); Python twin `packages/python/awaithumans/adapters/langgraph/__init__.py:249–272` + `_resolve_terminal` (:316+); test harness `packages/python/tests/adapters/test_idempotency_collision.py`.
**Signature:** TS `resolveTerminal(status, source, responseSchema, taskName, timeoutMs): TResponse`; Py `_resolve_terminal(status, task_record, response_schema, *, task, timeout_seconds) -> T`.
**Data Shape:** create response carries full echo `{id, idempotency_key, status, response, completed_at, timed_out_at, verification_attempt}` — not just the id. Terminal set = {completed, timed_out, cancelled, verification_exhausted}.

### Decisive source
```python
existing_status = task_record.get("status")
if existing_status in _TERMINAL_STATUS_VALUES:
    logger.warning(
        "LangGraph adapter: idempotency_key=%s already exists, status=%s, ...")
    return _resolve_terminal(existing_status, task_record, response_schema, ...)
# (interrupt() only reached when NOT already terminal)

resume_value = interrupt({ "task_id": ..., "idempotency_key": idem, ... })
if not isinstance(resume_value, dict):
    raise RuntimeError("...Did your callback handler forget to pass the "
                       "webhook body to Command(resume=...)?")
```

**Flow:** create task on server FIRST (idempotent on key; visible to humans immediately; interrupt-first would pause before the task existed) → if echoed status already terminal: log loudly + resolve from cached record and NEVER call `interrupt()` → else `interrupt()` double-duties (first run throws GraphInterrupt; resume returns the FULL webhook body passed via `Command({resume})`) → branch on status: completed = schema-validate + return; timed_out/cancelled/verification_exhausted = typed errors; unknown status = loud Error.
**Invariant:** pre-#72 a dev re-running with the same key parked on `interrupt()` until checkpointer timeout (or forever). The resume value must be the FULL webhook body — passing only `response` makes completed/timed_out/cancelled indistinguishable at the node.
**Probe:** `packages/python/tests/adapters/test_idempotency_collision.py` (:52–126 temporal matrix, :149–210 langgraph twin incl. verification-exhausted attempt-count assertion `"5" in str(exc)`); docstring pins WHY `_resolve_terminal` is tested directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "_resolve_terminal TERMINAL_STATUS_VALUES interrupt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt create-BEFORE-interrupt ordering, the terminal-echo short-circuit, full-body-as-resume-value, and the four-branch typed-error mapping verbatim — both languages implement it identically by design ("duplication cheaper than abstracting"). Adapt error classes/timeout units (TS takes ms, Python seconds). Omit nothing; this is the collision fix for #72 in both SDKs.
