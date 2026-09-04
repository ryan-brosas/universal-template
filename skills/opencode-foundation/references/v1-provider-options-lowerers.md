<!-- capsule-v2 -->
# V1 provider-options lowerers — how do you turn per-package legacy config options into wire headers, bodies, and SDK settings without a schema per vendor?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Legacy (V1) config lets users write provider options like `apiKey`, `baseURL`, `reasoningEffort` against a package name (`@ai-sdk/openai`, `@ai-sdk/anthropic`, ...). Each SDK package expects different header names, wire-case conventions, and option groupings. How do you normalize all of them from one small table?

## A package-keyed Lowerer table: provider() → {url, headers, body, settings}, request() → wire body
**Path/Symbol:** `packages/core/src/v1/config/provider-options.ts` (`get` :17-20, `raw` :22-27, `openai` :29-60, `anthropic` :62-87, `google` :89-105, `azure` :107-117, `bedrock` :119-126, `openaiCompatible` :128-140, `lowerers` table :142-160, `snake` :175-188).
**Signature:** `get(packageName?: string) → Lowerer` with `Lowerer = {provider(options) → ProviderResult, request(options) → Record<string, unknown>}`; `ProviderResult = {headers?, body?, url?, settings?}`.
**Data Shape:** input options are untyped `Readonly<Record<string, unknown>>`; output splits them into transport facts (url/headers), passthrough body, and SDK settings (everything unrecognized).

### Decisive source
```ts
// provider-options.ts:17-20 — prototype-safe table lookup, unknown → raw passthrough
export function get(packageName?: string): Lowerer {
  const key = packageName ?? ""
  return Object.hasOwn(lowerers, key) ? lowerers[key]! : raw
}
// :44-56 — openai.request: recursive snake_case, then FOLD reasoning twins into one object
const result = snake(options)
if (options.reasoningEffort !== undefined || options.reasoningSummary !== undefined) {
  result.reasoning = {
    ...(isRecord(result.reasoning) ? result.reasoning : {}),
    ...(options.reasoningEffort !== undefined ? { effort: options.reasoningEffort } : {}),
    ...(options.reasoningSummary !== undefined ? { summary: options.reasoningSummary } : {}),
  }
  delete result.reasoning_effort
  delete result.reasoning_summary
}
```

**Flow:** `get()` looks up the package name with `Object.hasOwn` (prototype-safe: `get("toString")` falls back to raw — test-pinned). Five lowerers: **openai** — apiKey→`Authorization: Bearer`, organization/project→`OpenAI-*` headers, baseURL→url, leftovers→settings; request recursively snake_cases and folds reasoningEffort/reasoningSummary into `reasoning:{effort,summary}` (deleting the snake twins) and textVerbosity into `text.verbosity`. **anthropic** — apiKey→`x-api-key`, authToken→Bearer; request folds effort/taskBudget into `output_config` and metadata.userId→`user_id`. **google** — apiKey→`x-goog-api-key`; request gathers thinkingConfig/responseModalities/mediaResolution/imageConfig into `generationConfig`, everything else stays camelCase. **azure** — `api-key` header + reuses openai.request. **bedrock** — NO url/header extraction (provider options pass through `direct`); request wraps the WHOLE options object into `additionalModelRequestFields`. **openaiCompatible** (+9 alias packages incl. cerebras/groq/mistral/xai/openrouter) — baseURL→url, everything else→settings, request only lowers reasoningEffort→`reasoning_effort`. Helpers: `headers()` drops non-string values; `compact()` drops undefined and returns undefined when EMPTY (so absent headers serialize as `headers: undefined`).
**Invariant:** unknown packages never crash and never leak prototype properties (Object.hasOwn, not `in`); the raw lowerer clones options without mutation; each lowerer is total over its documented option names — an option either lands in url/headers/body/settings or is dropped deliberately; request-level folding must DELETE the pre-snake-cased twins so keys never appear twice.
**Probe:** `packages/core/test/config/provider-options.test.ts` (224L, 8 `test` + 2 `test.each` groups): "keeps raw provider and request options unchanged" + "falls back to raw lowering for prototype property package names" pin the raw path and prototype safety; "lowers OpenAI provider and request options" pins header mapping + reasoning fold (`reasoning: {encrypted_content: true, effort: "high", summary: "auto"}`); "lowers Anthropic..." pins output_config; "lowers Google..." pins generationConfig gathering; "lowers Azure... uses OpenAI request lowering" pins the reuse; "lowers Amazon Bedrock..." pins additionalModelRequestFields wrapping; the 9-package test.each pins openaiCompatible aliasing; the 2-package test.each pins vertex→google/anthropic family routing. Source pin:
```bash
grep -c 'Object.hasOwn' packages/core/src/v1/config/provider-options.ts   # expect 1
grep -c 'additionalModelRequestFields' packages/core/src/v1/config/provider-options.ts # expect 1
grep -c 'generationConfig' packages/core/src/v1/config/provider-options.ts # expect 2
grep -c 'output_config' packages/core/src/v1/config/provider-options.ts   # expect 1
grep -c 'test.each' packages/core/test/config/provider-options.test.ts    # expect 2
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "ConfigProviderOptionsV1 lowerer provider request snake reasoning output_config generationConfig additionalModelRequestFields", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the table-of-lowerers shape: one pure function pair per SDK family, prototype-safe lookup, raw passthrough for unknowns, and a strict split into url/headers/body/settings. Adopt the fold-then-delete-twins pattern for grouped wire options. Adapt the per-package header names and case conventions to your SDK matrix; omit the V1 migration context (this module exists to keep legacy config working alongside the V2 catalog). Coverage caveat: Codebase Memory MCP not connected this session — Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
