<!-- capsule-v2 -->
# Serialized approval-ownership relink (schema 1.17) — how does a resumed run re-attach the CURRENT response's items by identity instead of value?

**Source:** OpenAI Agents Python MIT `main@fe45b415` (fix b354ef0 #4613); Codebase Memory project `openai-agents-python`. **Question:** After serialize→deserialize, `processed_response.new_items` and `interruptions` are rebuilt as NEW objects — what breaks when later-turn logic compares them to the generated-history items, and what must the snapshot store to fix it?

## Ownership record + guarded relink
**Path/Symbol:** `src/agents/run_state.py`: `_current_response_generated_item_ownership` (:1464–1503, serialized under key `current_response_generated_item_ownership`), `_restore_current_response_item_identities` (:5469–5570), gate `_CURRENT_RESPONSE_OWNERSHIP_MIN_SCHEMA_VERSION = "1.17"` (:185, applied at :4310–4319); schema summary updated: 1.17 = "Docker container labels AND current-response generated-item ownership" (:217–220).
**Signature:** `def _current_response_generated_item_ownership(self, generated_items: Sequence[RunItem]) -> dict[str, Any] | None` returning `{start, end, interruptions}`.
**Data Shape:** ownership is recorded ONLY when `_last_processed_response` exists, current step is `NextStepInterruption`, processed items are a UNIQUE contiguous identity subsequence of generated items (`candidate_starts` must be exactly 1 via `is` comparison), and every interruption maps to exactly one index.

### Decisive source
```python
# restore side — every guard must pass or the relink is SKIPPED entirely (fail-open to copies):
source_indexes = [*range(source_start, processed_end), *interruption_indexes]
...
# The complete current response must be the same terminal suffix in both histories.
session_start = len(state._session_items) - len(restored_current_response_items)
if session_start < 0 or any(
    generated_item is not session_item
    for generated_item, session_item in zip(
        restored_current_response_items,
        state._session_items[session_start:], strict=True))
    return
processed_response.new_items = restored_processed_items          # identity relink
current_step.interruptions = cast(list[ToolApprovalItem], restored_interruptions)
```
Restore guards: exact int types, `end == len(serialized_generated_items)`, `processed_end <= source_end` ("Handoff filters can clear prior items without resetting the model turn count"), interruption indexes within `(processed_end, source_end)`, unique, byte-equal expected payloads, unique restored-source mapping, all interruptions are `ToolApprovalItem`s, terminal-suffix identity against session items.

**Flow:** at save time record the response's [start,end) window plus which indexes are interruptions → at load time verify EVERY structural expectation → only then point `new_items`/`interruptions` back at the SAME live objects as `_generated_items`. Pre-1.17 blobs skip restoration (legacy behavior preserved).
**Invariant:** Identity relink must be all-or-nothing; a half-matched relink would alias wrong items. The bug this fixes: an output-guardrail tripwire on a LATER turn mis-owned items after resume (accepted outputs from other turns got withheld/mixed).
**Probe:** `grep -n '_CURRENT_RESPONSE_OWNERSHIP_MIN_SCHEMA_VERSION =' src/agents/run_state.py` → 1 hit at :185. Direct tests: `tests/test_agent_runner_streamed.py::test_serialized_later_turn_approval_with_output_guardrail_resumes` (:2578), `...test_serialized_mixed_approval_guardrail_preserves_only_accepted_outputs`, `...test_serialized_filtered_handoff_approval_with_empty_prefix_resumes`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_restore_current_response_item_identities ownership interruptions relink", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt snapshot-recorded ownership windows + fail-open guarded identity relink for any resumable engine that rebuilds object graphs; adapt schema-version gating style; omit OpenAI's RunState field names. Extends `versioned-snapshot-contract` (schema 1.17 shows the stamp-every-write discipline in action).
