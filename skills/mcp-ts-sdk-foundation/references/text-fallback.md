<!-- capsule-v2 -->
# TextContent auto-append — how does a schema-less tool's non-object structuredContent stay renderable and wire-legal?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When a handler returns `structuredContent: [1,2,3]` (or a primitive) with no content blocks, what must the codec add — and when must it wrap instead?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/wire/textFallback.ts`: `appendTextFallbackForNonObject` (:20-31); call sites: BOTH era codecs' `projectCallToolResult` (`wire/codec.ts` docblock :225-243).
**Signature:** `appendTextFallbackForNonObject(result: CallToolResult): CallToolResult` — era-agnostic (SEP-2106 §4.3, EVERY era, value-shape-based); returns same reference when nothing to do.
**Data Shape:** Trigger: `structuredContent` is a non-object value (array/primitive/null) AND the handler authored no `type:'text'` block. Action: append `{type:'text', text: JSON.stringify(value)}`. Opt-out BY AUTHORSHIP: returning any text block yourself.

### Decisive source
```ts
const sc = result.structuredContent;
if (sc === undefined) return result;
const isNonObjectValue = typeof sc !== 'object' || sc === null || Array.isArray(sc);
if (!isNonObjectValue) return result;
if (hasTextContent) return result;
return { ...result, content: [...(result.content ?? []), { type: 'text' as const, text: JSON.stringify(sc) }] };
```
Paired 2025-only decision in `projectCallToolResult`: wrap as `{result:<value>}` when value is non-object OR the ADVERTISED outputSchema has a non-object root — the 2025 wire shape requires structuredContent to be an object; a schema-less tool returning `[1,2,3]` would otherwise ship wire-illegal bytes. Identity on 2026.

**Flow:** handler returns → per-registration projection → text fallback (both eras) + `{result:…}` wrap check (2025 only) → wire. Consumers that read only `content` still receive a rendering of every structured result.

**Invariant:** The leaf module imports NOTHING from `./codec.js` (which value-imports both rev codecs top-level) — importing upward would make a runtime cycle and a TDZ hazard for entries evaluating a rev codec module first. Two independent decisions (auto-append vs wrap) live in the codec so server code never re-derives them.

**Probe:** `packages/core-internal/test/wire/codec.test.ts` (projection matrix incl. auto-append and 2025-wrap rows).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "appendTextFallbackForNonObject projectCallToolResult", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt the two-decision projection for structured tool results across wire-shape revisions; adapt wrap rules to your legacy shape; respect the leaf-module import direction if you mirror the codec layout.
