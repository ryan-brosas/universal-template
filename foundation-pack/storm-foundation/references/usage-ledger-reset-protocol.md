<!-- capsule-v2 -->
# Usage-ledger reset protocol — how do you attribute token/query spend per pipeline stage without a metering service?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How must LM objects, retriever objects, and the engine cooperate (naming convention + get-and-reset) so every stage's cost lands in the right bucket exactly once?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/interface.py:Engine.apply_decorators` (:512-522) + `log_execution_time_and_lm_rm_usage` (:492-510) + `LMConfigs.collect_and_reset_lm_usage` (:452-473).
**Signature:** `def apply_decorators(self)` wraps every `run_*` method; `collect_and_reset_lm_usage() -> Dict[model_name, {"prompt_tokens": int, "completion_tokens": int}]`; RM twin `Retriever.collect_and_reset_rm_usage -> Dict[rms_name, int]` (:273-286).
**Data Shape:** `self.time[func_name]`, `self.lm_cost[func_name]`, `self.rm_cost[func_name]` keyed by the wrapped method's name; usage dicts merge across all `_lm`-suffixed attributes by summing prompt/completion tokens per model.

### Decisive source
```python
methods_to_decorate = [m for m in dir(self)
    if callable(getattr(self, m)) and m.startswith("run_")]
for method_name in methods_to_decorate:
    setattr(self, method_name,
        self.log_execution_time_and_lm_rm_usage(getattr(self, method_name)))
# inside wrapper:
self.lm_cost[func.__name__] = self.lm_configs.collect_and_reset_lm_usage()
if hasattr(self, "retriever"):
    self.rm_cost[func.__name__] = self.retriever.collect_and_reset_rm_usage()

# LMConfigs side — the "_lm" suffix IS the discovery mechanism:
for attr_name in self.__dict__:
    if "_lm" in attr_name and hasattr(getattr(self, attr_name), "get_usage_and_reset"):
        combined_usage.append(getattr(self, attr_name).get_usage_and_reset())
# then sum prompt_tokens/completion_tokens per model name
```

**Flow:** Every provider wrapper (`LitellmModel`, `OpenAIModel`, `DeepSeekModel`, `AzureOpenAIModel`, `GroqModel`, `ClaudeModel`, `VLLMClient`, `TogetherClient`, `GoogleModel`) implements `log_usage(response)` accumulating under `threading.Lock` and `get_usage_and_reset()` returning `{model: {prompt_tokens, completion_tokens}}` then zeroing. The engine decorator drains ALL of them after each stage; `summary()` prints the ledger; `reset()` clears it.
**Invariant:** (1) Discovery is by `_lm` SUBSTRING in attribute names — an LM stored under a non-`_lm` attribute is silently invisible to accounting. (2) Every consumer MUST drain (`get_usage_and_reset`), never read-only, or double-counting follows on the next stage. (3) Per-provider field names differ (`input_tokens/output_tokens` for Anthropic, `prompt_token_count/candidates_token_count` for Gemini) but the ledger contract normalizes to prompt/completion keys. (4) `init_check()` warns on any None `_lm` slot before run.
**Probe:** deterministic pins — interface.py:517 `"run_"` prefix filter and storm_wiki/engine.py:208-209 `init_check()+apply_decorators()` wiring byte-verified GREEN this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "log_execution_time_and_lm_rm_usage apply_decorators", limit: 10 });
```

## Verdict
Adopt the naming-convention + drain-to-account pattern for any multi-stage LLM pipeline needing per-stage cost attribution; adapt the suffix/attribute names; omit the print-based `summary()` in favor of structured export. Caveat: no upstream tests; source-pinned.
