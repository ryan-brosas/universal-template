<!-- capsule-v2 -->
# Latest-wins dedupe with causal anchors — how do you drop stale tool outputs without reordering history?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory project `openai-agents-python`. **Question:** When the same stable identity appears twice in input history (retried call, re-sent output), which occurrence survives and WHERE does it sit?

## Two-pass anchor-preserving rewrite
**Path/Symbol:** `src/agents/run_internal/items.py`: `deduplicate_input_items_preferring_latest` (:768–800), key builder `_dedupe_key` (:681–712), anchor set `_DEDUPE_EARLIEST_ANCHOR_ITEM_TYPES` (:40–42); plain first-wins variant `deduplicate_input_items` (:752–765).
**Signature:** `def deduplicate_input_items_preferring_latest(items: Sequence[TResponseInputItem]) -> list[TResponseInputItem]`.
**Data Shape:** dedupe keys exist ONLY for identified non-message items: `call_id:<type>:<id>` for tool-call/output types, `id:<type>:<id>` for item ids (`FAKE_RESPONSES_ID` ignored so call_id dedupe stays possible :698–700), `approval_request_id:<type>:<id>` for hosted-MCP responses. Messages/role items and unidentified items return None → always kept.

### Decisive source
```python
# (:784-791) latest value wins...
latest_by_key[dedupe_key] = item
if (dedupe_key not in anchor_index_by_key
        or item_type not in _DEDUPE_EARLIEST_ANCHOR_ITEM_TYPES):
    anchor_index_by_key[dedupe_key] = index
# ...but anchors stay at their EARLIEST position (:793-799)
elif anchor_index_by_key[dedupe_key] == index:
    deduplicated.append(latest_by_key[dedupe_key])
```
Anchor types = all `_TOOL_CALL_TO_OUTPUT_TYPE` keys+values plus `mcp_approval_request` and `reasoning` — items that must keep their position relative to required followers.

**Flow:** pass 1 records the LATEST payload per key but freezes the anchor index at the earliest occurrence of anchor-typed items → pass 2 emits every unique/unidentified item at its own position and, at each anchor's original slot, substitutes the latest payload. Net effect: a retried call keeps its original early slot (so its output still follows it), while a re-sent output is emitted at its LATEST position (a corrected value never time-travels before the call it answers).
**Invariant:** Causal order is untouchable: a call may not move behind its follower; an approval response may not move before its request. Naive "keep last" or "keep first" both break one side of this.
**Probe:** `grep -c '_DEDUPE_EARLIEST_ANCHOR_ITEM_TYPES' src/agents/run_internal/items.py` → 2 (def :40, use :789). Direct tests: `tests/test_run_internal_items.py::test_deduplicate_input_items_preferring_latest_keeps_latest_output_position` (:1058), `..._keeps_output_after_matching_call` (:1078), `..._keeps_reasoning_before_follower` (:1103), `..._keeps_approval_request_before_response` (:1138).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "deduplicate_input_items_preferring_latest dedupe key anchor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-pass latest-value/earliest-anchor dedupe for any replayable event log with causal pairs; adapt the key vocabulary to your item schema; omit approval_request_id handling if you have no hosted approvals. Companion to `tool-invocation-dedup-gate` (that gate validates within-run reuse; this ladder cleans cross-turn duplicates).
