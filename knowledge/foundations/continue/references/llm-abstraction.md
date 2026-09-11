<!-- capsule-v2 -->
# LLM abstraction — capability flags and the single OpenAI-shaped adapter boundary

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does Continue normalize every provider onto one interface, and how are per-provider capabilities expressed so the FIM/chat/completions routing stays correct?

## BaseLLM: capability flags over interface methods
**Path/Symbol:** `core/llm/index.ts:BaseLLM` (90–…).
**Signature:** `abstract class BaseLLM implements ILLM` with `static providerName`, `supportsFim()`, `supportsImages()`, `supportsCompletions()`, `supportsPrefill()`, `underlyingProviderName`.
**Data Shape:** provider name is read from the CLASS (`static providerName`), so one provider class serves many registered variants; `underlyingProviderName` defaults to `providerName` (overridden for aliases like openrouter→openai).

### Decisive source
```ts
supportsFim(): boolean { return false; }                    // default; providers override
supportsImages(): boolean { return modelSupportsImages(this.providerName, this.model, this.title, this.capabilities); }
supportsCompletions(): boolean {
  if (["openai","azure"].includes(this.providerName)) {
    if (this.apiBase?.includes("api.groq.com") || this.apiBase?.includes("api.mistral.ai")
        || this.apiBase?.includes(":1337") || this.apiBase?.includes("integrate.api.nvidia.com")
        || this._llmOptions.useLegacyCompletionsEndpoint?.valueOf() === false) return false;
    // "Jan + Groq + Mistral don't support completions :( / Seems to be going out of style..."
  }
  if (["groq","mistral","deepseek"].includes(this.providerName)) return false;
  return true;
}
supportsPrefill(): boolean { return ["ollama","anthropic","mistral"].includes(this.providerName); }
```

**Flow:** `constructLlmApi` from `@continuedev/openai-adapters` maps every provider's native API onto an OpenAI-shaped `BaseLlmApi`/`ChatCompletionCreateParams`. All request bodies convert near the boundary: `toChatBody`, `toCompleteBody`, `toFimBody` (`core/llm/openaiTypeConverters.ts`); responses via `fromChatCompletionChunk`/`fromChatResponse`. Exponential backoff wraps retries (`core/util/withExponentialBackoff.ts`). FIM gets its own body path (`toFimBody`, index.ts:619) rather than squeezing prompts into chat — `supportsFim()` toggles whether the adapter ever routes there. Tool-calling applies `applyToolOverrides` at the same boundary.

**Invariant:** ALL provider traffic flows through one OpenAI-shaped adapter at a single boundary; body builders are named by destination shape (chat/complete/fim); capability flags encode known ecosystem weirdness as commented exceptions rather than per-provider branching in callers.

**Probe:** `core/llm/autodetect.vitest.ts` locks template detection per model name; `core/llm/countTokens.test.ts` + `getAdjustedTokenCount.test.ts` pin token accounting under prompt pruning — the exact math the FIM pipeline budgets against.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "BaseLLM supportsFim supportsCompletions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capability-flag base class, the class-level provider name, the OpenAI-shaped adapter boundary with destination-named body builders, and the backoff wrapper; adapt the provider allow/deny lists and API-base heuristics to host; omit provider-specific transports and onboarding. Coverage caveat: graph metadata `metadata_match`; `core/llm/llms/*` provider files are numerous but share this one base contract.
