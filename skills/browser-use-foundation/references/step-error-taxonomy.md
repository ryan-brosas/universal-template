<!-- capsule-v2 -->
# Step-error taxonomy — classify, recover, and keep the step counter alive

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does an agent loop distinguish "user interrupted" from "browser died" from "bad parse", retrying what's retryable without ever wedging its progress counter?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/service.py`: `_handle_step_error` (:1252-1308), outer shell `_execute_step` (:2441-2502) with `asyncio.wait_for(step_timeout)`, `take_step` (:2248-2281), consecutive-failure accounting (`max_total_failures = max_failures + final_response_after_failure`).
**Signature:** one classifier for every step exception; recovery actions differ per class; the timeout wrapper owns the step-counter invariant.
**Data Shape:** error classes: InterruptedError / connection-like (reconnecting) / browser-closed (terminal) / parse failures / everything else (counted).

### Decisive source
```ts
# _execute_step: on TimeoutError count the failure AND still advance n_steps
# if finalize was skipped by cancellation — the counter can never wedge (:2488-2491)
# _handle_step_error taxonomy:
InterruptedError        -> NOT an error: log warning, continue      # user stop is normal flow
reconnection in progress-> WAIT bounded on session reconnect event;
                           on success record 'Connection lost and recovered'
                           and RETRY the same step                   # transient
browser closed/disconnected -> terminal: set stopped + external pause event
parse failures ('Could not parse response', 'tool_use_failed')
                        -> append a hint about expected output shape  # error becomes instruction
everything else         -> consecutive_failures += 1; WARNING until final
                           failure (ERROR only at max); leave room for a
                           graceful final reply after repeated failures
```

**Flow:** every step exception lands in one handler → classified → transient classes recover in place (bounded reconnect wait then retry), user interrupts pass silently, terminal classes stop the run cleanly, parse errors feed corrective hints back into the next prompt. The outer timeout shell guarantees the step number advances even when cancellation skips finalize.
**Invariant:** no error class is unhandled; retries are bounded and event-driven; failure counting leaves headroom for a final graceful reply; the step counter is monotonic under all cancellation paths.
**Probe:** `tests/agent/` tests (interrupt not counted; recovered connection retries; terminal close stops; parse hint appended; counter advances on timeout).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_handle_step_error consecutive_failures _execute_step TimeoutError n_steps retry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the error taxonomy (interrupt/transient-retry/terminal/counted/hint-on-parse) plus the never-wedge counter guarantee in the timeout shell.
