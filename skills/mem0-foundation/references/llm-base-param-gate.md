<!-- capsule-v2 -->
# LLM base param-gate — how does one provider SDK shape requests for reasoning models, GPT-5, and plain models without tripping API rejections?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** which parameters survive for which model family (temperature? max_tokens vs max_completion_tokens? reasoning_effort?), and how does an explicit config override beat the name heuristic without breaking versioned model IDs?

## Connected graph-selected seam
**Path/Symbol:** `mem0/llms/base.py`: `LLMBase.__init__` config normalization (:13-28), `_validate_config` (:30-36), `_is_reasoning_model` (:38-75), `_uses_max_completion_tokens` (:77-94), `_get_supported_params` (:96-129), `_get_common_params` (:149-170); OpenAI consumer `mem0/llms/openai.py` `generate_response` (:85-150, store opt-in :130-134) + default model fill (:39-40). Direct tests `tests/llms/test_openai.py`: `test_gpt5_mini_not_classified_as_reasoning` (:290), `test_is_reasoning_model_classification` (:312), `test_is_reasoning_model_explicit_override` (:333), `test_store_not_sent_by_default` (:236), `test_gpt5_uses_max_completion_tokens` (:380), `test_gpt4_uses_max_tokens` (:402).
**Signature:** `_is_reasoning_model(model: str) -> bool`; `_uses_max_completion_tokens(model: str) -> bool`; `_get_supported_params(**kwargs) -> Dict`; `_get_common_params(**kwargs) -> Dict`.
**Data Shape:** classification inputs are raw model strings possibly carrying provider prefixes (`openai/o3-mini`, Azure `gpt-5.4-nano-2026-03-17`); reasoning allowlist {o1, o1-preview, o3-mini, o3, gpt-5, gpt-5o, gpt-5o-mini, gpt-5o-micro} + prefix families o1-/o1./o3-/o3.; explicit override reads `config.is_reasoning_model` (None = fall back to name).

### Decisive source
```python
explicit = getattr(self.config, "is_reasoning_model", None)
if explicit is not None:
    return explicit                       # override wins BEFORE any string matching
base_model = model_lower.rsplit("/", 1)[-1]   # strip provider prefix first
if base_model in reasoning_models: return True
# o1/o3 dated snapshots count; GPT-5.x point releases do NOT
if any(base_model.startswith(p) for p in ["o1-", "o1.", "o3-", "o3."]): return True

def _uses_max_completion_tokens(self, model):
    return (model or "").lower().rsplit("/", 1)[-1].startswith("gpt-5")   # WHOLE GPT-5 family

def _get_common_params(self, **kwargs):
    params = {"temperature": self.config.temperature, "top_p": self.config.top_p}
    if self._uses_max_completion_tokens(model):
        params["max_completion_tokens"] = self.config.max_tokens      # rename, never drop
    else:
        params["max_tokens"] = self.config.max_tokens
```

**Flow:** subclass ctor converts dict/base-config into its typed config → `super().__init__` normalizes None/dict → `_validate_config` demands a `model` attribute → at call time `generate_response` builds `params = _get_supported_params(...)`; the reasoning branch keeps ONLY messages/response_format/tools/tool_choice (+ optional reasoning_effort) and silently drops temperature/top_p/max_tokens entirely, while the plain branch sends temperature+top_p+the token param → OpenAI consumer then adds `store` ONLY when explicitly configured (OpenAI-compatible backends reject unknown fields) and OpenRouter mode swaps model for `models[]+route`.
**Invariant:** (1) prefix-strip (`rsplit("/",1)[-1]`) precedes every match — matching on the full string misses `openai/o3-mini`; (2) GPT-5 is NOT in the reasoning allowlist (it accepts temperature) but IS in the max_completion_tokens set — conflating the two tables breaks either direction; (3) the token-param is RENAMED not omitted for GPT-5 (dropping it silently caps output at provider default); (4) `store` must stay opt-in or every Gemini/Groq/vLLM-compatible backend 400s; (5) reasoning branch drops temperature by design — adding it back raises on o1/o3.
**Probe:** `tests/llms/test_openai.py::test_gpt5_mini_not_classified_as_reasoning`, `::test_gpt5_uses_max_completion_tokens` vs `::test_gpt4_uses_max_tokens`, `::test_reasoning_model_with_reasoning_effort` / `::test_non_reasoning_model_ignores_reasoning_effort`, `::test_store_not_sent_by_default` + explicit true/false twins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_is_reasoning_model _get_supported_params _get_common_params", limit: 10, fields: ["signature", "name", "file"] });
```
(resolves llms/base.py functions; consumers visible via CALLS edges from openai/azure/deepseek/groq/lmstudio/minimax/together/vllm/sarvam/xai)

## Verdict
Adopt the two-table split (reasoning-allowlist ≠ completion-token-rename table) and the explicit-override-first ladder verbatim; adapt the allowlist contents as your provider roster evolves (keep the prefix-strip invariant); omit the per-subclass typed-config conversion dance if your configs are already typed (keep dict→config back-compat normalization).
