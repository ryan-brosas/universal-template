<!-- capsule-v2 -->
# Flow ask() — contextvar-named steps, auto-checkpoint before blocking, timeout-None contract

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How can a sync method inside an async flow block on human input without stalling the event loop — and what state guarantees precede the block?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` — `ask` (:3368), `_checkpoint_state_for_ask` (:3343), `_resolve_feedback_provider` (:3652); step-name contextvar set in `_execute_method` (:2881 `current_flow_method_name.set`).
**Signature:** `ask(message: str, timeout: float | None = None, metadata: dict | None = None) -> str | None` (None = timeout/disconnect/error; "" = intentional empty input).
**Data Shape:** reads `current_flow_method_name` ContextVar (set BEFORE `copy_context()` so thread-pooled sync methods inherit it) instead of stack inspection.

### Decisive source
```python
# :3376 docstring states the concurrency contract verbatim:
# "Blocks the current thread until the user provides input or the
#  timeout expires. Works in both sync and async flow methods (the
#  flow framework runs sync methods in a thread pool via
#  ``asyncio.to_thread``, so the event loop stays free)."
#
# "Timeout ensures flows always terminate. When timeout expires,
#  ``None`` is returned" ... and:
# "Before waiting for input, the current ``self.state`` is automatically
#  checkpointed to persistence (if configured) for durability."

# :2876 ordering comment for the contextvar that makes ask() name-aware:
# "Set method name in context so ask() can read it without stack inspection.
#  Must happen before copy_context() so the value propagates into the
#  thread pool for sync methods."
method_name_token = current_flow_method_name.set(method_name)
try:
    if asyncio.iscoroutinefunction(method):
        result = await method(*args, **kwargs)
    else:
        ctx = contextvars.copy_context()
        result = await asyncio.to_thread(ctx.run, method, *args, **kwargs)
finally:
    current_flow_method_name.reset(method_name_token)
```

**Flow:** method calls self.ask(...) → framework checkpoints current state to persistence (durability against crash-during-wait) → resolves provider (default console; pluggable HumanFeedbackProvider) → blocks ONLY the worker thread / awaits only this coroutine → answer or None-on-timeout returns into the method; underlying provider request may outlive a timeout (documented best-effort).
**Invariant:** The thread-pool execution of sync methods is a PRECONDITION of ask(): blocking inside a loop-running coroutine would freeze every other task. The contextvar must be set before copy_context or pooled methods lose the step name. Timeout semantics are return-None-NOT-raise so `while (msg := ask(...)) is not None:` loops terminate.
**Probe:** `grep -c 'current_flow_method_name' lib/crewai/src/crewai/flow/runtime/__init__.py` → `5`.
**Direct test:** `tests/test_flow_ask.py::test_ask_returns_user_input` (:130), `::test_ask_in_async_method` (:144), `::test_ask_in_start_method` (:158), `::test_ask_conditional` (:212) — suite green (48 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "ask request input from the user during flow execution", limit: 5 });
// → ext-crewAI...flow.runtime.Flow.ask Method 3368+
```

## Verdict
Adopt thread-isolated blocking input with pre-block checkpointing and None-timeout for any interactive workflow. Adapt providers. Omit CrewAI's console prompt formatting.
