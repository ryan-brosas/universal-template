<!-- capsule-v2 -->
# Search modes — how does each query mode orchestrate LLM calls (fan-out, budget, state, failure) around the same builder/ABC spine?

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** for each mode (global/local/drift/basic), what is the exact LLM call choreography — and which failure-handling details do porters get wrong?

## Shared spine: BaseSearch + SearchResult
**Path/Symbol:** `query/structured_search/base.py:28-93` (`SearchResult`, `BaseSearch[Generic[T]]`).
**Signature:** every mode implements `async search(query, conversation_history=None) -> SearchResult` + `stream_search -> AsyncGenerator[str]`.
**Data Shape:** `SearchResult` carries response + context_data/context_text + totals AND per-stage category dicts (`llm_calls_categories` etc. keyed `build_context`/`map`/`reduce`/…).
**Invariant:** builders assemble context; searches template it into system prompts via `CompletionMessagesBuilder().add_system_message(...).add_user_message(query)`; token accounting is per-stage then summed.

## Global: Map-Reduce over community-report batches
**Path/Symbol:** `query/structured_search/global_search/search.py:55-431` (`GlobalSearch.__init__` :58-104, `_map_response_single_batch` :216-274, `_parse_search_response` :276-304, `_reduce_response` :306-431).
**Signature:** `concurrent_coroutines=32`, `max_data_tokens=8000`, `map_max_length=1000`, `reduce_max_length=2000`, `json_mode=True`, separate `map_llm_params`/`reduce_llm_params` (different model tiers allowed).
**Data Shape:** map output = JSON `{"points": [{"description", "score"}]}`; reduce input = sorted key points formatted `----Analyst N---- / Importance Score: S / answer`.

### Decisive source
```python
# search.py:237-243 — semaphore-bounded fan-out; json mode forced per call
async with self.semaphore:
    model_response = await self.model.completion_async(
        messages=messages_builder.build(),
        response_format_json_object=True, **llm_kwargs)
# :333-353 — score-0 filter → canned NO_DATA_ANSWER when nothing survived
filtered_key_points = [p for p in key_points if p["score"] > 0]
if len(filtered_key_points) == 0 and not self.allow_general_knowledge:
    return SearchResult(response=NO_DATA_ANSWER, ...)
```
**Flow:** builder returns a LIST of batch chunks → `asyncio.gather` one map call per chunk under a 32-slot semaphore (`stream_search` :120-128 streams the reduce phase after) → parse each batch's points (`try_parse_json_object` repair ladder; malformed batch degrades to `[{answer:"",score:0}]`, never raises) → sort survivors by score desc → greedily pack formatted points until `max_data_tokens` would overflow (:361-380) → ONE reduce streaming call. Map/reduce have SEPARATE params+lengths. `allow_general_knowledge` appends an instruction to answer from prior knowledge.
**Invariant:** map failures are swallowed as zero-score batches; reduce never runs on empty evidence unless general knowledge is on. Porters break this by raising inside the map loop or feeding unscored text to reduce.
**Probe:** no dedicated unit test pins `GlobalSearch` (coverage caveat); `tests/unit/query/llm/text_utils.py`-adjacent parsing helpers are exercised indirectly via smoke tests.

## Local: single-window answer (context in local-search capsule)
**Path/Symbol:** `query/structured_search/local_search/search.py:31-183` (`LocalSearch.search` :56-144).
### Decisive source
```python
# search.py:78-90 — DRIFT reuses this prompt slot to inject global_query + followups
if "drift_query" in kwargs:
    search_prompt = self.system_prompt.format(
        context_data=..., response_type=..., global_query=drift_query,
        followups=kwargs.get("k_followups", 0))
```
**Flow:** build_context → format LOCAL_SEARCH_SYSTEM_PROMPT → one streamed completion, tokens counted after; on exception return EMPTY response with context preserved (:134-144). Also the execution engine of DRIFT's follow-ups (see below).
**Invariant:** errors-as-results: a failed LLM call yields `response=""`, not a raise — callers must treat "" as failure.
**Probe:** coverage caveat as above (no dedicated unit test).

## DRIFT: primer → action graph → shared LocalSearch executor → reduce
**Path/Symbol:** `query/structured_search/drift_search/{search.py:37-311, primer.py:123-229, drift_context.py:39-229, state.py:18-150, action.py:15-245}`.
**Signature:** `DRIFTSearch(model, context_builder, tokenizer=None, query_state=None)`; config knobs `n_depth`, `drift_k_followups`, `primer_folds` (from `DRIFTSearchConfig`).
**Data Shape:** state = networkx `MultiDiGraph` whose NODES are `DriftAction` objects; edges parent→follow-up weighted 1.0.

### Decisive source
```python
# search.py:240-263 — epoch loop over ranked incomplete actions
while epochs < self.context_builder.config.n_depth:
    actions = self.query_state.rank_incomplete_actions()
    if len(actions) == 0:
        logger.debug("No more actions to take. Exiting DRIFT loop.")
        break
    actions = actions[: self.context_builder.config.drift_k_followups]
    ...
    results = await self._search_step(...)   # tqdm_asyncio.gather
```
```python
# action.py:85-100 — failed parses become score -inf, NOT exceptions
_, response = try_parse_json_object(search_result.response, verbose=False)
self.answer = response.pop("response", None)
self.score = float(response.pop("score", "-inf"))
...
self.follow_ups = response.pop("follow_up_queries", [])
```
**Flow:** if state empty → `build_context` HyDE-primes: `PrimerQueryProcessor.expand_query` writes a hypothetical answer shaped like ONE RANDOMLY-CHOSEN report's full content (`secrets.choice(reports).full_content`, primer.py:81), embeds it, cosine-ranks all reports in numpy (:216-228), takes top-k; `DRIFTPrimer.decompose_query` splits reports into `primer_folds` and generates structured `intermediate_answer/score/follow_up_queries` per fold via pydantic `response_format` (:32-43) → `_process_primer_results` averages fold scores and REQUIRES both answers+follow_ups (RuntimeError otherwise :111-157). Then epochs ≤ `n_depth`: take ranked incomplete actions, cap at `drift_k_followups`, run each through THE SAME shared `LocalSearch` instance configured FROM the DRIFT config (init_local_search :71-109 mirrors local_search_* params), parse answers/follow-ups into the graph. Finally serialize nodes+edges and optionally reduce all node answers into one response.
**Invariants:** (1) dedupe is IDENTITY-BY-QUERY — `DriftAction.__hash__/__eq__` hash only `query`, so identical follow-ups collapse into one node; (2) `rank_incomplete_actions` SHUFFLES when no scorer is given (state.py:75-77) — ordering is random without one; (3) failed actions stay in the graph at `-inf` so they rank last but don't crash the loop; (4) empty query raises ValueError up front (:211-213); (5) `stream_search` runs with `reduce=False` then streams its own reduction (:313-348).
**Probe:** no dedicated unit test pins the DRIFT loop (coverage caveat).

## Basic: vanilla RAG baseline
**Path/Symbol:** `query/structured_search/basic_search/search.py:32-182`; context from `basic_context.py:1-109` (vector top-k text units + optional conversation history).
### Decisive source
```python
# basic search.py:94-99 — NOTE: no await here (unlike local_search.search.py:102);
# completion_async's awaitable is consumed by async-for directly
response_stream: AsyncIterator[LLMCompletionChunk] = (
    self.model.completion_async(messages=messages_builder.build(), stream=True, ...)
)
```
**Flow:** vector-search raw chunks → BASIC_SEARCH_SYSTEM_PROMPT → streamed completion. Same errors-as-results shape as local.
**Invariant:** this is the no-graph control group — same spine, zero graph structures. Porting trap above: the missing `await` is intentional-looking but inconsistent with local mode; normalize deliberately, not accidentally.
**Probe:** coverage caveat as above.

## Bonus seam mined en route (not in legacy refs): LLM-rated dynamic community selection
**Path/Symbol:** `query/context_builder/dynamic_community_selection.py:26-176` + `rate_relevancy.py:27-86`.
**Signature:** `select(query) -> (list[CommunityReport], llm_info)`; BFS from level-"0" communities, rating each level's reports before descending.
**Data Shape:** `rate_relevancy` asks for a 0-10 rating per report (`num_repeats` votes, majority wins via `np.unique` counts; JSON-parse failure defaults to rating **1** = keep, :69-73).
### Decisive source
```python
# dynamic_community_selection.py:139-155 — parent pruning + cold-start fallback
if not self.keep_parent and community in self.communities:
    relevant_communities.discard(self.communities[community].parent)  # drop parent once child is relevant
...
if (len(queue)==0) and (len(relevant_communities)==0) and (str(level) in self.levels) and (level <= self.max_level):
    queue = self.levels[str(level)]   # nothing relevant yet -> widen to next level
```
**Invariant:** children IDs arrive as ints or strs — always `str(child)` before lookup (issue #2004 fix, pinned by test). Trades one cheap rating pass per report for a far smaller global-map input.
**Probe:** `tests/unit/query/context_builder/dynamic_community_selection.py::test_dynamic_community_selection_handles_int_children` :27-124 (int children must resolve against str-keyed reports).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "GlobalSearch _map_response_single_batch DRIFTSearch QueryState DriftAction DynamicCommunitySelection rate_relevancy", limit: 10, fields: ["signature", "name", "file"] });
// inbound trace: rank_incomplete_actions <- DRIFTSearch.search (hop 1), DRIFTSearch.stream_search (hop 2)
```

## Verdict
Adopt semaphore-bounded scored map-reduce with NO_DATA_ANSWER honesty, the shuffle-or-score action-graph expansion loop with identity-by-query dedupe, errors-as-results search contracts, HyDE-style priming off existing corpus summaries, and majority-vote relevancy rating with keep-on-failure default; adapt concurrency limits, model tiers per stage, depth/breadth knobs, and rating thresholds to host; omit Azure bindings and the unified-search-app UI. Coverage caveat: none of the four mode orchestrators has a dedicated unit test in-repo — behavior claims are source-grounded; the two cited tests pin entity mapping and int-children handling only.
