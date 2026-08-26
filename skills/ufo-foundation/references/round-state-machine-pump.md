<!-- capsule-v2 -->
# Round state-machine pump — How does a session drive an agent FSM to completion without ever raising?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** How does a session loop turn a status-carrying agent into a terminating sequence of states, and what exactly ends a round?

## Round pump over agent status
**Path/Symbol:** `galaxy/session/galaxy_session.py:GalaxyRound.run` (:71-134), `GalaxyRound.is_finished` (:136-151), `GalaxyRound.force_finish` (:153-158); session-level `GalaxySession.force_finish` (:480-493) and `BaseSession.run` (`ufo/module/basic.py`, :509-536).
**Signature:** `async def run(self) -> None`; `def is_finished(self) -> bool`; `def force_finish(self) -> None`.
**Data Shape:** The agent carries `status: str` (`START|CONTINUE|FINISH|FAIL` via `ConstellationAgentStatus`); the round holds `_is_finished: bool` plus the shared context that stores `ContextNames.SESSION_STEP`.

### Decisive source
```python
# BaseSession.run — outer round loop
while not self.is_finished():
    round = self.create_new_round()
    if round is None:
        break
    round_result = await round.run()

# GalaxyRound.run — inner state-machine pump
self._agent.set_state(StartConstellationAgentState())
while not self.is_finished():
    await self._agent.handle(self._context)
    self.state = self._agent.state.next_state(self._agent)
    self._agent.set_state(self.state)
    await asyncio.sleep(0.01)
return self.context.get(ContextNames.ROUND_RESULT)

# finish algebra
if self._is_finished:
    return True
if (self.state.is_round_end()
        or self.context.get(ContextNames.SESSION_STEP)
        >= galaxy_config.constellation.MAX_STEP):
    return True
```
Force-finish composes downward: `GalaxySession.force_finish` sets `_finish=True`, `agent.status="FINISH"`, records `finish_reason`, then delegates to `current_round.force_finish()` which sets the round's `_is_finished` flag — so a manual stop wins over whatever step the FSM was in.

**Flow:** session loop creates rounds until requests dry up or `_finish` → round resets agent into the START state → handle current state → ask that state for `next_state(agent)` (dispatched off `agent.status`) → install it → repeat until terminal-state `is_round_end()`, force-finish flag, or step budget → return `ROUND_RESULT` from context.
**Invariant:** the pump never raises — every exception class (`AttributeError`, `KeyError`, `Exception`) is logged with traceback and swallowed, so one bad round degrades to a logged error instead of killing the session; termination must remain reachable through at least one of {terminal state, force-finish flag, MAX_STEP}.
**Probe:** `tests/unit/galaxy/session/test_galaxy_round_refactored.py:106-210` pins multi-`handle` sequencing across transitions and graceful no-crash behavior on a raising `handle`. Coverage caveat: this suite mocks state names (`StartGalaxyAgentState`) and an `orchestrator=` kwarg that do not match production signatures at this pin — treat only its sequencing claims as live; direct source read `galaxy_session.py:119-158` verified byte-parity of the error funnel and finish algebra.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", query: "round state machine finished force finish session", limit: 10 });
```

## Verdict
Adopt the three-layer shape: outer request-fed session loop, inner status-dispatched FSM pump, finish algebra = explicit flag OR terminal predicate OR step ceiling, with force-finish writing both layers. Adapt the 0.01 s anti-busy-wait and the `SESSION_STEP` counter to your host's step accounting. Omit swallow-all logging if your porter requires fail-fast sessions — but then re-add a session-level error result so the outer loop still terminates.
