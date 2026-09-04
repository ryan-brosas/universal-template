<!-- capsule-v2 -->
# Step-failure retry funnel — what actually happens when a loop iteration throws, and which state leaks into the next iteration?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** When any agent stage raises mid-loop, does the run die, and what stale values survive into the next iteration?

## Outer catch-and-continue funnel with per-iteration error-slot resets
**Path/Symbol:** `core/orchestrator.py`:`Orchestrator.run` (`:311` while, `:400-401` slot resets, `:606-615` funnel).
**Signature:** `async def run(self, command, start_url: Optional[str] = None) -> str` (single `while not self.terminate` body).
**Data Shape:** Two locals declared BEFORE the browser stage every iteration: `browser_error = None`, `tool_interactions_str = None`. The critique prompt later interpolates both (`browser_error="{browser_error if browser_error else "None"}"`, `tool_response="{browser_response.data}"`) — so their reset discipline IS the correctness contract.

### Decisive source
```python
# :400-401 — slots reset at the TOP of every iteration, before BA runs
browser_error = None
tool_interactions_str = None
...
# :606-615 — the ONLY handler around the whole per-iteration try:
except Exception as step_error:
    error_msg = f"Error in execution step {i}: {str(step_error)}"
    await self.notify_client(f"Error in execution step {i} : {str(step_error)}", MessageType.ERROR)
    logfire.error(error_msg, exc_info=True)
    await self.browser_manager.notify_user(
        error_msg,
        message_type=MessageType.ERROR
    )
    # Optionally retry or continue to next iteration
    continue
```
**Flow:** planner raise → inner handler re-raises `PlannerError` (:371) → caught by :606 funnel → notify user+client → `continue` → iteration N+1 starts with fresh error slots and UNCHANGED agent histories → same command retried. Same path catches screenshot failures (`CustomException` :398/:496) and SS-analysis failures (`SSAnalysisError` :519). Only two exits exist from the loop: critique `terminate=True` (:585-596) or a context-length graceful return inside an inner handler (:369/:466/:576). The outermost `except Exception as e: ... raise` (:617-626) fires only for errors OUTSIDE the while body.
**Invariant:** A raised PlannerError/CritiqueError/SSAnalysisError does NOT abort the run — it degrades to notify+retry with no backoff, no max-attempt cap, and no iteration ceiling anywhere in code (`i = 0` at :309 is assigned once and never used; `self.iteration_counter += 1` at :313 is logging-only). Termination authority stays 100% with the critique LLM. Because histories are never rolled back on failure, a half-completed iteration's messages persist — the next planner run sees them.
**Leak trap (port carefully):** `tool_interactions_str` is reset each iteration but `browser_response` is NOT — if the browser stage RAISES, the critique prompt at :532 still interpolates the PREVIOUS successful iteration's `browser_response.data` alongside this iteration's real `browser_error`. A porter who "fixes" this by initializing once outside the loop turns a one-iteration staleness into permanent staleness; keep the per-iteration reset of the two declared slots exactly as-is and know that `browser_response` staleness is by omission.
**Probe:** `grep -c "browser_error = None" core/orchestrator.py` → `1`; `grep -c "tool_interactions_str = None" core/orchestrator.py` → `1`; `grep -n "browser_response.data" core/orchestrator.py` → lines `440, 441(comment), 532` (532 = the stale-carry site); `grep -c "context_length_exceeded" core/orchestrator.py` → `3` (one graceful exit per agent stage); `grep -c continue core/orchestrator.py` → `6` total occurrences incl. comments; `grep -n "raise PlannerError" core/orchestrator.py` → `371`; `grep -n "i = 0" core/orchestrator.py` → `309` only (never incremented).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "Orchestrator run step_error continue retry", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the funnel shape: per-stage handlers classify (data-error → critique input; context-death → graceful return), ONE outer catch-all converts everything else into notify+retry. Adopt the per-iteration slot resets verbatim. Adapt: add a hard attempt ceiling/backoff before porting to production (upstream relies on the critique LLM noticing loops via its ≥5-repeat rule). Omit the unused `i` variable and logfire plumbing. Coverage caveat: no upstream tests; probes are line-pinned greps at pin `71daa28`.
