<!-- capsule-v2 -->
# SummarizeExtractor token-budget accumulation — refill the usable-token pool with each partial summary; never summarize a single description

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how are hundreds of per-text-unit descriptions folded into ONE entity/relationship description without blowing the LLM context window?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/summarize_descriptions/description_summary_extractor.py`: `SummarizeExtractor.__call__` (:196-213), `_summarize_descriptions` (:215-258), `_summarize_descriptions_with_llm` (:260-274); `summarize_descriptions.py`: `get_summarized` (:39-93), `do_summarize_descriptions` (:95-111).
**Signature:** `SummarizeExtractor(model, max_summary_length: int, max_input_tokens: int, summarization_prompt: str, on_error=None)`; `__call__(id: str | tuple[str, str], descriptions: list[str]) -> SummarizationResult`.
**Data Shape:** id is a title (entity) or `(source, target)` tuple (edge), JSON-dumped into the prompt via `json.dumps(id, ensure_ascii=False)`; descriptions arrive as sorted deduped lists (`sorted(set(...))` at call sites).

### Decisive source
```python
if len(descriptions) == 0:  result = ""
elif len(descriptions) == 1: result = descriptions[0]     # NO LLM CALL for singles
else: result = await self._summarize_descriptions(id, descriptions)
...
usable_tokens = self._max_input_tokens - self._tokenizer.num_tokens(self._summarization_prompt)
for i, description in enumerate(descriptions):
    usable_tokens -= self._tokenizer.num_tokens(description)
    descriptions_collected.append(description)
    if (usable_tokens < 0 and len(descriptions_collected) > 1) or (i == len(descriptions) - 1):
        result = await self._summarize_descriptions_with_llm(sorted_id, descriptions_collected)
        if i != len(descriptions) - 1:                    # another round is coming:
            descriptions_collected = [result]             #   partial result BECOMES an input
            usable_tokens = (self._max_input_tokens
                             - num_tokens(prompt) - num_tokens(result))
```

**Flow:** outer op fans out per node then per edge over one shared `asyncio.Semaphore(num_threads)` (nodes complete before edges start) → per item, descriptions accumulate until budget overflow (>1 collected, else flush at end) → LLM summarizes the batch → if more remain, the pool refills accounting for the PARTIAL SUMMARY's own token cost → final partial becomes the answer.
**Invariant:** (1) single-description items bypass the LLM entirely (cost guard). (2) A lone oversized description still goes through (the `len>1` condition prevents infinite loops / empty batches). (3) The rolling pool reserves tokens for prompt AND accumulated partial — repeated halving converges instead of overflowing. (4) Progress ticks inside the semaphore.
**Probe:** no direct unit test file for SummarizeExtractor (config-side pins exist in `tests/unit/config/utils.py::assert_summarize_descriptions_configs` :230-235); behavior pinned by source read — coverage caveat recorded in-capsule.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "SummarizeExtractor _summarize_descriptions usable_tokens descriptions_collected run_summarize_descriptions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt rolling-partial map-reduce summarization with exact tokenizer accounting and the 0/1-item fast path; adapt budgets to host model limits; keep the "partial result re-enters as input" step — replacing it with naive concatenation breaks long-tail entities.
