<!-- capsule-v2 -->
# Streamed interruption & handoff save variants — why do resume, handoff, and fresh turns use different persistence callbacks?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** Which save callback does each next-step outcome use in the streamed loop, and why does the resumed handoff path skip the tool-guardrail accumulation?

## Save-callback routing table
**Path/Symbol:** `src/agents/run_internal/run_loop.py:` `_save_resumed_items` (:1072–1083), `_save_stream_items_with_count` / `_without_count` (:1085–1111), `_save_max_turns_items` (:1113–1132), `_save_resumed_stream_items` (:361–389), `_save_stream_items` (:392–421); consumption at the resume block (:1301–1369), handoff (:1711–1731), interruption (:1748–1772), run-again (:1773–1784).
**Signature:** closures over `(items: list[RunItem], response_id: str | None, store_setting: bool | None)`.

### Decisive source
```python
# The non-streaming resume path extends its run-wide lists before finalizing
# but skips a resumed turn that loops back to the same model, so a guardrail that
# re-runs for the same tool call on resume is not counted twice.
if not isinstance(turn_result.next_step, NextStepRunAgain):
    _accumulate_tool_guardrail_results(streamed_result, turn_result)
```
Resume turns pass `_save_resumed_items` (which threads `persisted_count` through `save_resumed_turn_items`, returning the updated count into `streamed_result._current_turn_persisted_item_count`); fresh turns pass `_save_stream_items_with_count` (count mirrored from run state AFTER `save_result_to_session`) except HANDOFFS which deliberately use `_save_stream_items_without_count` (the agent transition owns subsequent counting); interruptions always save BEFORE `_complete_stream_interruption` sets `interruptions`, `_last_processed_response`, `is_complete`, sentinel.

**Flow (per outcome):** Handoff → save-without-count → swap agent → publish `AgentUpdatedStreamEvent` → finish span → reset start-hooks flag → set state step `NextStepRunAgain` → await consumer-drain gate (which also honors `after_turn` cancel). FinalOutput → finalize-final-output (see its capsule) → clear step → break. Interruption → mirror raw responses/generated/session items into run state FIRST (so approval resume has full context) → save → complete-interruption. RunAgain → zero the persisted counter → save-with-count → drain gate.

**Invariant:** A resumed turn must never double-count already-persisted items — the count travels with the result, not the module; handoff saves must not advance the new agent's counter; interruption completion happens strictly after persistence so a crash between them leaves recoverable state.

**Probe:** `tests/test_run_state_pending_input.py::test_streamed_resume_matches_pending_input_ordering` (:172) and `tests/test_agent_runner_streamed.py` resume suites pin ordering/no-duplication.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "save stream items persisted count resumed turn interruption", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the callback-per-outcome routing and the count-travels-with-result invariant; adapt closure shapes to your persistence API; omit the drain-gate details if your consumers are synchronous.
