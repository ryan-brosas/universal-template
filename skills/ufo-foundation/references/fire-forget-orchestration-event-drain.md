<!-- capsule-v2 -->
# Fire-and-forget orchestration with a blocking event drain — How does the planner stop blocking the executor it launched?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** How does an agent state start a long-running orchestrator without awaiting it, then still react to every task completion in order?

## Launch-and-continue over asyncio.create_task + queue drain
**Path/Symbol:** `galaxy/agents/constellation_agent_states.py:StartConstellationAgentState.handle` (:67-127) and `ContinueConstellationAgentState.handle` (:182-234).
**Signature:** `async def handle(self, agent: "ConstellationAgent", context: Context) -> None` (both states).
**Data Shape:** `agent.task_completion_queue: asyncio.Queue[TaskEvent]`; each event carries `task_id` and `data["constellation"]` (the orchestrator's live constellation object).

### Decisive source
```python
# StartConstellationAgentState.handle — non-blocking launch
if agent.current_constellation:
    asyncio.create_task(
        agent.orchestrator.orchestrate_constellation(
            agent.current_constellation, metadata=timing_info))
    agent.status = ConstellationAgentStatus.CONTINUE.value

# ContinueConstellationAgentState.handle — blocking drain, no timeout
first_event = await agent.task_completion_queue.get()
completed_task_events.append(first_event)
while not agent.task_completion_queue.empty():
    try:
        event = agent.task_completion_queue.get_nowait()
        completed_task_events.append(event)
    except asyncio.QueueEmpty:
        break
latest_constellation = completed_task_events[-1].data.get("constellation")
```

**Flow:** START state creates the constellation once (`WeavingMode.CREATION`), spawns the orchestrator as a fire-and-forget task so the FSM keeps running, and flips status to CONTINUE; any creation failure funnels into `status=FAIL`. The CONTINUE state blocks indefinitely on the first completion event ("NO timeout here / timeout is handled at task execution level"), coalesces everything already queued behind it, treats the LAST event's constellation as freshest, and hands the batch to `process_editing`.
**Invariant:** the orchestrator task is never awaited by the FSM — progress must be observed exclusively through the queue; the drain must be get-once-blocking + get_nowait-coalescing so a burst of completions triggers exactly one editing pass instead of N.
**Probe:** direct read of `constellation_agent_states.py:182-209` verified byte-parity with the graph-served snippet (blocking get → QueueEmpty-bounded drain). Direct test: `tests/unit/galaxy/session/test_galaxy_round_refactored.py:135-188` pins multi-state handle sequencing; the no-timeout wait itself has no dedicated unit test at this pin (coverage caveat — behavior pinned by source comment and the task-execution-level timeout contract in `TaskStar.execute`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", name_pattern: ".*constellation_agent_states\\..*", limit: 20 });
```

## Verdict
Adopt the decoupling: launch executors as un-awaited tasks, communicate only via a typed completion queue, and coalesce queued events per wake-up to amortize expensive replanning. Adapt where the timeout lives — UFO deliberately pushes per-task timeouts down into execution, keeping the planning loop wait-forever-simple. Omit the WeavingMode context plumbing unless your host distinguishes creation vs editing prompts.
