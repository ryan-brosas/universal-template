<!-- capsule-v2 -->
# Typed completion-event gate — What stops malformed or irrelevant events from waking the planner?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** How does the completion queue enforce that only genuine terminal task events reach the editing state, and who is allowed to produce them?

## Producer-side type-and-kind whitelist
**Path/Symbol:** `galaxy/agents/constellation_agent.py:ConstellationAgent.add_task_completion_event` (:595-630); producer chain resolved by trace: `galaxy/session/observers/base_observer.py:ConstellationProgressObserver.on_event` / `_handle_task_event`.
**Signature:** `async def add_task_completion_event(self, event: TaskEvent) -> None`.
**Data Shape:** Accepts only `TaskEvent` instances whose `event_type ∈ {TASK_COMPLETED, TASK_FAILED}`; queue put failures are re-raised as `RuntimeError`.

### Decisive source
```python
if not isinstance(event, TaskEvent):
    raise TypeError(
        f"Expected TaskEvent instance, got {type(event).__name__}. "
        f"Only TaskEvent instances can be added to the task completion queue.")

if event.event_type not in [EventType.TASK_COMPLETED, EventType.TASK_FAILED]:
    raise TypeError(
        f"Expected TaskEvent with event_type in [TASK_COMPLETED, TASK_FAILED], "
        f"got {event.event_type}.")

try:
    await self._task_completion_queue.put(event)
except asyncio.QueueFull as e:
    raise RuntimeError(f"Task completion queue is full: {str(e)}") from e
```

**Flow:** orchestrator publishes a TaskEvent → `ConstellationProgressObserver.on_event` routes it to `_handle_task_event` → the observer calls `add_task_completion_event`, the single gated producer API → invalid type or non-terminal kind raises TypeError at the publisher instead of poisoning the consumer → valid terminal events land in the queue that `ContinueConstellationAgentState.handle` blocks on.
**Invariant:** the queue contains ONLY terminal (completed/failed) TaskEvents — progress/start events must never wake the editor; gate failures surface at publish time (loud) rather than as consumer confusion (silent).
**Probe:** `search_code(project="ufo", pattern="task_completion_queue", path_filter="^galaxy/")` returned exactly 4 symbol hits — this gate (:619), the queue property (:580-585), `__init__` (:87), and the Continue-state consumer (:194-200) — proving the gated method is the only production write path. Direct test: no dedicated unit test for the gate at this pin (coverage caveat); behavior pinned by direct source read of :595-630 and inbound trace showing ConstellationProgressObserver as the sole caller.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", name_pattern: ".*add_task_completion_event.*", limit: 10 });
```

## Verdict
Adopt the pattern: one whitelisted producer method per queue, validating both runtime type AND event semantics (terminal-only) at enqueue time. Adapt the exception style to your host's error taxonomy (UFO raises TypeError/RuntimeError eagerly). Omit the observer indirection if your executor can call the gate directly — but keep exactly ONE write path so the whitelist stays enforceable.
