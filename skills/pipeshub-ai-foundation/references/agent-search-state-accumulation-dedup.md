<!-- capsule-v2 -->
|# Agent-search state accumulation dedup — how does a stateful search tool let parallel/repeat calls share one citation pool without double-counting blocks?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** An LLM fires several knowledge searches in one wave (one per source) and may repeat a query later — where does dedup live so the final citation set never contains the same block twice?

## Key-based append into the shared ChatState list
**Path/Symbol:** `backend/python/app/agents/actions/retrieval/retrieval.py` `_block_accumulation_key` (L55–61) + `_dedupe_append_final_results` (L64–83); write site inside `search_internal_knowledge` L561–564.
**Signature:** `_block_accumulation_key(entry: dict) -> str | None`; `_dedupe_append_final_results(existing: list[dict], new_blocks: list[dict]) -> list[dict]`.
**Data Shape:** key = `f"{virtual_record_id}_{block_index}"`; `None` when either part is missing. State keys: `final_results` (list of flattened block dicts), plus sibling maps `virtual_record_id_to_result`, `tool_records`.

### Decisive source
```python
def _block_accumulation_key(entry):
    virtual_record_id = entry.get("virtual_record_id")
    block_index = entry.get("block_index")
    if virtual_record_id is None or block_index is None:
        return None                       # incomplete ⇒ NEVER deduped
    return f"{virtual_record_id}_{block_index}"

def _dedupe_append_final_results(existing, new_blocks):
    if not isinstance(existing, list): existing = []
    seen_keys = {key for entry in existing
                 if (key := _block_accumulation_key(entry)) is not None}
    appended = list(existing)
    for entry in new_blocks:
        key = _dedupe...key(entry)
        if key is None or key not in seen_keys:
            if key is not None: seen_keys.add(key)
            appended.append(entry)
    return appended
```
(L55–83; write: `self.state["final_results"] = _dedupe_append_final_results(existing, final_results)`.)

**Flow:** each tool call reads `state["final_results"]` → merges this call's blocks through the key filter → writes the merged list back → next call in the same wave sees the accumulated pool.
**Invariant:** (1) Dedup is FIRST-WINS on `(virtual_record_id, block_index)` — content differences don't matter, identity does. (2) Entries with a missing key part are always appended (never silently dropped). (3) The merge returns a NEW list; the state write is whole-value replacement, safe because asyncio single-loop semantics serialize the read-modify-write between awaits. (4) The sibling record map uses `{**existing, **new}` and `tool_records` dedups on `_id` — three shapes, one "accumulate without inflation" goal.
**Probe:** EXECUTED at pin: `tests/unit/agents/actions/test_retrieval.py::TestBlockDedupOnAccumulation` — dup block skipped keeping first content (:356–365), incomplete-key entries all kept (:367–374), two overlapping single-source calls leave exactly 1 block in `state["final_results"]` (:377–410).
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` file_pattern=`*agents/actions/retrieval*` query="dedupe append final results block accumulation key parallel calls state" → resolves exactly `_dedupe_append_final_results` + `_block_accumulation_key` (rank −56.89/−39.14).

## Verdict
Adopt key-based first-wins append whenever parallel agent tools write into one shared result/citation pool keyed by state. Adapt the key to your domain identity pair; adapt storage to your run-state object. Omit the incomplete-key escape hatch ONLY if your schema guarantees both identity fields on every block.

<!-- capsule-evidence: pipeshub-ai@68509725e15c retrieval.py L55–83/L561–564; tests test_retrieval.py TestBlockDedupOnAccumulation; live search_graph 2026-08-26 -->
