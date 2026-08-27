<!-- capsule-v2 -->
# Streamable function duality — how does one pipeline function serve both a plain call site and a live progress UI?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** How do you add streaming progress to long pipeline functions without duplicating them into "batch" and "streaming" variants?

## StreamableFunction: __call__ drains the generator; .stream() exposes it
**Path/Symbol:** `sweepai/utils/streamable_functions.py:StreamableFunction` (:7–27), `@streamable` (:29–30); decorated producers `multi_get_top_k_snippets`/`prep_snippets`/`multi_prep_snippets`/`fetch_relevant_files` (`ticket_utils.py`) and `get_files_to_change` (`sweep_bot.py:397`); consumer `sweepai/handlers/on_ticket.py:520–531`.
**Signature:** `__call__(self, *args, **kwargs) -> YieldType | ReturnType`; `stream: Callable[..., Generator[YieldType, None, ReturnType]]`.
**Data Shape:** Producer yields arbitrary progress tuples (e.g. `(message, ranked_snippets)` or `(renames_dict, user_facing_message, file_change_requests)`) and `return`s the authoritative final value.

### Decisive source
```python
def __call__(self, *args, **kwargs):
    result = None
    try:
        generator = self.stream(*args, kwargs)
        while True:
            result = next(generator)
    except StopIteration as e:
        return e.value if e.value is not None else result
```
```python
# on_ticket.py:520-531 — the UI consumer side:
for renames_dict, user_facing_message, file_change_requests in get_files_to_change.stream(
        relevant_snippets=..., problem_statement=..., ...):
    planning_markdown = render_fcrs(file_change_requests)
    edit_sweep_comment(user_facing_message + planning_markdown, 2, step_complete=False)
edit_sweep_comment(user_facing_message + planning_markdown, 2)
```

**Flow:** the same function object has two invocation modes — plain `f(...)` silently iterates every yield (discarding progress messages) and returns `StopIteration.value`, falling back to the LAST yield when the producer has no return; `.stream()` hands back the raw generator so interactive callers can render each yield. `fetch_relevant_files` exploits this fully: it yields `(message, RepoContextManager)` snapshots for the comment feed while its return value is only the final manager. `__call__` forwards arguments normally (`self.stream(*args, **kwargs)`); producers that want to self-compose (e.g. `get_top_k_snippets` draining `multi_get_top_k_snippets.stream`) call `.stream()` explicitly and re-yield.
**Invariant:** The RETURN value is the contract; yields are advisory. Any caller that needs the final artifact must use `__call__` semantics (or drain the generator's StopIteration.value) — iterating `.stream()` alone loses the return unless the last yield carries it. Mid-stream consumers must treat each yield as a complete consistent snapshot (Sweep rebuilds the whole RepoContextManager per yield).
**Probe:** No unit test exists for streamable_functions itself (coverage caveat); its `__main__` block documents the dual contract (`return -1` vs yielding 0..9). Deterministic probes at pin: `grep -c 'StopIteration' sweepai/utils/streamable_functions.py` → 1; `grep -c '\*\*kwargs' sweepai/utils/streamable_functions.py` → 2 (signature + forward, no positional-kwargs quirk); `grep -rn '\.stream(' sweepai/utils/ticket_utils.py | wc -l` → 6 self-consumption sites (:157/:216/:313/:329/:437/:526).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "StreamableFunction streamable stream intermediate results", limit: 5 });
// executed at pin: stream :34-37, StreamableFunction.__call__ :17-27,
// streamable :29-30 — all three rows resolve in streamable_functions.py
```

## Verdict
Adopt the wrap-a-generator decorator that preserves normal call syntax while exposing `.stream()`, and the rule that returns are authoritative with yields as disposable progress. Adapt the tuple shapes to your UI events. Omit nothing structural — the wrapper is ~15 lines and the only porting decision is your yield-tuple contract.
