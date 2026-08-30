<!-- capsule-v2 -->
# GraphExtractor gleaning loop — delimiter-grammar parsing where the continuation probe is a separate LLM call that must not run on the final glean

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how does the index pipeline turn one LLM completion into a multi-round entity/relationship extraction, and what grammar + error contract does the parser rely on?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/extract_graph/graph_extractor.py`: `GraphExtractor.__call__` (:59-83), `_process_document` (:85-122), `_process_result` (:124-178).
**Signature:** `GraphExtractor(model, prompt, max_gleanings: int, on_error: ErrorHandlerFn | None = None)`; `__call__(text: str, entity_types: list[str], source_id: str) -> tuple[pd.DataFrame, pd.DataFrame]`.
**Data Shape:** wire grammar — records split on `"##"`, fields split on `"<|>"`, terminal sentinel `"<|COMPLETE|>"`; entity record `("entity", NAME, TYPE, DESC)`, relationship record `("relationship", SRC, TGT, DESC, WEIGHT)`; names/types upper-cased. Empty outputs are typed empty frames (`_empty_entities_df` / `_empty_relationships_df`) so downstream groupby never sees missing columns.

### Decisive source
```python
if self._max_gleanings > 0:
    for i in range(self._max_gleanings):
        messages_builder.add_user_message(CONTINUE_PROMPT)
        response = await self._model.completion_async(messages=messages_builder.build())
        results += response.content
        if i >= self._max_gleanings - 1:
            break                                  # final glean: skip the Y/N probe
        messages_builder.add_user_message(LOOP_PROMPT)
        response = await self._model.completion_async(messages=messages_builder.build())
        if response.content != "Y":
            break                                  # model says "no more"
...
weight = float(record_attributes[-1])              # LAST field is weight
except ValueError:
    weight = 1.0                                   # unparseable → default 1.0, never raise
```
On any exception in `_process_document`, `__call__` logs via `on_error(e, traceback, {"source_id", "text"})` and returns BOTH empty frames — a failed text unit is silent-empty at this layer.

**Flow:** prompt formatted with only `{input_text}` + `{entity_types}` (delimiters are baked into the prompt text, not passed as variables) → first completion appended to conversation → loop of CONTINUE (append output) / LOOP-probe ("more? Y/N": exact-string compare against `"Y"`) → whole transcript parsed once by splitting records and dispatching on the quoted record-type field.
**Invariant:** (1) The Y/N continuation call is SKIPPED after the last allowed glean (saves a doomed LLM round-trip). (2) Weight is read from field `-1`, tolerating extra description commas; parse failure degrades to 1.0 instead of dropping the relationship. (3) Entity/relationship rows always carry `source_id` — provenance survives merging. (4) Extraction failure yields typed-empty frames, never raises past `__call__`.
**Probe:** `tests/unit/indexing/operations/test_extract_graph.py` pins the MERGE side of these rows (`test_groups_by_title_and_type`, `test_groups_by_source_target` weight summing; extractor class itself has no direct unit test — smoke-covered via workflow tests; caveat recorded).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "GraphExtractor _process_document max_gleanings CONTINUE_PROMPT LOOP_PROMPT TUPLE_DELIMITER", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the continue/loop-probe gleaning pattern with the final-glean skip and the `<|>`/`##` tuple grammar for structured LLM extraction; adapt delimiters/prompt to host schema; omit the hard-coded upper-casing if the target ontology is case-sensitive.
