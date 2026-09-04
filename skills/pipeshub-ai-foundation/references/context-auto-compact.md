<!-- capsule-v2 -->
# Atomic-group auto-compaction — how do you bound context tokens without ever splitting an assistant message from its tool results?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What is the head/tail/summary compaction shape that adapts to any message-size distribution?

## Budget-ratio trigger → group partition → protected tail → middle summary
**Path/Symbol:** `backend/python/app/agent_loop_lib/hooks/middleware/builtin/auto_compact.py` — char constants (:14-19), `_SUMMARIZER_SYSTEM/_SUMMARIZER_PROMPT` (21-45, MUST-PRESERVE list incl. citation refs/record IDs/tool returns), `_naive_summary` (:48-82), `make_llm_summarizer` (:85-169), `_build_groups` (:176-214), `shape_auto_compact` (:226-324), `_find_tail_start` (:335-378).
**Signature:** `shape_auto_compact(summarizer=None, trigger_ratio=0.85, max_tail_ratio=0.6, pin_first_n=1)` returning PRE_MODEL middleware mutating `ctx.messages`.
**Data Shape:** groups = atomic units: an AssistantMessage-with-tool_calls PLUS its following ToolMessages (matched by tool_call_id) move together; pinned messages (indices < pin_first_n) each form single-element head groups.

### Decisive source
```python
# auto_compact.py:226-245 — the three-region contract
"""Fires when total tokens exceed trigger_ratio × budget. Splits messages
into three regions:
1. Head (pinned, never compacted) — first pin_first_n messages.
2. Tail (protected recent context) — walking backwards from the end,
   accumulating atomic groups until adding the next would exceed
   max_tail_ratio × budget. Groups are never split: an AssistantMessage
   and its ToolMessages move together.
3. Middle — replaced with a single summary message.
This approach adapts to any message-size distribution: a conversation
with 50 small turns keeps most of them; a conversation with 3 huge
retrieve results protects only what fits the budget."""
```

**Flow:** token count vs budget×0.85 → too small ⇒ passthrough → build groups → walk backwards accumulating tail (always ≥1 group; pinned never in tail) → summarize middle via injected LLM summarizer or naive join → replace `ctx.messages` = head + `[Auto-compacted summary of N earlier message(s)] + summary` + tail. The summarizer formats per-message with artifact-meta awareness and a 100K-char input budget with omission markers; LLM failure falls back to naive; empty LLM output also falls back.
**Invariant:** Provider-mandated pairing is never broken (orphaned ToolMessages handled defensively as singleton groups); compaction is per-call shaping — stored history untouched; the summary prompt demands preservation of IDs/citations/numbers because the summary REPLACES the original messages.
**Probe:** `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_context_compaction.py::test_artifact_compaction_preserves_pairing` (:76), `::test_last_turn_compacted_when_over_budget` (:159), `::test_current_turn_with_schema_compacted_first` (:195); `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_auto_compact_coverage.py::test_resolves_transport_lazily_with_provider` (:157), naive-summary table :112-145.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "shape_auto_compact _build_groups _find_tail_start make_llm_summarizer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt atomic grouping by tool_call_id pairing, backward-walk protected tail, ratio triggers, and the preservation-list summarizer prompt; adapt ratios, char constants, and model/provider resolution to host; omit the naive fallback only if you can guarantee a summarizer. Direct tests pin pairing preservation and region boundaries across budget regimes.
