<!-- capsule-v2 -->
# Completion API — how does completion/complete autocomplete prompt args and template URIs, and what are its hard bounds?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What is the exact `completion/complete` contract — reference types, argument context threading, the 100-item cap, and error mapping?

## One request, two reference types
**Path/Symbol:** `docs/specification/draft/server/utilities/completion.mdx` (whole; capability :33–43; request/response :45–131; ref types :133–141; result rules :142–149; errors :185–193); wire types `schema/draft/schema.ts` (`CompleteRequestParams` :2593–2618, `CompleteRequest` :2628–2631, `CompleteResult` :2644–2661, `ResourceTemplateReference` :2680–2688, `PromptReference` :2695–2697).

**Data Shape:** capability `completions: {}`. Request params: `{ ref: PromptReference | ResourceTemplateReference, argument: { name, value }, context?: { arguments?: Record<string,string> } }`. Refs: `{ type: "ref/prompt", name }` or `{ type: "ref/resource", uri }` (URI **or URI template**, e.g. `file:///{path}`). Result: `{ completion: { values: string[], total?, hasMore? } }`.

### Decisive source
```ts
// schema.ts:2644-2660 (the hard bound + pagination flags)
export interface CompleteResult extends Result {
  completion: {
    // An array of completion values. Must not exceed 100 items.
    // @maxItems 100
    values: string[];
    // The total number of completion options available. This can exceed
    // the number of values actually sent in the response.
    total?: number;
    // Indicates whether there are additional completion options beyond
    // those provided in the current response, even if the exact total
    // is unknown.
    hasMore?: boolean;
  };
}

// completion.mdx:189-190 (error mapping)
// Method not found: -32601 (Capability not supported)
// Invalid prompt name / missing required arguments: -32602
```

**Flow (context threading):** user types into arg #1 → client sends `completion/complete {ref/prompt, argument:{name,value}}` → server returns ranked suggestions (≤100) → user picks; for arg #2 of a multi-arg template, client REPEATS the call adding `context.arguments = { <arg1>: <chosen> }` so the server can return context-dependent suggestions (e.g. framework choices filtered by already-chosen language) — clients SHOULD debounce rapid requests; servers MAY fuzzy-match and rate-limit.

**Result discipline:** values sorted by relevance; `total` may exceed `values.length`; `hasMore: true` signals more options exist even when `total` is unknown — this is NOT cursor pagination (no nextCursor), it's an advisory shape for "keep typing".

**Invariant:** ≤100 values per response is a schema-enforced maxItems; suggestions are advisory (client free to ignore); completion targets are prompt names or resource-template URIs only — never plain resources or tools. A porter who pages completions with cursors, who sends >100 values, or who completes tool names breaks the contract.

**Probe:** no runtime tests in the spec repo; machine-checkable anchors are `CompleteRequest/CompleteResult` in `schema/draft/schema.ts` + `examples/CompleteRequest/*`, `examples/CompleteResult/*` validated by `scripts/validate-examples.ts`. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "CompleteRequest|CompleteResult", limit: 10 });
```

## Verdict
Adopt `completion/complete` behind the `completions: {}` capability with both ref types, `context.arguments` threading for multi-arg templates, and the 100-item cap; adapt your matching/fuzzy logic to host; omit cursor-style paging of completion values (not part of the contract) and completing anything but prompts/template URIs.
