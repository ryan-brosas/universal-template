<!-- capsule-v2 -->
# Agent message compaction — cadence+floor-gated history summarization

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does a long-running agent keep its prompt bounded without losing task progress, decisions, or sensitive data?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/message_manager/service.py` (600 lines): `MessageManager` (:104) — `maybe_compact_messages` (:216-302), `create_state_messages` (:424), `_filter_sensitive_data` (:577), `add_new_task` (:191), `get_messages` (:548); state on `AgentMessageManagerState {compacted_memory, compaction_count, last_compaction_step, agent_history_items, read_state_description}`; settings via `MessageCompactionSettings`.
**Signature:** `maybe_compact_messages(llm, settings, step_info) -> bool` — fires only when BOTH gates pass: step cadence (`step_number - last_compaction_step >= compact_every_n_steps`) AND char floor (`len(history_text) >= trigger_char_count`, default 40k).
**Data Shape:** compaction input = tagged sections (`<previous_compacted_memory>`, `<agent_history>`, `<read_state>`); output summary replaces all but the first + last N history items.

### Decisive source
```ts
# dual gate: cadence OR floor alone never triggers
steps_since = step_info.step_number - (state.last_compaction_step or 0)
if steps_since < settings.compact_every_n_steps: return False
if len(full_history_text) < trigger_char_count: return False
# sensitive data filtered BEFORE the summarizer sees it
if self.sensitive_data:
    compaction_input = self._filter_sensitive_data(UserMessage(content=compaction_input)).text
# anti-hallucination instruction in the summarizer system prompt:
# 'Only mark a step as completed if you see explicit success confirmation...
#  Never infer completion from context — mark it "IN-PROGRESS"'
summary = (await llm.ainvoke([SystemMessage(prompt), UserMessage(compaction_input)])).completion
# retention: first item + most recent keep_last_items survive
self.state.agent_history_items = [history_items[0]] + history_items[-keep_last:]
```

**Flow:** each step → gates checked → on fire, history serialized to tagged text → sensitive values redacted → LLM summarizes into a rolling `compacted_memory` block (fed back as `<previous_compacted_memory>` next time → recursive memory of memory) → history truncated to anchor + recent tail. Failure to summarize is non-fatal (returns False, run continues un-compacted).
**Invariant:** compaction is lossy but anchored (first item kept); summaries are capped and re-capped; secrets never reach the summarizer LLM; completion claims require explicit confirmation in-source.
**Probe:** `tests/agent/` tests (gates both required; previous memory included in input; truncation keeps first+last; sensitive filtering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "maybe_compact_messages MessageManager compacted_memory sensitive_data history", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-gated (cadence+size) rolling compaction with recursive memory blocks, secret pre-redaction, and strict no-inferred-completion instructions; adapt thresholds to host token budgets.
