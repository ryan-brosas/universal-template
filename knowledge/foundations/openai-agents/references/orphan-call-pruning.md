<!-- capsule-v2 -->
# Orphan-call pruning with reasoning cascade — what must be deleted together when a tool call has no output?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory project `openai-agents-python`. **Question:** Before resuming or retrying from stored history, how do you remove calls whose outputs are gone WITHOUT leaving the API-rejected residue behind them?

## The orphan ladder
**Path/Symbol:** `src/agents/run_internal/items.py`: `drop_orphan_function_calls` (:171–271) + `_drop_reasoning_items_preceding_dropped_calls` (:274–304); helpers `_completed_call_ids_by_type` (:964–978), `_get_program_caller_id` (:1007–1015), `_is_pending_hosted_shell_call` (:1018–1023), `_matched_anonymous_tool_search_call_indexes` (:1045–1068); call→output type table `_TOOL_CALL_TO_OUTPUT_TYPE` (:29–38).
**Signature:** `def drop_orphan_function_calls(items, *, pruning_indexes: set[int] | None = None, output_pruning_indexes: set[int] | None = None) -> list[TResponseInputItem]`.
**Data Shape:** `pruning_indexes` restricts which items may DROP; `output_pruning_indexes` marks unambiguous stored history whose OUTPUTS may also drop if their call vanished.

### Decisive source
```python
# Reasoning items that immediately precede a dropped call are removed too — the Responses
# API rejects reasoning without its following item:
# "Item 'rs_...' of type 'reasoning' was provided without its required following item"(:183-185)
```
Program lifecycle: a `program` call with no `program_output` is scanned for retained program-OWNED items (hosted tool calls/outputs via `caller.caller_id`) — any retained child keeps the program ACTIVE; none ⇒ the whole program-owned chain drops (:193–210).

**Flow:** build completed-output sets per output type → classify programs active/orphan → drop calls (per type table) lacking outputs, EXCEPT pending hosted shell calls (`status` None/"in_progress" may legally wait) and anonymous `tool_search_call`s that a later anonymous output matches LIFO-style → optionally prune outputs whose call was pruned → finally walk BACKWARD: a reasoning item is dropped iff the next non-reasoning item is in the dropped set.
**Invariant:** Never ship reasoning-without-follower; never kill an in-flight hosted shell; never orphan a program that still owns live children. A porter who only drops bare function_calls leaves 400-causing reasoning items in history.
**Probe:** `grep -c "def test_drop_orphan_function_calls" tests/test_run_internal_items.py` → 9 (incl. `..._drops_reasoning_preceding_dropped_tool_call` :218, `..._preserves_active_program_call_chain` :151, `..._matches_latest_anonymous_tool_search_call` :360).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "drop_orphan_function_calls reasoning preceding program caller", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the orphan ladder incl. the reasoning cascade and program-ownership rule; adapt the type table to your call/output vocabulary; omit anonymous tool-search matching if your model always assigns call ids. Coverage caveat: none — all cited paths clean at generation 2026-08-24T03:12:31Z.
