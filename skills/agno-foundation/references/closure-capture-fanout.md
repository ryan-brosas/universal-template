<!-- capsule-v2 -->
# Fan-out closure capture — why do per-member async delegates need default-arg binding?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** When delegating to all members concurrently, how do you prevent every task from acting on the LAST loop iteration's member?

## Closure bug regression harness
**Path/Symbol:** `libs/agno/tests/unit/team/test_delegate_closure_bug.py:30` (`test_async_closure_captures_correct_agent_identity`); fix pattern in production fan-out loops (e.g. `_default_tools.py` delegate-to-all paths, PR #6067).
**Signature:** test simulates `for member_agent in agents: tasks.append(closure)` then `asyncio.gather`.
**Data Shape:** Python closures capture VARIABLES by reference — a loop variable keeps re-binding, so all deferred tasks observe its final value.

### Decisive source
```python
# BUGGY (PR #6067): every gathered task sees the last agent
for member_agent in agents:
    async def run_agent():
        return member_agent.name            # late binding → always "Worker3"

# FIXED: bind via default argument — evaluated at DEFINITION time
for member_agent in agents:
    async def run_agent(agent=member_agent):
        return agent.name                   # each closure freezes its own agent

results_buggy = await asyncio.gather(*[t() for t in buggy_tasks])
assert len(set(results_buggy)) == 1        # all identical = the bug signature
assert len(set(results_fixed)) == 3        # distinct = fixed
```

**Flow:** build one coroutine per member inside a loop → defer execution with `asyncio.gather` → WITHOUT default-arg binding every coroutine resolves the loop variable at AWAIT time and all act on the final member; WITH `param=value` each function object captures its own cell at definition.
**Invariant:** Any fan-out that closes over a loop variable (member agents, task objects, media lists) must freeze it via a default argument or factory function — this is not a style rule, it is correctness for concurrent dispatch. The repo ships a dedicated regression suite because the bug shipped to production once (#6067).
**Probe:** `tests/unit/team/test_delegate_closure_bug.py` (7 tests incl. streaming-branch variant + early/late-binding demonstrations) — executed GREEN at pin within the 94-pass run.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "delegate closure bug", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the default-arg binding pattern for any loop-spawned concurrent work; nothing host-specific to adapt; omit the test file's mock scaffolding. Direct tests exist and were executed green.
