<!-- capsule-v2 -->
# Tokenizer selection + model multiplier — which tokenizer counts tokens, and why is the count inflated for some models?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** When no vendor tokenizer is available, how does Continue pick an encoding for ANY model name, and what correction must a porter apply before trusting the number?

## The encoding ladder
**Path/Symbol:** `core/llm/countTokens.ts:encodingForModel` (:73-85), `asyncEncoderForModel` (:56-71), `countTokens` (:112-132); `core/llm/getAdjustedTokenCount.ts:getAdjustedTokenCountFromModel`.
**Signature:** `countTokens(content: MessageContent, modelName = "llama2"): number`; `getAdjustedTokenCountFromModel(baseTokens: number, modelName: string): number`.
**Data Shape:** in → string or `MessagePart[]`; out → integer token count. Module-global singletons: lazy `gptEncoding` (js-tiktoken `gpt-4`) and one shared `llamaEncoding`/`LlamaAsyncEncoder`.

### Decisive source
```ts
function encodingForModel(modelName: string): Encoding {
  const modelType = autodetectTemplateType(modelName);
  if (!modelType || modelType === "none") {
    if (!gptEncoding) { gptEncoding = _encodingForModel("gpt-4"); }  // lazy, cached
    return gptEncoding;
  }
  return llamaEncoding;   // any chat-template-known model counts with the LLAMA tokenizer
}
```
```ts
// getAdjustedTokenCount.ts — llama tokenizer UNDERCOUNTS these vendors' real tokenizers,
// so inflate by measured ratio + ~10% safety (estimates per the linked article)
const ANTHROPIC_TOKEN_MULTIPLIER = 1.23;
const GEMINI_TOKEN_MULTIPLIER   = 1.18;
const MISTRAL_TOKEN_MULTIPLIER  = 1.26;
export function getAdjustedTokenCountFromModel(baseTokens, modelName) {
  let multiplier = 1;
  const lowerModelName = modelName?.toLowerCase() ?? "";
  if (lowerModelName.includes("claude")) multiplier = ANTHROPIC_TOKEN_MULTIPLIER;
  else if (lowerModelName.includes("gemini")) multiplier = GEMINI_TOKEN_MULTIPLIER;
  else if (lowerModelName.includes("stral") || lowerModelName.includes("mixtral"))
    multiplier = MISTRAL_TOKEN_MULTIPLIER;   // catches mistral/mixtral/codestral/devstral
  return Math.ceil(baseTokens * multiplier);
}
```
The final line of `countTokens` applies it: `return getAdjustedTokenCountFromModel(baseTokens, modelName)`.

**Flow:** model name → `autodetectTemplateType`: known chat template ⇒ llama tokenizer; unknown/none ⇒ lazy-cached gpt-4 tiktoken. Count text parts (`part.text ?? ""`), images flat at **1024 tokens**, then multiply by vendor factor and ceil.
**Invariant:** The DEFAULT model name is `"llama2"` "because the tokenizer tends to produce more tokens" — i.e., counting errs HIGH on unknown models, never low. Every budget decision downstream consumes the MULTIPLIED count, so callers must not re-adjust. The `"stral"` substring deliberately matches the whole mistral family — porters matching only `"mistral"` silently under-count codestral/devstral budgets.
**Probe:** `core/llm/countTokens.test.ts:18/:24` pin simple-string and MessagePart[] counting; `core/llm/getAdjustedTokenCount.test.ts:10/:17/:24/:38/:43` pin claude/gemini/mistral multipliers, undefined-name handling, and case-insensitivity.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "countTokens encodingForModel getAdjustedTokenCountFromModel", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-bucket tokenizer choice (template-known ⇒ cheap shared llama encoding, unknown ⇒ gpt tiktoken) plus vendor multiplier inflation with `Math.ceil`; adapt multipliers as you measure your own models; omit the worker-pool async encoder path (packaging workaround documented in-source). Tests exist and pass at this pin; caveat: multipliers are estimates from a third-party article, cited in source comments.
