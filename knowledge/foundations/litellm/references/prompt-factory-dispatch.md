<!-- capsule-v2 -->
# Prompt template factory dispatch — turning chat messages into provider-native text prompts

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm`. **Question:** For providers whose APIs take a single prompt string rather than a message array, how does litellm pick the right prompt template, and where do user-defined custom prompts override it?

## prompt_factory + custom_prompt_dict override + function_call_prompt
**Path/Symbol:** `litellm/litellm_core_utils/prompt_templates/factory.py` — `prompt_factory` (:5258-5361), `function_call_prompt` (:5156-5173); override site example `litellm/llms/vllm/completion/handler.py:56-66`; gate `litellm/main.py:5398-5402`.
**Signature:** `prompt_factory(model: str, messages: list, custom_llm_provider: str | None = None, api_key: str | None = None)`; `function_call_prompt(messages: list, functions: list) -> list`.
**Data Shape:** input messages is the OpenAI-style role/content list; output is either a formatted prompt string (most templates) or the mutated message list (perplexity pops `name`, watsonx delegates); `function_call_prompt` returns the SAME list object mutated.

### Decisive source
```python
# factory.py:5262-5272 (head of the dispatch) + terminal fallback
if custom_llm_provider == "ollama":
    return ollama_pt(model=model, messages=messages)
elif custom_llm_provider == "anthropic":
    if litellm.AnthropicTextConfig._is_anthropic_text_model(model):
        return anthropic_pt(messages=messages)
    return anthropic_messages_pt(messages=messages, model=model, llm_provider=custom_llm_provider)
elif custom_llm_provider == "gemini":
    if (model == "gemini-pro-vision" or litellm.supports_vision(model=model) ...):
        return _gemini_vision_convert_messages(messages=messages)
...
# tail: HF model-name heuristics then
else:
    return hf_chat_template(original_model_name, messages)
except Exception:
    return default_pt(...)   # never raises out of the factory

# vllm handler.py:56-66 — where user prompts win over built-ins
if model in custom_prompt_dict:
    model_prompt_details: Final = custom_prompt_dict[model]
    prompt = custom_prompt(role_dict=model_prompt_details["roles"],
                           initial_prompt_value=..., final_prompt_value=..., messages=messages)
else:
    prompt = prompt_factory(model=model, messages=messages)
```

**Flow:** each text-completion handler first checks `custom_prompt_dict[model]` → `custom_prompt(role_dict, initial/final prompt values, messages)`; only when absent does it call `prompt_factory`, which dispatches provider-first (`custom_llm_provider` elif chain), then falls back to HuggingFace model-name heuristics (llama-2/3, falcon, mpt, codellama, wizardcoder…), then to `hf_chat_template(original_model_name, messages)`; any exception inside collapses to `default_pt`. Separately, when a provider reports `functions_unsupported_model` and `litellm.add_function_to_prompt` is set, main.completion folds the tool schemas into the conversation via `function_call_prompt` — appending a JSON-only instruction block to the system message (string content gets appended, list content gets a new text part; no system message → one is appended).
**Invariant:** The factory never raises through its callers (terminal except). `function_call_prompt` mutates the caller's message list in place. Custom-prompt lookup happens in the handler *before* the factory — registering `custom_prompt_dict[model]` fully bypasses built-in template selection.
**Probe:** `tests/test_litellm/litellm_core_utils/prompt_templates/test_litellm_core_utils_prompt_templates_factory.py` executed live at the pin → 97 passed (ollama_pt simple/consecutive-user cases, anthropic thinking-block sign/drop rules, bedrock converse document formats, gemini conversion…).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  namePattern: "^prompt_factory$", fields: ["lines", "signature"] });
// → exact single hit: Function 5258-5361, sig "(model, messages, custom_llm_provider=None, api_key=None)"
```
BM25 caveat: prose queries with provider words ("prompt_factory ollama anthropic gemini bedrock") rank tests above the function — use the name-pattern needle.

## Verdict
Adopt the layering: per-handler custom-prompt override → provider dispatch table → model-name heuristics → generic chat-template fallback → never-fail default; and the in-place function-to-prompt folding gated on an explicit opt-in flag plus a provider capability signal. Adapt template bodies per vendor (they encode each vendor's exact control tokens). Omit the hardcoded llamaguard safety-policy jinja blob unless you need that model. Coverage caveat: `hf_chat_template`/`custom_prompt` interiors not deep-read this pass (NEXT-PASS TARGET 3); `tests/llm_translation/test_prompt_factory.py` unrunnable here (missing `vcr`) — unit suite stands in.
