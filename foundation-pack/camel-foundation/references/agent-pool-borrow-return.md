<!-- capsule-v2 -->
# AgentPool borrow/return — How do you reuse expensive LLM agent instances across parallel task executions?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What does a correct async object pool for cloneable agents look like — sizing, blocking, idle reaping, and reset discipline?

## Condition-guarded deque pool keyed by id()
**Path/Symbol:** `camel/societies/workforce/single_agent_worker.py:AgentPool` (:54-197), wired in `SingleAgentWorker` (:275-313).
**Signature:** `AgentPool(base_agent, initial_size=1, max_size=10, auto_scale=True, idle_timeout=180.0, cleanup_interval=60.0)`; `async get_agent() -> ChatAgent`; `async return_agent(agent) -> None`; `async cleanup_idle_agents() -> None`.
**Data Shape:** `_available_agents: deque`, `_in_use_agents: Set[int]` (id()), `_agent_last_used: Dict[int, float]`; one `asyncio.Lock` + `asyncio.Condition(self._lock)` shared.

### Decisive source
```python
async with self._condition:
    while True:
        if self._available_agents:
            agent = self._available_agents.popleft()
            self._in_use_agents.add(id(agent)); self._pool_hits += 1
            agent.reset(); return agent
        if len(self._in_use_agents) < self.max_size or self.auto_scale:
            agent = self._create_fresh_agent()   # base_agent.clone(with_memory=False)
            self._in_use_agents.add(id(agent)); return agent
        await self._condition.wait()
```

**Flow:** borrow prefers pooled (reset BEFORE handout = clean memory state), else creates fresh when under max or auto-scaling, else blocks on the condition; `return_agent` silently ignores foreign ids (`if agent_id not in self._in_use_agents: return`), resets, records last-used time, appends + `notify()` ONE waiter — but only `if len(available) < max_size`, else drops tracking and lets GC eat it; `cleanup_idle_agents` runs on a sidecar loop started inside `_listen_to_channel` (:585-596) every `cleanup_interval` and removes only AVAILABLE agents idle past `idle_timeout` (auto_scale gate). Stats counters (`total_borrows/total_clones_created/pool_hits/agents_cleaned`) expose hit-rate.
**Invariant:** Borrowed agents are CLONES of the base (`clone(with_memory=False)`), so per-task memory isolation comes from cloning, not pooling; the pool never hands out an unreset agent twice. Return of an over-max agent must still discard its in-use mark.
**Probe:** `grep -c 'notify()' camel/societies/workforce/single_agent_worker.py` → 1; `grep -n 'idle_timeout' camel/societies/workforce/single_agent_worker.py | head -2` → :80/:177 region hits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "AgentPool get_agent return_agent cleanup_idle_agents", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the id()-keyed in-use set + condition-wait borrow + notify-one return for any costly cloneable resource. Adapt clone semantics to your agent type. Omit workflow-memory accumulator wiring (`_conversation_accumulator`) — separate concern.
