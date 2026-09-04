<!-- capsule-v2 -->
# Optional-params validation ladder — when does an OpenAI-style kwarg get dropped, remapped, or rejected per provider?

**Source:** litellm MIT `litellm_internal_staging@f005afa1`; Codebase Memory `litellm`. **Question:** Which non-default parameters are validated against a provider's supported list, what happens to unsupported ones, and why can a raise site passing 500 still surface as 400?

## Validation ladder inside `get_optional_params`
**Path/Symbol:** `litellm/utils.py:get_optional_params` (:3943-4541); inner `_check_valid_arg` (:4016-4049); supported-list fallback (:4051-4060); `litellm/exceptions.py:UnsupportedParamsError` (:911-933).
**Signature:** `def get_optional_params(model: str, functions=None, ..., custom_llm_provider="", drop_params=None, allowed_openai_params=None, base_model=None, **kwargs) -> dict`.
**Data Shape:** `passed_params = locals().copy()` minus `kwargs`/`base_model` (routing hint); `pre_process_non_default_params` keeps only user-set values; output `optional_params` dict consumed by every provider handler.

### Decisive source
```python
        for k in non_default_params:
            if k not in supported_params:
                if k == "user" or k == "stream_options" or k == "stream":
                    continue
                if k == "n" and n == 1:  # langchain sends n=1 as a default value
                    continue  # skip this param
                if k == "max_retries":
                    continue  # skip this param
                else:
                    unsupported_params[k] = non_default_params[k]

        if unsupported_params:
            if litellm.drop_params is True or (drop_params is not None and drop_params is True):
                for k in unsupported_params:
                    non_default_params.pop(k, None)
            else:
                raise UnsupportedParamsError(status_code=500, message=f"...")
```
(:4027-4048) — and the class that normalizes it:
```python
class UnsupportedParamsError(BadRequestError):
    def __init__(self, message, ..., status_code: int = 400, ...):
        self.status_code = 400   # forced, regardless of the raise-site argument
        self.message = f"litellm.UnsupportedParamsError: {message}"
```
(`exceptions.py:911-923`) — after validation, each provider maps via `<Provider>Config().map_openai_params(...)` (:4066+; e.g. anthropic :4068-4073).

**Flow:** provider config resolved via `ProviderConfigManager.get_provider_chat_config` → non-default extraction → supported list from module-level `get_supported_openai_params(model, custom_llm_provider)` with **openai fallback when None**, extended by `allowed_openai_params` → skip-list filter → drop-or-raise → per-provider `map_openai_params`.
**Invariant:** only *non-default* OpenAI params are ever validated; `UnsupportedParamsError` always carries status 400 because its constructor overwrites the passed code — a subclass invariant that overrides caller intent.
**Probe:** executed live at the pin: `get_optional_params(model="claude-3-5-sonnet", custom_llm_provider="ollama", logit_bias={...})` → `UnsupportedParamsError` status 400; same call with `drop_params=True` returns without `logit_bias`. Direct tests: `tests/local_testing/test_get_optional_params_functions_not_supported.py`, `tests/local_testing/test_get_optional_params_embeddings.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm", query: "get_optional_params", limit: 5 });
// rank-1 → litellm.litellm.utils.get_optional_params Function litellm/utils.py :3943-4541 (verified at pin)
```

## Verdict
Adopt the ladder order (defaults stripped first, skip-list, global-or-per-call drop flag, provider map last) and the openai fallback for unknown providers' supported lists. Adapt the skip-list and per-provider configs to your param surface; do NOT copy the accidental double `map_openai_params` call in the `anthropic_text` branch (:4074-4086, idempotent but wrong-shaped). Omit langchain-specific `n==1` patching unless you serve langchain clients. Caveat: embeddings/image-gen/transcription variants exist separately (utils.py :3011-3594) — next-pass target.
