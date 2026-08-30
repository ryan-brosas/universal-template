<!-- capsule-v2 -->
# Termination algebra — what breaks when you reuse a satisfied condition or combine AND/OR?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** What is the contract of a termination condition across calls, and why do AND and OR raise different exception types?

## Delta-consuming callables with mandatory reset
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/base/_termination.py` (`TerminationCondition` :15–85, `AndTerminationCondition.__call__` :105–121, `OrTerminationCondition.__call__` :156–165).
**Signature:** `async def __call__(self, messages: Sequence[BaseAgentEvent | BaseChatMessage]) -> StopMessage | None`; combinators via `__and__`/`__or__`.
**Data Shape:** Conditions are STATEFUL: each call receives only the delta since the last call; `terminated` property latches satisfaction; `reset()` is required before reuse. AND accumulates `_stop_messages` across deltas until all children fired.

### Decisive source
```python
class TerminatedException(BaseException): ...     # NOT Exception

# AND:
if self.terminated:
    raise TerminatedException("Termination condition has already been reached.")
stop_messages = await asyncio.gather(*[condition(messages) for condition in self._conditions if not condition.terminated])
...
if any(stop_message is None for stop_message in stop_messages):
    return None                                   # ALL must fire within their windows

# OR:
if self.terminated:
    raise RuntimeError("Termination condition has already been reached")
stop_messages = await asyncio.gather(*[condition(messages) for condition in self._conditions])
```

**Flow:** manager feeds each response delta to the condition chain → first non-None StopMessage ends the chat → manager resets conditions + turn counter → next `run()` starts clean.
**Invariant:** calling a satisfied condition raises BEFORE evaluating children (prevents silently swallowing a second stop); AND's exception is `TerminatedException(BaseException)` while OR uses plain `RuntimeError` — code catching only `Exception` will crash through `TerminatedException`, which is deliberate so a reused AND cannot be absorbed by normal error handling; AND skips already-terminated children in the gather but keeps their earlier StopMessages joined into the final content/source strings.
**Probe:** `python/packages/autogen-agentchat/tests/test_termination_condition.py::test_and_termination` / `::test_or_termination` (combination semantics incl. stop-message joining); `::test_max_message_termination` (delta counting).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "TerminationCondition AndTerminationCondition OrTerminationCondition reset terminated", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt delta-consuming stateful conditions with an explicit reset protocol and operator composition — it keeps any stop policy declarative. Adapt which exception base reused-condition triggers on (but keep it OUTSIDE normal handling). Omit pydantic Component serialization unless you need declarative save/load of teams.
