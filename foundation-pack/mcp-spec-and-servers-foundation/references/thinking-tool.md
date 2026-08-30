<!-- capsule-v2 -->
# Sequential-thinking tool — a state-machine-as-tool with coercive schemas and structured output mirroring

**Source:** modelcontextprotocol/servers MIT `main@76d64c8`; Codebase Memory `servers`. **Question:** How does the reference "thinking" server accept messy LLM input robustly while returning both text and validated structured content?

## Safe boolean/number coercion + dual content/structuredContent response
**Path/Symbol:** `src/sequentialthinking/index.ts` (`coercedBoolean` preprocess :9–16 — string "true"/"false" case-insensitively become booleans before z.boolean(); registration :25–123 with long behavioral description as prompt engineering, `z.coerce.number().int().min(1)` for thought counters :86–92, `annotations` read-only hints :94–99, `outputSchema` :100–106; handler :108–122 parses the JSON text back into `structuredContent`); engine `src/sequentialthinking/lib.ts:SequentialThinkingServer.processThought`.

**Signature:** handler `(args) => { const result = thinkingServer.processThought(args); if (result.isError) return result; return {content: result.content, structuredContent: JSON.parse(result.content[0].text)}; }`.

### Decisive source
```ts
// src/sequentialthinking/index.ts:8-16 — the coercion shim
/** Safe boolean coercion that correctly handles string "false" */
const coercedBoolean = z.preprocess((val) => {
  if (typeof val === "boolean") return val;
  if (typeof val === "string") {
    if (val.toLowerCase() === "true") return true;
    if (val.toLowerCase() === "false") return false;
  }
  return val;
}, z.boolean());
```
The tool description (:29–82) is itself the interface contract: when to use, how to revise/branch thoughts, and the 11-step protocol — an example of encoding behavior guidance in tool prose rather than code. Response path (:108–122): engine returns `{isError?, content:[{type:"text", text:<JSON>}]}`; error results pass through untouched (isError routing per schema-registration.md); success re-parses its own JSON text into `structuredContent` so clients with output-schema validation get typed data while plain-text clients see the same bytes.

**Flow:** LLM sends possibly-stringy args → zod preprocess/coerce normalizes types at the boundary → processThought appends to thought history / branch map → returns JSON state summary {thoughtNumber, totalThoughts, nextThoughtNeeded, branches, thoughtHistoryLength} → handler mirrors it as text + structuredContent.

**Invariant:** validation happens through COERCION-first schemas because LLM-emitted arguments arrive stringified more often than spec-perfect; error results must short-circuit BEFORE structured parsing (parsing an error payload would throw). Porters who use strict z.boolean() turn every `"false"` into a -32602.

**Probe:** graph anchors: `search_graph --name-pattern coercedBoolean|processThought --project servers`; test coverage lives in the SDK-level integration runs — this repo's sequentialthinking has no dedicated unit suite (recorded honestly); the vitest harness pattern from everything/__tests__ applies if you add one.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "coercedBoolean processThought outputSchema structuredContent sequential thinking", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt preprocess-coercion input schemas for LLM-facing tools, isError short-circuit ordering, and text/structuredContent dual emission; adapt the description protocol to your own reasoning workflow; omit the thought-history internals unless building a branching-reasoning product.
