<!-- capsule-v2 -->
# Follow-up question generation — how does the "generate next questions" feature reuse a context builder, and why do agenerate/generate exist as near-twins?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** what is LocalQuestionGen's contract (history→prompt mapping, newline-split response, errors-as-empty) that a porter must keep for conversational follow-ups?

## LocalQuestionGen
**Path/Symbol:** `packages/graphrag/graphrag/query/question_gen/local_gen.py` (`LocalQuestionGen.agenerate` :56-146, `generate` :148-237 — byte-identical twins).
**Signature:** `agenerate/generate(question_history: list[str], context_data: str | None, question_count: int, **kwargs) -> QuestionResult`.
**Data Shape:** `QuestionResult{response: list[str], context_data: dict, completion_time, llm_calls=1, prompt_tokens}`; history maps to LAST question = current query, all PRIOR questions become user-role messages.

### Decisive source
```python
# local_gen.py:70-79 + :127-128 — history slicing rule and the SPLIT:
# the LLM returns one question per LINE; no JSON parsing, no numbering
# strip — raw .split("\n") is the response contract
question_text = question_history[-1]
history = [{"role": "user", "content": q} for q in question_history[:-1]]
conversation_history = ConversationHistory.from_list(history)
...
return QuestionResult(response=response.split("\n"), ...)
```
```python
# :138-146 — ANY exception (prompt format KeyError, LLM failure) logs and
# returns EMPTY response with llm_calls still counted 1 — question
# generation failing must never break the chat turn it decorates
except Exception:
    logger.exception("Exception in generating question")
    return QuestionResult(response=[], context_data=context_records,
                          completion_time=time.time() - start_time,
                          llm_calls=1, prompt_tokens=self.tokenizer.num_tokens(system_prompt))
```

**Flow:** empty history → empty question text + conversation_history=None → optional context build via injected LocalContextBuilder when caller passed context_data=None → system_prompt.format(context_data=..., question_count=...) → CompletionMessagesBuilder(system, user=question_text) → streaming completion accumulating tokens with per-token callbacks → split on newlines.
**Invariant:** the sync/async twin pair exists because BaseQuestionGen's abstract surface declares both; porters "deduplicating" them break the ABC. `question_context` key is PREPENDED into context_data so consumers can see which turn produced the questions (:129-132).
**Probe:** no dedicated unit file for question_gen (feature exercised via unified-search-app smoke); pinned @pin by greps: `grep -c 'question_history\[-1\]' local_gen.py` = 2 (both twins), `grep -c 'response.split' local_gen.py` = 2, `grep -c 'llm_calls=1' local_gen.py` = 4 (two per twin). Recorded caveat: verified by direct read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "LocalQuestionGen generate questions", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved rank#2 `local_gen.LocalQuestionGen.generate` :148-237 (rank#1 is the app-layer consumer).

## Verdict
Adopt history-slicing semantics, newline-split response contract, and never-raise error shape; adapt prompt template and builder injection to host; omit the sync twin if your base class is async-only (then delete both halves consistently).
