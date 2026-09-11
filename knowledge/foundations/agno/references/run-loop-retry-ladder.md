<!-- capsule-v2 -->
# Run loop retry ladder — How does the synchronous run loop order its stages and retry without losing background work?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** Where do retries sit relative to session reads, hooks, and background futures so a porter doesn't re-read sessions per attempt or leak threads?

## The attempt loop wraps everything between session read and final store
**Path/Symbol:** `libs/agno/agno/agent/_run.py:_run` (:340-751).
**Signature:** `_run(agent, run_response, run_context, session_id, user_id=None, add_history_to_context=None, ..., pre_session=None, **kwargs) -> RunOutput`.
**Data Shape:** mutates caller-owned `run_response` in place; `pre_session` lets dispatch reuse its already-read session on attempt 0 (`if attempt == 0 and pre_session is not None: agent_session = pre_session` :410-413), so retries RE-READ the session but the first attempt never double-reads.

### Decisive source
```python
num_attempts = agent.retries + 1
for attempt in range(num_attempts):
    ...
    except Exception as e:
        if attempt < num_attempts - 1:
            if agent.exponential_backoff:
                delay = agent.delay_between_retries * (2**attempt)
            else:
                delay = agent.delay_between_retries
            time.sleep(delay)
            continue
        run_response.status = RunStatus.error
        flush_in_flight_messages_on_error(run_response, locals().get("run_messages"))
        if run_response.content is None:
            run_response.content = str(e)
```

**Flow:** read/create session → update metadata → load session_state → resolve dependencies → cancellation check → pre-hooks (consumed with `deque(..., maxlen=0)`) → get/determine tools → build run messages → start memory/learning/culture futures → reasoning → `call_model_with_fallback` → output-model/parser-model post-passes → update_run_response → PAUSE EXIT if any tool `.is_paused` → media/structured-format/followups → post-hooks → cancellation check → wait_for_open_threads + merge_background_metrics → optional session summary → status=completed → cleanup_and_store.
**Invariant:** Retryable `Exception`s sleep-and-retry INSIDE the loop, but `RunCancelledException`, `InputCheckError`/`OutputCheckError`, and `KeyboardInterrupt` have dedicated except arms that return immediately WITHOUT consuming an attempt — guardrail failures and cancellations are terminal, not retryable. On any non-retryable path `flush_in_flight_messages_on_error` drains partial messages into the response BEFORE cleanup_and_store persists them.
**Probe:** `grep -c 'raise_if_cancelled(run_response.run_id)' libs/agno/agno/agent/_run.py` → **47** inline cancellation checkpoints threaded through every stage boundary of both sync loops; direct behavior test `libs/agno/tests/integration/agent/test_agent_run_cancellation.py::test_continue_session_after_cancelled_agent_run`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "_run agent run loop retries attempt", limit: 10, fields: ["signature", "name", "file"] });
```
(resolves `_run` Function libs/agno/agno/agent/_run.py 340-751.)

## Verdict
Adopt the stage ordering and the terminal-vs-retryable exception split; adapt the concrete future trio names to your framework's side-effect workers; omit FastAPI `background_tasks` passthrough if you have no request-scoped task queue.
