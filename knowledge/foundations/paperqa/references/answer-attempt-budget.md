<!-- capsule-v2 -->
# Answer-attempt budget — how does the environment stop an agent that keeps trying to answer forever?

**Source:** paper-qa Apache-2.0 `main@57e89f72`; Codebase Memory `paper-qa`. **Question:** When an optional cap on answer attempts is configured, how is it counted and what success semantics does hitting it produce?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/agents/env.py:PaperQAEnvironment._has_excess_answer_failures` (:295-305) + `PaperQAEnvironment.step` (:309-346).
**Signature:** `def _has_excess_answer_failures(self) -> bool`; `async def step(self, action: Message) -> tuple[Messages, float, bool, bool]`.
**Data Shape:** Budget knob `settings.answer.max_answer_attempts: int | None` (None disables). Counter source is the session's own `tool_history: list[list[str]]` of recorded tool names — no separate failure flag exists; ANY gen_answer invocation past the cap ends the episode.

### Decisive source
```python
if self._settings.answer.max_answer_attempts is None:
    return False
return (sum(tn == GenerateAnswer.gen_answer.__name__
            for s in self.state.session.tool_history
            for tn in s)
        > self._settings.answer.max_answer_attempts)
...
async def step(self, action):
    # Record before the type check so the cost gets recorded even if the action was the wrong type
    self.state.record_action(action)
    ...
    done = any(isinstance(msg, ToolResponseMessage) and msg.name == Complete.complete.__name__
               for msg in response_messages)
    if not done and self._has_excess_answer_failures():
        # we consider this done, but we cannot determine success because we're not calling the complete tool
        self.state.session.has_successful_answer = None
        done = True
    return response_messages, self.USE_POST_PROCESSED_REWARD, done, False  # caller determines truncations
```

**Flow:** each environment step records the action FIRST (cost survives malformed input), executes tool calls with per-tool concurrency flags, checks for the Complete tool → done; otherwise consults the budget → if exceeded, terminates WITHOUT calling Complete and marks `has_successful_answer = None`. Truncation detection is deliberately left to the caller (fourth tuple element always False).
**Invariant:** Hitting the budget is UNKNOWN-success, not failure — a three-state outcome (`True` / `False` / `None`) distinct from Complete's explicit verdicts; downstream status normalization must preserve `None` rather than coercing it into FAIL.
**Probe:** No test exercises `max_answer_attempts` (grep over tests/ found zero matches — recorded as an honest probe gap); behavior pinned by direct source read of env.py :295-346 plus inbound trace (`step` sole in-repo caller). Adjacent observable: `tests/test_agents.py::test_gather_evidence_rejects_empty_docs` (:562-614) shows TRUNCATED as the terminal status when steps run out. Deterministic source probe only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "max_answer_attempts has_successful_answer step", limit: 10 });
// trace_path --project paper-qa --function-name _has_excess_answer_failures --direction both → PaperQAEnvironment.step
```

## Verdict
Adopt the tool-history-derived counter (no duplicate bookkeeping), the record-before-validate step ordering, and the tri-state success semantics on budget exhaustion; adapt `tool_history` to your framework's action log shape; omit ldp/reward plumbing (USE_POST_PROCESSED_REWARD is RL-host-specific). Coverage: agents/env.py no_recorded_issue + metadata_match @ gen 2026-08-25T19:57:59Z.
