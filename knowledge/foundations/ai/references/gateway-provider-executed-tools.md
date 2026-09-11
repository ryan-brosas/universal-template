<!-- capsule-v2 -->
# Gateway provider-executed search tools — how does a provider ship a server-side tool with zero execute function?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the factory shape for tools the GATEWAY executes, and what is the input/output contract?

## createProviderExecutedToolFactory + config closure
**Path/Symbol:** `packages/gateway/src/tool/exa-search.ts:exaSearchToolFactory` (338–346) + `exaSearch` wrapper (350–352); siblings `parallel-search.ts`, `perplexity-search.ts` (same pattern).
**Signature:** `createProviderExecutedToolFactory<Input, Output, Config>({ id: 'gateway.exa_search', inputSchema, outputSchema })` → called with `config` returns a tool with NO local `execute`.
**Data Shape:** Input uses snake_case wire fields (`num_results`, `include_domains`, `contents.text.max_characters`) each with `.describe()` prompt text; Output is a z.union of success response (`requestId, results[], costDollars?`) and typed error object (`error: enum('api_error'|'rate_limit'|'timeout'|'invalid_input'|'configuration_error'|'execution_error'|'unknown'), statusCode?, message`) — errors are DATA in the output union, not thrown. Optional per-call `config` supplies defaults (type, numResults, category, domains, contents).

### Decisive source
```ts
export const exaSearchToolFactory = createProviderExecutedToolFactory<
  ExaSearchInput, ExaSearchOutput, ExaSearchConfig
>({
  id: 'gateway.exa_search',
  inputSchema: exaSearchInputSchema,
  outputSchema: exaSearchOutputSchema,
});
export const exaSearch = (config: ExaSearchConfig = {}): ReturnType<typeof exaSearchToolFactory> =>
  exaSearchToolFactory(config);
```

**Flow:** user calls `gateway.tools.exaSearch({numResults: 5})` → tool descriptor (schemas + config) rides the model request → gateway executes server-side → result validated against outputSchema on return.
**Invariant:** The tool ID is namespaced `gateway.*` — it must match what the service registered or routing fails server-side. Because execution is remote, there is deliberately no `execute`; porters adding one convert a provider-executed tool into a client-executed one and double-bill. Failure-as-data keeps the agent loop alive: the model can read `{error: 'rate_limit', message}` and react.
**Probe:** `grep -cF "id: 'gateway.exa_search'" packages/gateway/src/tool/exa-search.ts` → `1`. Direct-test caveat: NO unit tests exist for `src/tool/*` (verified by directory listing) — coverage relies on examples (`examples/ai-functions/src/*/gateway/tool-exa-search.ts`) and schema round-trip at runtime.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "exaSearchToolFactory createProviderExecutedToolFactory gateway.exa_search", limit: 10 });
```
Resolves line-exact: `exaSearch Function tool/exa-search.ts 350-352` (+ example call sites).

## Verdict
Adopt the factory+closure shape and failure-as-data union for remotely executed tools; adapt ids/schema fields to your service's registry; note the direct-test gap when re-verifying this capsule.
