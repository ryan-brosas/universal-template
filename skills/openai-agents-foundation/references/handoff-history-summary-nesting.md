<!-- capsule-v2 -->
# Handoff history summary nesting — how does a handoff collapse the transcript for the next agent without losing it, and how does a second handoff un-collapse it?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** How do you interleave lossless items with text summaries of filtered items, keep provenance, and re-flatten prior summaries instead of nesting summaries inside summaries?

## Ordered summary/verbatim interleave + provenance + re-flat
**Path/Symbol:** `src/agents/handoffs/history.py:` `_nest_handoff_history_with_provenance` (:97–157), `_build_ordered_default_history` (:337–373), `_build_summary_message` (:376–398), `_map_run_item_occurrences` (:266–308), `_extract_nested_history_transcript` (:469–491), `_SUMMARY_ONLY_INPUT_TYPES` (:44–49).
**Signature:** `nest_handoff_history(handoff_input_data, *, history_mapper=None) -> HandoffInputData`; `default_handoff_history_mapper(transcript) -> [assistant summary message]`.
**Data Shape:** result input_history = `[summary | verbatim item]*`; owned provenance = `NestedHistoryOwnedItem{run_item, input_index, digest, occurrence_key}` stashed as `_nested_history_owned_items`; summary message = assistant text `preamble\n<CONVERSATION HISTORY>\n1. record\n…\n</CONVERSATION HISTORY>`.

### Decisive source
```python
for plain_input, forward_verbatim, run_item in normalized_items:
    if not forward_verbatim:
        pending_summary.append(plain_input); continue
    if pending_summary or not history_items:
        history_items.extend(default_handoff_history_mapper(pending_summary))
        pending_summary = []
    digest = digest_input_item(plain_input)
    if digest is not None:
        ensure_nested_history_run_item_occurrence_key(run_item)
        owned_items.append(NestedHistoryOwnedItem(
            run_item=run_item, input_index=len(history_items), digest=digest))
    history_items.append(plain_input)
...
nested = handoff_input_data.clone(input_history=tuple(copied_history),
                                  pre_handoff_items=(), input_items=())
```

**Flow:** normalize history (string→items; deep-copy) and FLATTEN any previously nested summary messages by detecting the preamble+wrapper markers and re-parsing numbered records back into items → partition pre/new RunItems dropping ToolApprovalItems → walk in order: summary-only types (`function_call`, `function_call_output`, reasoning) and other non-forwarded items accumulate into the pending summary; verbatim-forwarded items first flush that summary as one assistant message, then append themselves and register ownership (index+digest+occurrence key) → custom mappers replace the default entirely (their return IS the exact model input; nothing appended after) → provenance recovery maps copied filtered items back to original occurrences identity-first, then by occurrence key, consuming each source index at most once.
**Invariant:** chronological order survives (summary segments never swallow or reorder interleaved verbatim items); durable session history is untouched — only the next agent's INPUT collapses; nested summaries flatten before re-summarizing so depth stays 1.
**Probe:** `tests/test_handoff_history_duplication.py::TestHandoffHistoryDuplicationFix::test_summary_and_raw_items_preserve_chronological_order` (:364 asserts 3 items: prior summary / raw answer / handoff summary), `::test_forwarded_items_are_excluded_from_summary_until_the_next_handoff` (:301), `test_bare_role_record_from_an_older_summary_is_recovered` (:2301).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "history.py", query: "nest handoff summary", limit: 30 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.handoffs.history._nest_handoff_history_with_provenance" });
```

## Verdict
Adopt ordered summary|verbatim interleaving with per-verbatim provenance digests and marker-based summary flattening for any agent-to-agent context transfer. Adapt marker strings (`set_conversation_history_wrappers`) and record formatting. Omit occurrence-key mapping if your filters never drop-and-reorder items. Coverage: no_recorded_issue @ gen 2026-08-24T14:05:06Z (parser tail :506–664 map-level only).
