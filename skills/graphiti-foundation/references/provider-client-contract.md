<!-- capsule-v2 -->
# Provider-client shared contract — what does every graphiti LLM client agree on beyond the ABC method set?

**Source:** Graphiti Apache-2.0 `main@401c59a` (`anthropic_client.py`, `gemini_client.py`); Codebase Memory `graphiti`. **Question:** When porting structured-output over a new provider, which cross-provider conventions (tool-forcing ladder, max-token resolution, refusal-vs-rate-limit split, safety-block surfacing) must survive?

## Tool-forced JSON + four-step max-token precedence + error taxonomy mapping
**Path/Symbol:** `graphiti_core/llm_client/anthropic_client.py:_generate_response` (:248–335), `_resolve_max_tokens` (:226–244), `_create_tool` (:161–199), `_extract_json_from_text` (:136–158); `graphiti_core/llm_client/gemini_client.py:_check_safety_blocks` (:130–152), `_check_prompt_blocks` (:154–163), `GEMINI_MODEL_MAX_TOKENS` (:45–60).
**Signature:** `async _generate_response(...) -> tuple[dict, int, int]` (response, input_tokens, output_tokens).
**Data Shape:** Anthropic tool def `{name: response_model.__name__, input_schema: model_json_schema()}` with forced `tool_choice={'type':'tool','name':...}`; generic fallback schema `{type:'object', additionalProperties: True}` when no model given.

### Decisive source
```python
except anthropic.RateLimitError as e:
    raise RateLimitError(f'Rate limit exceeded. ...') from e
except anthropic.APIError as e:
    # Special case for content policy violations. We convert these to RefusalError
    # to bypass the retry mechanism, as retrying policy-violating content will always fail.
    if 'refused to respond' in str(e).lower():
        raise RefusalError(str(e)) from e
    raise e
```
max-token precedence (:237–244): explicit param → instance max_tokens → per-model table → DEFAULT (8192); and Gemini's safety gate:
```python
if not (hasattr(response, 'candidates') and response.candidates):
    return
candidate = response.candidates[0]
if not (hasattr(candidate, 'finish_reason') and candidate.finish_reason == 'SAFETY'):
    return
...
raise Exception(f'Response blocked by Gemini safety filters: {safety_details}')
```

**Flow:** ANTHROPIC — messages split system-first (`messages[0]` → `system=`, rest → user turns); ONE tool defined from the pydantic schema and FORCE-selected, so the model cannot answer in prose; response walk takes the first `tool_use` block's dict input verbatim (json.loads only if not already dict); NO tool_use ⇒ scan text blocks and brace-slice `{first…}last` for salvageable JSON, else raise ValueError. Errors map into the shared taxonomy: provider rate-limit → library `RateLimitError` (retryable by base-class ladder), policy refusals → `RefusalError` (deliberately NON-retryable — retrying refused content always fails), everything else re-raised. GEMINI — mirrors the same shape with its own SDK: two-block check (`_check_prompt_blocks` raises on `prompt_feedback.block_reason`; `_check_safety_blocks` inspects `finish_reason == 'SAFETY'` and formats blocked ratings into the message), `MAX_RETRIES: ClassVar[int] = 2`, per-model max-token table with the same four-step resolution, dual models (main/small) selected by `ModelSize`.
**Invariant:** the retry taxonomy is semantic, not transport-level: rate-limit = retry later, refusal = never retry (fail fast to save spend), safety-block = surfaced as data-rich exceptions. Every client returns `(dict, input_tokens, output_tokens)` from `_generate_response` even when the API doesn't report usage (zeros, or GLiNER-style estimates elsewhere) — the token ledger depends on the tuple always existing.
**Probe:** no direct unit tests for either client (provider suites absent upstream; `tests/llm_client/` holds only token-tracker/openai-client tests). Coverage caveat recorded. Deterministic probe: assert `_create_tool(None)` yields the generic additionalProperties schema and forced choice; assert refusal-string mapping bypasses retry by construction (RefusalError not subclassing the retryable family).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "_generate_response RateLimitError RefusalError tool_choice", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: forced-tool JSON extraction with prose-salvage fallback, the four-step max-token precedence, and the retry/refusal/safety error taxonomy. Adapt schemas/tool-choice names to each SDK's dialect. Omit the hardcoded model tables (stale by design — refresh at port time). This capsule generalizes what `openai-base-client.md` and `generic-client-structured-output.md` pinned for the OpenAI family to the second/third provider families.
