<!-- capsule-v2 -->
# LangGraph Interrupt Adapter — how does a graph node block on a human while surviving process death?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** In interrupt/resume engines, which side-effect ordering makes the human-facing ticket appear exactly once across checkpoint replays?

## Create-BEFORE-interrupt with resume-value passthrough
**Path/Symbol:** `packages/python/awaithumans/adapters/langgraph/__init__.py` — `await_human` (:121–316), `_default_idempotency_key` (:90–107), `dispatch_resume` (:343–400).
**Signature:** `interrupt({task_id, idempotency_key, task, payload, callback_url}) -> resume_value`; `dispatch_resume(*, graph, thread_id, body, signature_header) -> dict`.
**Data Shape:** resume value = FULL webhook body dict (not just response — status branches need it); recommended explicit key `langgraph:{thread_id}:{node_name}`.

### Decisive source
```python
# Create the task BEFORE interrupt() so the human-facing surface
# (Slack DM, email, dashboard row) appears immediately. Putting interrupt
# first creates a "tree falls in the forest" window where the graph is
# paused but NO HUMAN HAS BEEN NOTIFIED yet.
resp = await client.post(f"{server_url}/api/tasks", json=body, headers=headers)
...
if existing_status in _TERMINAL_STATUS_VALUES:
    # No webhook coming and Command(resume=...) would never fire (#72).
    return _resolve_terminal(...)        # skip interrupt() entirely
resume_value = interrupt({...})
if not isinstance(resume_value, dict):
    raise RuntimeError("LangGraph adapter expected a dict resume value ... "
                       "Did your callback handler forget to pass the webhook body?")
```
Server-side per-key uniqueness makes re-running this node idempotent across checkpoint restores — same key hits the same task, no duplicate ticket.

**Flow:** node POSTs task → interrupt throws GraphInterrupt → checkpointer already persisted → caller catches at `.ainvoke()` boundary → human answers via any channel → server POSTs `callback_url` (thread_id baked into it) → user's route calls `dispatch_resume`: HMAC fail ⇒ PermissionError(401), JSON fail ⇒ ValueError(400) → `graph.ainvoke(Command(resume=payload), config={"configurable":{"thread_id":...}})` → replayed `interrupt()` RETURNS the value → status branch raises typed errors or validates response.
**Invariant:** content-hash default COLLIDES across threads with identical payloads — thread-scoped keys are the documented fix; adapters namespace prefixes (`langgraph:`/`temporal:`) so a cross-adapter collision can't land on one task. GraphInvokable kept STRUCTURAL (callable taking Command+config) so the heavy CompiledStateGraph class never enters the type surface.
**Probe:** shared adapter matrix `packages/python/tests/adapters/test_idempotency_collision.py` (:149–199 — the four `test_langgraph_resolve_*` tests; NO dedicated `test_langgraph_adapter.py` exists at this pin) + sibling `temporal-adapter.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "langgraph dispatch_resume Command interrupt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt create-before-park ordering, terminal short-circuit before interrupt, full-body resume passthrough with shape assertion, and structural typing of engine handles. Adapt to your engine's pause primitive. Omit example FastAPI wrappers (~10-line host glue).
