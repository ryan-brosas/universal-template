<!-- capsule-v2 -->
# Tool timeout resolution — which timeout value reaches a tool's abort signal, and what does the number form mean?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** Given one `TimeoutConfiguration` shared by request, step, chunk, and tool timers, how does a specific tool resolve its own milliseconds?

## getToolTimeoutMs
**Path/Symbol:** `packages/ai/src/prompt/request-options.ts:13-22` (`TimeoutConfiguration`), `:89-98` (`getToolTimeoutMs`).
**Signature:** `getToolTimeoutMs(timeout: TimeoutConfiguration<TOOLS> | undefined, toolName: keyof TOOLS & string): number | undefined`.
**Data Shape:** Config is `number | {totalMs?, stepMs?, firstChunkMs?, chunkMs?, toolMs?, tools?: Partial<Record<`${toolName}Ms`, number>>}` (defined at `request-options.ts:13-22`). Output: milliseconds for THIS tool or `undefined`. Sole consumer: `executeToolCall` — the model-call timeout extractors (`getTotalTimeoutMs`/`getStepTimeoutMs`/`getFirstChunkTimeoutMs`/`getChunkTimeoutMs`) are siblings on the same type, not tool consumers.

### Decisive source
```ts
export function getToolTimeoutMs<TOOLS extends ToolSet>(
  timeout: TimeoutConfiguration<TOOLS> | undefined,
  toolName: keyof TOOLS & string,
): number | undefined {
  if (timeout == null || typeof timeout === 'number') {
    return undefined;                    // number form = REQUEST-level only; never reaches tools
  }
  return timeout.tools?.[`${toolName}Ms`] ?? timeout.toolMs;
}
```

**Flow:** sibling extractors on the same config: `getTotalTimeoutMs` (accepts the bare-number form as total), `getStepTimeoutMs` / `getFirstChunkTimeoutMs` / `getChunkTimeoutMs` (object-form only). For tools: per-tool key lookup FIRST (`tools['testToolMs']`), fallback to blanket `toolMs`.

**Invariant:** The shorthand `timeout: 30000` deliberately does NOT bound tool executions (test-pinned); per-tool overrides beat the generic default; `undefined` propagates so `executeToolCall` creates no timer at all. A porter who applies the number to tools changes user-visible semantics.

**Probe:** `packages/ai/src/generate-text/execute-tool-call.test.ts:1031` ("should use per-tool timeout over generic toolMs" — `timeout: { toolMs: 10000, tools: { testToolMs: 2000 } }`) and `:1056` ("should fall back to toolMs when tool not in tools").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "getToolTimeoutMs TimeoutConfiguration", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-level resolution ladder and the number-form exclusion. Adapt the template-literal key convention (`${toolName}Ms`) if your host uses structured overrides.
