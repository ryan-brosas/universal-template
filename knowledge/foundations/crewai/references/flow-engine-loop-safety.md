<!-- capsule-v2 -->
# Flow engine loop-safety — how does the event runtime bound infinite listener cycles and dedupe or_() triggers?

**Source:** crewAI MIT `main@f4731f5025f861c78e3af0487cc80bf5e7c64782`; Codebase Memory `ext-crewAI`. **Question:** How does the Flow runtime detect runaway listener loops, track pending multi-event conditions, and allow cyclic re-execution safely?

## _execute_single_listener / _condition_met / _find_triggered_methods
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py:3938L module`; loop guard `:3248-3256`, completed/resume handling `:3258-3281`, condition bookkeeping `_condition_met`/`_find_triggered_methods` `:3181-3215`, kickoff sync→async bridge `:2026-2089`.
**Signature:** `def _execute_single_listener(self, listener_name, result, triggering_event_id=None) -> tuple[Any, str | None]`.
**Data Shape:** `_pending_events: dict[PendingListenerKey, set[str]]` (events seen per subscription), `_fired_or_listeners: set` (or_-listeners already run this cycle), `_completed_methods: set`, `_method_call_counts: dict[str, int]`, field `max_method_calls: int = 100`.

### Decisive source
```python
count = self._method_call_counts.get(listener_name, 0) + 1
if count > self.max_method_calls:
    raise RecursionError(
        f"Method '{listener_name}' has been called {self.max_method_calls} times in "
        f"this flow execution, which indicates an infinite loop. "
        f"This commonly happens when a @listen label matches the method's own name.")
self._method_call_counts[listener_name] = count

if listener_name in self._completed_methods:
    if self._is_execution_resuming:
        ...  # resume: skip execution but CONTINUE downstream listeners
    # "For cyclic flows, clear from completed to allow re-execution"
    self._completed_methods.discard(listener_name)
    # "...Only discarding the individual listener is insufficient because
    #  downstream or_() listeners (e.g., method_a listening to
    #  or_(handler_a, handler_b)) would remain suppressed across iterations."
    self._clear_or_listeners()

def _condition_met(self, condition, trigger_method, subscription_key) -> bool:
    seen = self._pending_events.setdefault(subscription_key, set())
    seen.add(str(trigger_method))
    if not _condition_satisfied(condition, seen):
        return False
    del self._pending_events[subscription_key]   # consume — fires ONCE per cycle
    return True
```

**Flow:** Every emitted method-finished event scans listeners (`router_only` split pass); or_-listeners additionally skip if already fired this cycle; satisfied conditions fire and clear their pending set. Sync `kickoff` detects a running loop via `asyncio.get_running_loop()` and bridges through a single-worker ThreadPoolExecutor running `asyncio.run(_run_flow())` with copied contextvars (nested-loop safety); streaming kickoff returns a session instead of blocking.
**Invariant:** The call-count ceiling is per-method-per-execution and its error message names the classic cause (a label equal to the method's own name → self-loop). Cycle re-entry must reset BOTH the completed marker AND all fired-or-listener markers, else second iterations silently no-op — the comment documents this exact bug class. Resume mode is the ONLY case where a completed method skips while still propagating.
**Probe:** Deterministic anchors at this pin: `grep -n 'max_method_calls' lib/crewai/src/crewai/flow/runtime/__init__.py` → lines 590 (field default 100), 240 (`max_method_calls = max_iter * 10` executor setup), 3249-3251 (guard); `grep -n '_clear_or_listeners' …runtime/__init__.py` ≥2 sites.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "Flow kickoff_async listener recursion max_method_calls", limit: 6, detail: "ids" });
```

## Verdict
Adopt per-listener call budgets + consumed-pending-set conditions + full-cycle reset semantics; adapt the bridge strategy to your async host; omit checkpoint/persistence branches (`apply_checkpoint`, `_checkpoint_state_for_ask`) unless porting durability too.
