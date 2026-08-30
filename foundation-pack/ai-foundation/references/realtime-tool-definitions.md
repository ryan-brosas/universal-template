<!-- capsule-v2 -->
# Realtime tool definitions — how are SDK tools serialized for a realtime session config?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** Which tool types cross the realtime boundary, and how do dynamic descriptions resolve?

## Function/dynamic-only export with exhaustive guard
**Path/Symbol:** `packages/ai/src/realtime/get-realtime-tool-definitions.ts` — `getRealtimeToolDefinitions` (:9–48), `resolveRealtimeToolDescription` (:50–66).
**Signature:** `getRealtimeToolDefinitions({tools, toolsContext?}): Promise<RealtimeToolDefinition[]>`.
**Data Shape:** output `{type:'function', name, description?, parameters: jsonSchema}` — provider-defined tools are silently EXCLUDED, unknown types THROW.

### Decisive source
```ts
switch (toolType) {
  case undefined:
  case 'function':
  case 'dynamic': {
    const description = resolveRealtimeToolDescription({tool, toolName, toolsContext});
    definitions.push({
      type: 'function', name, description,
      parameters: await asSchema(tool.inputSchema).jsonSchema,
    });
    break;
  }
  case 'provider': break;                 // excluded: server-side execution
  default: {
    const exhaustiveCheck: never = toolType as never;
    throw new Error(`Unsupported tool type: ${exhaustiveCheck}`);
  }
}
...
return tool.description === undefined ? undefined
  : typeof tool.description === 'string'
    ? tool.description
    : tool.description({ context: toolsContext[toolName] }); // dynamic desc
```

**Flow:** iterate the ToolSet → function/dynamic/legacy-undefined tools have their inputSchema lifted through `asSchema(...).jsonSchema` (Zod included) and their description resolved — plain strings pass through; FUNCTION descriptions receive the per-tool entry from `toolsContext`, enabling state-dependent tool descriptions in agentic UIs → `provider` tools are skipped because they execute on the provider's side and make no sense in a browser voice session → any FUTURE tool type trips the `never` exhaustiveness check rather than passing silently.
**Invariant:** The boundary is fail-loud on unknown types but silent on provider tools — the asymmetry is intentional: exclusion is a known semantic, novelty is a bug. Description-as-function resolution is what keeps realtime tool prompts context-aware without re-registering tools.
**Probe:** deterministic: `grep -n "exhaustiveCheck" packages/ai/src/realtime/get-realtime-tool-definitions.ts` returns :44–45 hits (`grep -n exhaustiveCheck packages/ai/src/realtime/get-realtime-tool-definitions.ts` → two lines); `grep -n "await asSchema(tool.inputSchema).jsonSchema" packages/ai/src/realtime/get-realtime-tool-definitions.ts` → single hit inside the push block. Direct tests: covered indirectly via session setup suites; standalone suite absent (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "getRealtimeToolDefinitions provider exhaustiveCheck", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 getRealtimeToolDefinitions :9-48
```

## Verdict
Adopt the type filter with exhaustiveness throw and context-resolved descriptions; adapt the wire shape to your realtime API's function schema; omit nothing — forwarding provider tools leaks server-execution contracts to clients.
