<!-- capsule-v2 -->
# Replay sanitizer — which output-only fields must be stripped before a RunItem becomes model input?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory project `openai-agents-python`. **Question:** When converting response/output items back into Responses-API input items, what server-assigned metadata would a naive `model_dump()` replay that the API then rejects?

## The single sanitize funnel
**Path/Symbol:** `src/agents/items.py`: `RunItemBase.to_input_item` (:151–153) routes EVERY item through `_output_item_to_input_item` (:222–256); tool_search variants share `_tool_search_item_to_input_item` (:207–219); `ModelResponse.to_input_items` (:732–738) maps all outputs through the same funnel; `ToolCallOutputItem.to_input_item` pre-strips SDK-only keys (:462–489).
**Signature:** `def _output_item_to_input_item(raw_item: Any) -> TResponseInputItem`.
**Data Shape:** dict payloads shallow-copied; BaseModel payloads dumped `exclude_unset=True`; anything else raises `AgentsException`.

### Decisive source
```python
# ``created_by`` is server-assigned, output-only metadata that is absent from the Responses
# input-item schema, so it must not be replayed back to the API. Several output item types
# carry it (apply_patch/shell calls and tool-call outputs)...(:237-241)
payload.pop("created_by", None)
if item_type == "shell_call_output":
    chunks = payload.get("output")
    if isinstance(chunks, list):
        payload["output"] = [
            {key: value for key, value in chunk.items() if key != "created_by"}
            if isinstance(chunk, dict) else chunk for chunk in chunks
        ]
```

**Flow:** read `type` from dict-or-model → copy payload → pop `created_by` (top level, and inside every `shell_call_output.output` chunk because the outer copy is SHALLOW) → return. `ToolCallOutputItem` additionally pops `status`, `shell_output`, `provider_data` from shell outputs before delegating (:473–477). Commit 8cd1f5e moved the base-class path onto this funnel — previously plain items replayed raw dumps and leaked `created_by`.
**Invariant:** Every replay path (single item, item list, whole ModelResponse) must go through the same strip; a porter who keeps the pre-fix two-branch dump sends server-assigned fields back and gets 400s. Strip copies — never mutate the caller's raw item (nested chunk dicts are rebuilt fresh).
**Probe:** `grep -c 'payload.pop("created_by", None)' src/agents/items.py` → 2 (:218, :241). Direct tests: `tests/test_items_helpers.py::test_to_input_items_for_tool_search_strips_created_by` (:525), `..._strips_created_by_for_non_tool_search_items` (:571), `test_tool_call_item_to_input_item_strips_created_by` (:624), `..._tool_call_output_item_...` (:645), `..._strips_nested_created_by_from_shell_call_output` (:703).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "output_item_to_input_item created_by replay strip", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-funnel replay sanitizer with shallow-copy semantics and nested-chunk rebuild; adapt the exact stripped-field list to your API's output-only vocabulary; omit OpenAI's specific `created_by`/`shell_output` names if your backend differs. Coverage: all cited paths no_recorded_issue at generation 2026-08-24T03:12:31Z.
