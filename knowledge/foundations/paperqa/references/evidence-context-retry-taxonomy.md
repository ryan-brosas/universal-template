<!-- capsule-v2 -->
# Evidence-context retry taxonomy — which context failures retry once vs abandon?

**Source:** paper-qa Apache-2.0 `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** When an LLM call fails while turning a Text into a scored Context, when does the pipeline retry with the failure fed back, and when does it drop the context while preserving cost accounting?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/core.py` (`LLMContextError` :127-133, `LLMBadContextJSONError` :136-147, `LLMContextTimeoutError` :150-160, `LLMContextRequestFailedError` :163-175, `_map_fxn_summary` :178-380, `map_fxn_summary` :383-400).
**Signature:** `async def map_fxn_summary(**kwargs) -> tuple[Context | None, list[LLMResult]]`.
**Data Shape:** Input kwargs include `text: Text`, `summary_llm_model`, `prompt_templates: tuple[str,str] | None`, `parser: Callable | None`. Output is `(Context | None, llm_results)` — `None` context means "abandoned", but `llm_results` ALWAYS carries every LLMResult made (including failures) so callers can `session.add_tokens` them (`docs.aget_evidence` :573-575).

### Decisive source
```python
class LLMContextError(ValueError):
    retryable: ClassVar[bool]
    def __init__(self, message, llm_results):
        self.llm_results = llm_results  # House so we can cost track across retries
...
except litellm.BadRequestError as exc:
    if not evidence_text_only_fallback: raise
    logger.warning(f"... Retrying without media.")
    llm_result = await summary_llm_model.call_single(messages=[
        Message(role="system", content=system_prompt),
        Message(content=message_prompt),  # text-only retry
        *append_msgs])
...
try:
    return await _map_fxn_summary(**kwargs)
except LLMContextError as exc:
    if not exc.retryable:
        return None, exc.llm_results            # abandon once
    try:
        return await _map_fxn_summary(**kwargs, _prior_attempt=exc)  # ONE retry
    except LLMContextError as exc2:
        return None, exc2.llm_results           # abandon after second failure
```

**Flow:** Bad JSON from parser ⇒ `LLMBadContextJSONError` (retryable=True) → retry appends a synthetic prior-attempt user message (:214-223). Provider `Timeout` ⇒ non-retryable; `MidStreamFallbackError`/`BadRequestError` ⇒ non-retryable `LLMContextRequestFailedError`; opt-in `evidence_text_only_fallback` converts media-bearing BadRequestError into a text-only retry INSIDE the same attempt (:270-288). No model/prompts configured ⇒ score hardcoded 5 with comment "we filter out 0s in another place" (:350-356).
**Invariant:** Exactly one retry maximum, and every failed attempt's tokens still reach the session ledger — cost never disappears because a context was abandoned.
**Probe:** `tests/test_paperqa.py::test_unrelated_context` (:1508) plus executed AST-lifted probe `python3 /tmp/pqa-pass1/probe_gate5.py` (T3e asserts `llm_parse_json` raises ValueError → wrapped as retryable bad-JSON).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "map_fxn_summary LLMContextError retryable", limit: 10 });
// trace_path --project ext-paper-qa --function-name map_fxn_summary --direction inbound  → Docs.aget_evidence (hop 1), gather_evidence/gen_answer/aquery (hop 2-3)
```

## Verdict
Adopt the two-class taxonomy (retryable bad-output vs non-retryable transport) + results-carried-through-failures pattern; adapt exception classes to your provider SDK's error surface; omit litellm-specific MidStreamFallbackError handling if you have no router fallbacks. Coverage caveat: full-path probe runner-blocked (ambient python lacks litellm/lmi); parser + classification logic verified by lifted execution.
