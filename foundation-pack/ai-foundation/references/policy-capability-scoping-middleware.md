<!-- capsule-v2 -->
# Capability-scoping middleware — how do you hide tools from the model (not just deny calls) with a policy engine, failing closed?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** an approval gate only blocks calls after the model emits them — how does a middleware narrow the tool list BEFORE the call so the model never sees disallowed tools at all?

## opaCapabilityMiddleware — allowlist tool narrowing in transformParams
**Path/Symbol:** `packages/policy-opa/src/opa/opa-capability-middleware.ts:55` (`export function opaCapabilityMiddleware`); transform body :67–115; strict allowlist parser `extractAllowedNameSet` :117–131.

**Signature:**
```ts
function opaCapabilityMiddleware(opts: {
  client: PolicyClient; path: string;
  toInput?: (args: { messages; providerOptions }) => unknown;
}): LanguageModelV4Middleware;  // transformParams narrows params.tools
```

**Data Shape:** the OPA rule returns `string[]` of allowed names OR `{tools: string[]}`. Function tools match by `name`; provider tools match by dotted `id` (`<provider>.<tool>`) OR bare `name` — an allowlist authored with the bare name keeps the tool. Default input: `{messages, providerOptions}`.

### Decisive source
```ts
async transformParams({ params }) {
  if (params.tools == null || params.tools.length === 0) return params;  // nothing to filter
  const outcome = await evaluatePolicy(client, path, input);
  if (!outcome.ok) return { ...params, tools: undefined };        // fail closed: NO tools
  const allowed = extractAllowedNameSet(outcome.result);
  if (allowed == null) return { ...params, tools: undefined };    // malformed allowlist: NO tools
  let removed = false;
  const filtered = params.tools.filter(t => {
    const keep = t.type === 'function'
      ? allowed.has(t.name)
      : allowed.has(t.id) || allowed.has(t.name);
    if (!keep) removed = true;
    return keep;
  });
  if (!removed) return params;  // preserve object identity when nothing was dropped
  return { ...params, tools: filtered };
}
```

**Flow:** model call → `transformParams` → empty tools short-circuit (evaluator never called) → policy evaluation → error or malformed allowlist ⇒ `tools: undefined` (the model is told it has NO tools) → otherwise filter to the allowlist → identity preserved when nothing dropped so downstream middleware can no-op on reference equality.

**Invariant:** fail-closed in BOTH failure modes — evaluator error and malformed result (including a single non-string item poisoning the whole list via `extractAllowedNameSet` returning null) set `tools: undefined`; misconfiguration must never silently widen capabilities. The rationale is two-fold per the source comment: defense in depth (a bug in the approval policy still cannot expose tools) and capability disclosure (the model says "I don't have access to that tool" instead of "[approval denied]", and doesn't waste tokens on tools it cannot call).

**Probe:** `packages/policy-opa/src/opa/opa-capability-middleware.test.ts` (10 cases): string[] allowlist filters function tools (:43–64); provider tool kept by dotted id (:66–84) and by bare name (:86–104); `{tools:[...]}` object form (:106–121); malformed result drops every tool (:123–136); client throw drops every tool (:138–153); no-tools params pass through by reference with evaluator NOT called (:155–171); identity preserved when nothing dropped (:173–187); custom `toInput` (:189–214); allowlist matching nothing yields `[]` not undefined (:216–229).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "opaCapabilityMiddleware transformParams tools allowlist fail closed", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: opa-capability-middleware.ts :55, then its test describe :42.

## Verdict
Adopt capability-scoping as the complement to call-time approval for any policy-gated agent; adapt the allowlist source (your engine, a static config) and the tool-identity matching to your tool model; omit the LanguageModelV4Middleware typing if your host has a different request-transform seam. Coverage caveat: none — fully test-pinned (10 cases).
