<!-- capsule-v2 -->
# Completion dispatch boundary — how does one sync entry funnel route to every provider and guarantee OpenAI-compatible errors?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `litellm`. **Question:** What must a porter preserve when adding or reordering a provider branch in the central completion dispatcher, and what does the outer exception handler promise callers?

## Central provider dispatch (`main.completion`)
**Path/Symbol:** `litellm/main.py:completion` (:4902-5796, fan-in ≈490) with `_CompletionDispatchContext` (:5546-5577).
**Signature:** `def completion(model: str, messages: list = [], timeout=None, ..., **kwargs) -> ModelResponse`.
**Data Shape:** ordered pipeline state: normalized kwargs → `get_llm_provider` result → `Logging` obj + `litellm_params` → `optional_params` from `get_optional_params` → mock short-circuit (:5465-5480) → Responses-API bridge check (:5482-5539) → one bundled `_dispatch_ctx` handed to every `_complete_<provider>` helper.

### Decisive source
```python
        elif custom_llm_provider == "langflow":
            response = _complete_langflow(_dispatch_ctx)

        else:
            raise LiteLLMUnknownProvider(model=model, custom_llm_provider=custom_llm_provider)
        return response
    except Exception as e:
        ## Map to OpenAI Exception
        raise exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=args,
            extra_kwargs=kwargs,
        )
```
(:5781-5796)

**Flow:** normalize → resolve provider → build logging obj → validate params → mock/bridge checks → elif chain on `custom_llm_provider` (specific providers first; the openai-compatible catch-all at :5635-5662 is guarded so a known OpenAI model name only routes there when the provider is unset/`openai`) → terminal `else` raises `LiteLLMUnknownProvider` → single `except` re-maps *every* failure via `exception_type`.
**Invariant:** `completion()` never leaks a raw provider exception — even internally-raised typed errors (e.g. `LiteLLMUnknownProvider`) are re-wrapped by `exception_type` into the OpenAI-compatible hierarchy before crossing the boundary.
**Probe:** executed live at the pin: `completion(model="totally-unknown-provider/xyz", ...)` → raised `BadRequestError` (status 400); direct tests: any `tests/local_testing/test_completion.py` error-path test pins the same wrap.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm", qn_pattern: "litellm\\.litellm\\.main\\.completion" });
// → litellm.litellm.main.completion Function litellm/main.py :4902-5796 (rank-1, verified at pin)
```

## Verdict
Adopt the single try/except→`exception_type` boundary and the dispatch-context bundle pattern (one immutable struct per attempt). Adapt the provider list and per-helper signatures to your gateway's providers; keep specific-provider branches before the openai-compatible catch-all and its known-model guard. Omit the deprecated provider stubs (`palm`, legacy together_ai text path). Coverage caveat: function body is ~900 lines; cited ranges were read directly at :5380-5796 plus graph snippet for :4902-5401.
