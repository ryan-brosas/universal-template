<!-- capsule-v2 -->
# streamSimple delegation adapter — how do you route a custom provider through a stock OpenAI-compatible streamer without shadowing the host's builtin?

**Source:** pi-hypercharm-provider MIT `main@4520704` (pass 4); Codebase Memory project `pi-hypercharm-provider`. **Question:** A host hands your `streamSimple(model, context, options)` a model registered under YOUR api name — how do you adapt it into an existing SDK stream call, and where do test doubles plug in?

## streamHypercharm adapter contract
**Path/Symbol:** `index.ts:570-619` (`streamHypercharm`; graph: `USAGE makeProviderConfig → streamHypercharm`, no CALLS edges — it is passed as the `streamSimple` hook value). Interceptor interior and thinking clamp are owned by teed-usage-capture.md / thinking-level-mapping.md; this capsule owns the adapter frame.
**Signature:** `(model: any, context: any, options?: SimpleStreamOptions) => AssistantMessageEventStream`.
**Data Shape:** in: host model record (api `"hypercharm"`, baseUrl from registration), request context, options possibly carrying `{apiKey?, reasoning?, fetch?}`. out: whatever pi-ai's `streamOpenAICompletions` returns for the NORMALIZED model.

### Decisive source
```ts
const apiKey = (options as any)?.apiKey || cachedApiKey || "";
if (!apiKey) { throw new Error(`No API key for HyperCharm. ...`); }

// Force the model into the family the stock streamer implements:
const hyperModel = { ...model, api: "openai-completions", baseUrl: model.baseUrl || BASE_URL };

// pi hands options.reasoning (raw level); strip it AFTER converting so the
// downstream never sees an option it does not understand:
const clampedReasoning = options?.reasoning ? clampThinkingLevel(hyperModel, options.reasoning) : undefined;
const reasoningEffort = clampedReasoning === "off" ? undefined : clampedReasoning;
const { reasoning: _reasoning, ...streamOptions } = (options ?? {}) as any;

// Test/injection seam: caller-supplied fetch wins, else platform global.
const upstreamFetch = (streamOptions as any).fetch ?? globalThis.fetch;

return streamOpenAICompletions(hyperModel, context, {
	...streamOptions,
	fetch: metaFetch,
	reasoningEffort,
	apiKey,
} as any);
```

**Flow:** key gate (throw) → normalize model (`api` forced to the streamer's real family `"openai-completions"` while registration stays `"hypercharm"`; baseUrl defaulted) → clamp+convert reasoning, then REST-strip the raw `reasoning` key → resolve injection seam (`options.fetch ?? globalThis.fetch`) and wrap it as the per-request `metaFetch` interceptor → delegate everything to the stock streamer with `{...rest, fetch, reasoningEffort, apiKey}`.
**Invariant:** the custom api name in `makeProviderConfig` is load-bearing NAMESPACING, not decoration — it makes this extension's `streamSimple` register as its own handler so it can never shadow pi's built-in openai-completions pipeline used by other providers (source comment `index.ts:1004-1006`). The adapter must re-translate before delegation: the stock streamer only knows `openai-completions`, reads ONLY `reasoningEffort` (never `reasoning`), and gets its key explicitly. The `?? globalThis.fetch` fallback keeps the wrapper honest under concurrency — each invocation closes over ITS OWN interceptor instead of patching a global (see teed-usage-capture.md).
**Probe:** no upstream runner for index.ts — deterministic probe P-ADAPT executed this pass via `node -e`: spread-normalization `{...m, api:"openai-completions", baseUrl:m.baseUrl||"DEF"}` preserved unknown fields, overrode api, defaulted only-falsy baseUrl (`undefined`→DEF, kept `"http://x"`); rest-strip removed exactly the `reasoning` key. Source pins :575-618.
**Coverage caveat:** untested upstream; smoke suite covers status.ts only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "pi-hypercharm-provider",
  query: "MATCH (a)-[r]->(b) WHERE b.name = 'streamHypercharm' RETURN type(r), a.qualified_name" });
// → USAGE makeProviderConfig→streamHypercharm; DEFINES from index.ts.__file__
```

## Verdict
Adopt the adapter frame: namespaced registration name + per-call family/baseUrl normalization + option translation with rest-strip + injectable upstream fetch. Adapt the target streamer import to your stack. Omit the metaFetch interior here (owned by teed-usage-capture.md).
