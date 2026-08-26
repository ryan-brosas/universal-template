<!-- capsule-v2 -->
# engine-temperature-precedence — Who wins when engine params and call sites disagree about temperature?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** What is the temperature precedence across engines, and where does cost accrue?

## Temperature seam
**Path/Symbol:** `gui_agents/s3/core/engine.py` — LMMEngineOpenAI.generate (:42-68, pin comment :37), Anthropic (:91-122), Gemini (:176-201), OpenRouter (:225-250), AzureOpenAI (:278-311 incl. cost accrual :309-310), vLLM (:335-366 with extra_body repetition_penalty).
**Signature:** every `generate(messages, temperature=0.0, max_new_tokens=None, **kwargs)`; constructor accepts `temperature=None`.
**Data Shape:** Instance temperature = optional hard pin; call-site temperature = per-call default 0.0. Worker reads `worker_engine_params.get("temperature", 0.0)` (worker.py :49) and passes it on EVERY call; CodeAgent hardcodes temperature=1.

### Decisive source
```python
# OpenAI arm — instance pin wins outright (no fallback chain)
temperature=(temperature if self.temperature is None else self.temperature)
# comment at __init__: "Can force temperature to be the same (in the case of o3 requiring temperature to be 1)"

# Other arms use a two-level default:
temp = self.temperature if self.temperature is not None else temperature
```

**Flow:** CLI `--model_temperature` → engine_params["temperature"] → engine ctor stores as pin → generate resolves: OpenAI-style engines return pin-or-call value directly; Gemini/OpenRouter/Azure/vLLM compute temp then pass explicitly; Anthropic passes `temp` only in the non-thinking path (thinking path omits temperature entirely).
**Invariant:** (1) A configured pin cannot be overridden by any caller — this is how reasoning-models-requiring-fixed-temperature are supported without touching call sites. (2) The OpenAI arm resolves inline (:62) while the other five arms compute `temp = ...` first; two written FORMS exist: call-value-first checks (`temperature if self.temperature is None else self.temperature` :62, `self.temperature if temperature is None else temperature` :99 Anthropic and :190 Gemini) versus instance-first checks on OpenRouter/Azure/vLLM (:239/:301/:357) — a porter unifying them must preserve each arm's None-vs-value distinction, not copy one form everywhere. (3) Azure accrues cost PER CALL: `self.cost += 0.02 * ((total_tokens + 500) / 1000)` — the only engine with accounting. (4) vLLM alone sends top_p=0.8 + repetition_penalty=1.05 defaults via extra_body.
**Probe:** `grep -n 'self.temperature' gui_agents/s3/core/engine.py | grep -v 'self.temperature = ' | wc -l` → 9 (six generate-arm resolutions :62/:99/:190/:239/:301/:357 + three duplicate comments :238/:300/:356).
**Probe:** `grep -n 'self.cost += 0.02' gui_agents/s3/core/engine.py` → :310.
**Probe:** `grep -n 'extra_body={"repetition_penalty"' gui_agents/s3/core/engine.py` → :364.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "generate temperature max_new_tokens backoff", limit: 5 });
```

## Verdict
Adopt instance-pin-beats-call-site temperature semantics for models with mandated temperatures; adapt per-engine quirks to your SDK versions; omit the ad-hoc Azure cost formula unless reproducing their accounting.
