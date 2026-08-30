<!-- capsule-v2 -->
# aquery prompt chain — how does one question flow through the multi-call answer pipeline with cost attributed per stage?

**Source:** paper-qa Apache-2.0 `main@57e89f72`; Codebase Memory `paper-qa`. **Question:** When a session is queried, which LLM calls run in what order, how is each call correlated to the session, and when does the chain skip its expensive middle?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/docs.py:Docs.aquery` (:588-721); caller `agents.tools.GenerateAnswer.gen_answer` (:323-372).
**Signature:** `async def aquery(self, query: PQASession | str, settings=None, callbacks=None, llm_model=None, summary_llm_model=None, embedding_model=None, partitioning_fn=None) -> PQASession`.
**Data Shape:** Accepts a bare question (wraps in `PQASession` stamped with `config_md5`) or an existing session (mutated in place and returned). Every LLM result is immediately folded into `session.add_tokens(...)`; final answer text lands in `session.raw_answer` and is post-processed by `populate_formatted_answers_and_bib_from_raw_answer()` at :719.

### Decisive source
```python
contexts = session.contexts
if answer_config.get_evidence_if_no_contexts and not contexts:   # :615 bootstrap
    session = await self.aget_evidence(session, ...)
...
with set_llm_session_ids(session.id):                            # :627 correlation
    pre = await llm_model.call_single(messages=messages, callbacks=callbacks, name="pre")
session.add_tokens(pre)
...
if prompt_config.answer_iteration_prompt and session.answer:     # :658 re-answer hook
    prior_answer_prompt = prompt_config.answer_iteration_prompt.format(prior_answer=session.answer)
...
answer_result = await llm_model.call_single(..., name="answer")  # :678 stage tag
...
session.add_tokens(post); answer_text = f"{answer_text}\n\n{post.text}"  # :710-711 post REPLACES then CONCATENATES
```

**Flow:** optional evidence bootstrap (`get_evidence_if_no_contexts`) → optional `pre` call whose output rides into the context block as "Extra background information" → context serialization + empty-context refusal short-circuit → `answer` call (with prior-answer injected when iterating) → example-citation echo scrub → optional extra-background regex strip → optional `post` call that REPLACES `answer_text` then concatenates the old text → raw_answer/bib population. Each of pre/answer/post runs inside `set_llm_session_ids(session.id)` with a stage tag (`name="pre"/"answer"/"post"`), so provider-side logging, callbacks, and cost routing can attribute every token to the session and stage.
**Invariant:** Cost accounting is stage-local and immediate — a failure after `pre` still keeps `pre`'s tokens on the ledger; and the empty-context refusal happens BEFORE the answer call, so the pipeline never spends the big call on no evidence.
**Probe:** `tests/test_paperqa.py::test_aquery_groups_contexts_by_question` (:1043-1114) drives aquery end-to-end with `answer_iteration_prompt: None`; `::test_too_much_evidence` (:2588-2606) stresses the chain with `evidence_k=10`/`max_sources=10`. No runner provisioned in lane env — deterministic source/test-range probe.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "aquery add_tokens set_llm_session_ids", limit: 10 });
// trace_path --project paper-qa --function-name aquery --direction both
// → sole caller GenerateAnswer.gen_answer; callees map_fxn_summary/retrieve_texts/context_serializer
```

## Verdict
Adopt the stage-tagged chain (`set_llm_session_ids` + `name=` tags + immediate add_tokens), the bootstrap flag, and the replace-then-concatenate post semantics if you need revision-style post-processing; adapt the session-id mechanism to your LLM client's metadata channel; omit litellm-specific reasoning_content plumbing if your provider lacks it. Coverage: docs.py no_recorded_issue + metadata_match @ gen 2026-08-25T19:57:59Z.
