<!-- capsule-v2 -->
# provider-normalization-gate — How do budget providers alias onto the OpenAI engine, and when must init fail?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** What normalization do ollama/deepseek/qwen apply at LMMAgent construction, and what is the fail-vs-default policy per provider?

## Provider alias seam
**Path/Symbol:** `gui_agents/s3/core/mllm.py:LMMAgent.__init__` (:18-113); direct tests `tests/test_providers.py` (5 tests, all pinning this seam).
**Signature:** `LMMAgent(engine_params=None, system_prompt=None, engine=None)` — engine_type ∈ {openai, anthropic, azure, vllm, huggingface, gemini, open_router, parasail, ollama, deepseek, qwen}.
**Data Shape:** Alias engines rewrite `engine_params["base_url"]`/`["api_key"]` IN PLACE then construct LMMEngineOpenAI. Precedence: explicit param > env var > provider default (deepseek/qwen) or hard error (ollama).

### Decisive source
```python
elif engine_type == "ollama":
    if not engine_params.get("base_url"):
        base_url = os.getenv("OLLAMA_HOST")
        if base_url:
            if not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"
            engine_params["base_url"] = base_url
        else:
            raise ValueError("Ollama endpoint must be provided via 'base_url' parameter or 'OLLAMA_HOST' environment variable.")
    if not engine_params.get("api_key"):
        engine_params["api_key"] = "ollama"          # placeholder key
elif engine_type == "deepseek":
    ...  # default https://api.deepseek.com + /v1; api_key from DEEPSEEK_API_KEY else ValueError
elif engine_type == "qwen":
    ...  # default dashscope compatible-mode/v1; QWEN_API_KEY else ValueError
```

**Flow:** engine_type dispatch → alias normalization (/v1 suffix appended only when missing) → shared LMMEngineOpenAI construction → messages initialized with a default system prompt ("You are a helpful assistant.") when none given.
**Invariant:** (1) Ollama has NO default URL — missing both param and OLLAMA_HOST raises at INIT time (fail-fast), while deepseek/qwen fall back to cloud defaults but still REQUIRE their API keys from env. (2) The `/v1` append is idempotent (`endswith("/v1")` guard). (3) api_key="ollama" placeholder exists because the OpenAI client demands a non-empty key. (4) Passing a pre-built `engine=` bypasses all normalization — tests exploit this indirectly via patched envs.
**Probe:** `tests/test_providers.py::test_ollama_missing_config` asserts the exact ValueError message at construction.
**Probe:** `tests/test_providers.py::test_ollama_valid_config_env` pins OLLAMA_HOST=http://env-host:11434 → base_url http://env-host:11434/v1 (the /v1 append).
**Probe:** `grep -n 'engine_params\["api_key"\] = "ollama"' gui_agents/s3/core/mllm.py` → :54.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "LMMAgent engine_type ollama deepseek qwen", limit: 5 });
```

## Verdict
Adopt in-place param normalization with per-provider fail-vs-default policy and idempotent /v1 appending; adapt the provider set; omit nothing — the asymmetry (local=strict, hosted=lenient) is deliberate and test-pinned.
