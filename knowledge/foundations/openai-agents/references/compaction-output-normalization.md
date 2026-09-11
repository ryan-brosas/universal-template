<!-- capsule-v2 -->
# Compacted-output replay normalization — which ids and content shapes does responses.compact emit that the API will refuse on replay?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory project `openai-agents-python`. **Question:** After compaction rewrites history, what must be normalized before the compacted items can legally be sent back as input?

## Three normalizers
**Path/Symbol:** `src/agents/memory/openai_responses_compaction_session.py`: `_strip_orphaned_assistant_ids` (:458–484), `_normalize_compaction_output_items` (:487–507), user-message content repair `_normalize_compaction_user_message` / `_input_image` / `_input_file` (:510–579); applied in `run_compaction` (:244–246) BEFORE the replace transaction.
**Signature:** `def _strip_orphaned_assistant_ids(items: list[TResponseInputItem]) -> list[TResponseInputItem]`.
**Data Shape:** compact output arrives as dicts or pydantic models (dumped `exclude_unset=True, warnings=False` — compact legitimately returns user-style input_text inside ResponseOutputMessage :493–496).

### Decisive source
```python
# Some models (e.g. gpt-5.4) return compacted output that retains assistant message IDs
# even after stripping the reasoning items those IDs reference. Sending these orphaned
# IDs back to ``responses.create`` causes a 400 error because the API expects the paired
# reasoning item for each assistant message ID. (:462-466)
has_reasoning = any(isinstance(item, dict) and item.get("type") == "reasoning" for item in items)
if has_reasoning:
    return items   # ids are fine when their reasoning partners exist
```
Content repair: an `input_image` keeps exactly one of `image_url`/`file_id` else ValueError; an `input_file` needs one of `file_data`/`file_url`/`file_id`; optional `filename`/`detail` forwarded only when non-empty strings.

**Flow:** dump models → rewrite user-message content chunks into minimal replay-valid shapes → strip assistant ids ONLY when NO reasoning item exists anywhere in the compacted output → replace store.
**Invariant:** Assistant-id stripping is a WHOLE-LIST decision, not per-item: with reasoning present the ids pair up and must stay. Repairing shapes per-chunk (raise on neither-url-nor-file) beats silently dropping the chunk — a dropped image silently changes what the model believes happened.
**Probe:** `grep -n "def _strip_orphaned_assistant_ids" src/agents/memory/openai_responses_compaction_session.py` → 1 hit at :458. Direct tests: class `TestStripOrphanedAssistantIds`: `test_noop_when_empty` (:1645), `test_strips_id_from_assistant_when_no_reasoning` (:1648), `test_preserves_id_when_reasoning_present` (:1665) in tests/memory/test_openai_responses_compaction_session.py.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_strip_orphaned_assistant_ids compaction normalize output items", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt post-compaction normalization (orphan-id gate + content-shape repair); adapt to your provider's compact output quirks; omit gpt-5.4-specific comments. Direct tests pin all three strip/preserve branches.
