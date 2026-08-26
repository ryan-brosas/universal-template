<!-- capsule-v2 -->
# Max-turns vs guardrail race — why must the max-turns exception be recorded exactly once in a streaming run?

**Source:** OpenAI Agents Python MIT `main@fe45b415` (fix 1a55d70 #4606); Codebase Memory project `openai-agents-python`. **Question:** In `RunResultStreaming._check_errors`, what happens when the turn budget trips on the SAME event drain where an input-guardrail tripwire lands — and which flag fixes it?

## The one-shot latch
**Path/Symbol:** `src/agents/result.py`: `_check_errors` (:1042–1090); latch field `_max_turns_handled: bool = field(default=False, repr=False)` (:669); fix adds the set at :1056.
**Signature:** `def _check_errors(self) -> None`.
**Data Shape:** `_check_errors` runs repeatedly (once per streamed event consumption), so every branch is re-evaluated each time.

### Decisive source
```python
if (self.max_turns is not None
        and self.current_turn > self.max_turns
        and not self._max_turns_handled):
    max_turns_exc = MaxTurnsExceeded(f"Max turns ({self.max_turns}) exceeded")
    max_turns_exc.run_data = self._create_error_details()
    self._stored_exception = max_turns_exc
    self._max_turns_handled = True          # ← the one-line fix (1a55d70)

# Fetch all the completed guardrail results from the queue and raise if needed
while not self._input_guardrail_queue.empty():
    guardrail_result = self._input_guardrail_queue.get_nowait()
    if guardrail_result.output.tripwire_triggered:
        tripwire_exc = InputGuardrailTripwireTriggered(guardrail_result)
        ...
        self._stored_exception = tripwire_exc   # guardrail OVERWRITES max-turns — intended
```
`_stored_exception` is a single slot: later assignments WIN. Without the latch, every subsequent drain re-stamps MaxTurnsExceeded, clobbering a tripped input-guardrail exception that arrived after the budget breach.

**Flow:** budget exceeded → store MaxTurnsExceeded once and LATCH → same or later drains may still overwrite with a tripped input guardrail (deliberate precedence: the safety signal outranks the bookkeeping limit) → nothing may resurrect the max-turns error afterwards. Pre-fix behavior: max_turns clobbered the guardrail tripwire in streaming when both fired near-simultaneously.
**Invariant:** Terminal-exception assignment must be idempotent per cause but overridable by higher-priority causes; "store once then stop storing" is the mechanism that lets priority emerge from ordering rather than comparison logic.
**Probe:** `grep -n '_max_turns_handled' src/agents/result.py` → 3 hits (:669 default False, :1051 gate, :1056 set). Direct tests: `tests/test_stream_input_guardrail_timing.py` (timing matrix incl. the guardrail-vs-maxturns ordering cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_check_errors _max_turns_handled stored_exception guardrail queue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-shot terminal-error latch for streaming result objects; adapt which exceptions take precedence; omit OpenAI exception types. Extends `streaming-persistence-gates` (same drain loop, error plane).
