<!-- capsule-v2 -->
# Agent tool loop & status protocol — how does an LLM drive search/gather/answer tools through a shared EnvironmentState?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** What is the concurrency contract between tools mutating one Docs/PQASession state, how does the agent read progress, and when does the runner force an answer?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/agents/tools.py` (`EnvironmentState` :47-92, `PaperSearch.paper_search` :120-210, `GatherEvidence.gather_evidence` :225-311, `GenerateAnswer.gen_answer` :323-386, `Complete.complete` :415-440, `AVAILABLE_TOOL_NAME_TO_CLASS` :691-712) + `env.py:settings_to_tools/PaperQAEnvironment.step` (:47-140, :309-346).
**Signature:** `CONCURRENCY_SAFE: ClassVar[bool]` per tool class — ONLY PaperSearch and ClinicalTrialsSearch declare True.
**Data Shape:** Every tool returns a STRING ending in `state.status` = `"Status: Paper Count=N | Relevant Papers=N | Current Evidence=N | Current Cost=$X.XXXX"`; `EnvironmentState.STATUS_SEARCH_REGEX_PATTERN` is THE machine-readable channel (GenerateAnswer splits answer from status with `" | " + STATUS_REGEX`; Complete splits certainty likewise).

### Decisive source
```python
search_key = query, year          # previous_searches dict keyed by EXACT (query, year-range)
try:    offset = self.previous_searches[search_key]
except KeyError: offset = self.previous_searches[search_key] = 0
results = await index.query(query, top_n=self.settings.agent.search_count,
                            offset=offset, field_subset=[f for f in index.fields if f != "year"])
self.previous_searches[search_key] += self.settings.agent.search_count   # continuation cursor
```
Question-swap hazard (GatherEvidence):
```python
try:
    state.session.question = question        # TODO: remove this swap, as it prevents parallel calls
    state.session = await state.docs.aget_evidence(query=state.session, ...)
    l1 = len(state.session.contexts)
finally:
    state.session.question = original_question   # ALWAYS restored
```
Runner failover (`main._run_with_timeout_failure` :151-179): on TRUNCATED or never-called gen_answer, synthesize ToolRequestMessage calling GenerateAnswer directly.

**Flow:** env.step records action (cost!) BEFORE type-checking, executes tool calls concurrently (aviary honors per-tool CONCURRENCY_SAFE), done ⇔ any ToolResponseMessage named `complete`. max_answer_attempts counts gen_answer calls in tool_history and force-finishes with `has_successful_answer=None`. Reset clears contexts only — docs stay.
**Invariant:** GatherEvidence must NEVER run concurrently with itself (question swap is global state) though it may run beside PaperSearch; PaperSearch continuation requires repeating the SAME (query, year) key — offset bookkeeping lives in the tool instance, not the index.
**Probe:** `tests/test_agents.py` (tool loop); executed grep pins CONCURRENCY_SAFE=True only on PaperSearch(:114)/ClinicalTrialsSearch(:447), question-swap+finally :260/:275, offset cursor increment :204.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "previous_searches gather_evidence CONCURRENCY_SAFE status", limit: 10 });
// trace_path --function-name gather_evidence --direction inbound → aviary exec_tool_calls
```

## Verdict
Adopt per-tool concurrency flags + string-status protocol + search-cursor pattern; adapt status format to your harness (keep ONE regex as contract); omit clinical-trials twin unless in medical domain. Coverage caveat: behavior pinned by cited tests + mechanical greps.
