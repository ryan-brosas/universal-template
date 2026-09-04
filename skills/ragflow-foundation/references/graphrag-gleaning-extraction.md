<!-- capsule-v2 -->
# GraphRAG gleaning extraction — how do you squeeze maximal entities from a chunk with a bounded number of LLM calls and abort on a hopeless model?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** What is the exact continuation ("gleaning") loop shape, the forced yes/no continuation probe, and the error budget that stops a bad extraction run?

## Two extractor variants, one loop skeleton
**Path/Symbol:** `rag/graphrag/general/graph_extractor.py:GraphExtractor._process_single_content` (:94-147); `rag/graphrag/light/graph_extractor.py:_process_single_content` (:74-126); shared fan-out `rag/graphrag/general/extractor.py:extract_all` (:135-177) + `_async_chat` (:76-112).
**Signature:** `async def _process_single_content(self, chunk_key_dp: tuple[str,str], chunk_seq: int, num_chunks: int, out_results, task_id="")`. Constants at pin: `ENTITY_EXTRACTION_MAX_GLEANINGS = 2`; `MAX_CONCURRENT_PROCESS_AND_EXTRACT_CHUNK = env("MAX_CONCURRENT_PROCESS_AND_EXTRACT_CHUNK", 10)`; `GRAPHRAG_MAX_ERRORS = env("GRAPHRAG_MAX_ERRORS", 3)`.
**Data Shape:** LLM output text is record-delimited (`##`) tuples wrapped in parens with `<|>` field separators and `<|COMPLETE|>` terminator; parsed via `\((.*)\)` per record into node/edge dicts.

### Decisive source
```python
# general variant — continuation probe forces a single token:
self._loop_args = {"logit_bias": {yes[0]: 100, no[0]: 100}, "max_tokens": 1}   # tiktoken ids of "YES"/"NO"
for i in range(self._max_gleanings):
    history.append({"role": "user", "content": CONTINUE_PROMPT})
    response = await self._async_chat("", history, {}, task_id)
    results += response or ""
    if i >= self._max_gleanings - 1:
        break                                    # final glean: skip the probe
    history.append({"role": "assistant", "content": response})
    history.append({"role": "user", "content": LOOP_PROMPT})
    continuation = await self._async_chat("", history, {}, task_id)
    if continuation != "Y":
        break
    history.append({"role": "assistant", "content": "Y"})
```
```python
# light variant normalizes instead of logit-biasing:
if_loop_result = if_loop_result.strip().strip('"').strip("'").lower()
if if_loop_result != "yes":
    break
# shared circuit breaker in extract_all:
error_count += 1
if error_count > max_errors:
    raise Exception(f"Maximum error count ({max_errors}) reached.")
```

**Flow:** semaphore(10)-bounded per-chunk workers → initial extraction → CONTINUE/LOOP gleaning ladder (≤2 gleanings at pin) → records split by delimiters → regex paren capture → `_entities_and_relations` filters entity types against the configured list → results folded across chunks; per-chunk exceptions increment a shared counter and abort the whole gather only past the budget.
**Invariant:** The continuation probe is skipped on the final glean (saves one call); `_async_chat` treats timeout as NON-transient (raises immediately, no retry) but retries other failures up to 3 attempts; responses are cached (`get_llm_cache`/`set_llm_cache`) with ≤1-char responses treated as cache misses; think-tags are stripped via `re.sub(r"^.*</think>", "", flags=DOTALL)` before parsing.

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "extractor gleaning continuation loop max tokens record", filePattern: "rag/graphrag/general/*", fields: ["lines","signature"] });
// rank-1 Extractor.__call__ :131-257, _process_single_content :94-147
```

## Verdict
Adopt the gleaning ladder (bounded continue rounds + forced single-token continuation check + final-glean skip), the response-cache/think-tag/**ERROR**-sentinel chat wrapper, and the shared error-budget breaker; adapt prompt constants, delimiters, and env knob names to your host; omit the Microsoft-copyrighted prompt texts (rewrite for your models). No dedicated unit test pins the loop at this pin — evidence is full-source reads of both extractors.
