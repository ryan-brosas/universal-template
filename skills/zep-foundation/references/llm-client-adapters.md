<!-- capsule-v2 -->
# LLM client adapters — how do optional provider SDKs plug into a complete(prompt) -> str protocol?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How are OpenAI/Anthropic/OpenAI-compatible endpoints wrapped, and what do the wrappers guarantee?

## llm/openai.py / llm/anthropic.py
**Path/Symbol:** `ingestion/src/zep_ingest/llm/openai.py:19` (`OpenAILLM`), `:48` (`OpenAICompatibleLLM`); `llm/anthropic.py:9` (`AnthropicLLM`).
**Signature:** `complete(self, prompt: str) -> str`; constructors take an injected `client` OR build one (ZepDependencyError with exact pip command when SDK missing).
**Data Shape:** Defaults: gpt-5-mini / claude-haiku-4-5, max_tokens=200 (require_int_range ≥1). OpenAICompatibleLLM REQUIRES model+base_url when constructing its client ("both are provider-specific").

### Decisive source
```python
# openai.py — the universal connector pattern:
# OpenAICompatibleLLM is the universal connector: point it at any
# OpenAI-compatible /chat/completions endpoint — LiteLLM, Ollama, vLLM,
# OpenRouter, Together, Groq, Azure-compatible proxies — which is the
# pattern Zep's own docs recommend for bring-your-own-provider setups.

# anthropic.py — read by block type, not position:
text = next((block.text for block in response.content if block.type == "text"), "")
return str(text).strip()

# openai.py — reasoning-model-safe kwarg:
response = self.client.chat.completions.create(
    model=self.model,
    messages=[{"role": "user", "content": prompt}],
    max_completion_tokens=self.max_tokens,
)
```

**Flow:** construct (inject or build; missing SDK ⇒ ZepDependencyError naming `pip install zep-ingest[openai|anthropic]`) → complete() sends single user message → strip whitespace → return. Both are optional conveniences: anything implementing complete(prompt)->str satisfies LLMClient directly.
**Invariant:** Anthropic responses may carry thinking blocks — text extraction must filter by block.type, never content[0]. OpenAI path uses max_completion_tokens (newer-reasoning-models kwarg). Injected clients are duck-typed so tests pass mocks.
**Probe:** `grep -c 'def test' ingestion/tests/test_llm_adapters.py` → ≥8; import probe `python3 -c "import sys;sys.path.insert(0,'src');from zep_ingest.llm.anthropic import AnthropicLLM"` (works without anthropic installed until client=None).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "OpenAICompatibleLLM AnthropicLLM complete adapter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one-method protocol + injectable clients + dependency-error-with-install-command + type-based response extraction; adapt defaults to your models; omit provider-specific kwargs you don't target.
