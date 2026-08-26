<!-- capsule-v2 -->
# Tool outputSchema + structuredContent — how does a tool return machine-validatable data without breaking clients that only read text blocks?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** What is the dual-emission contract for typed tool outputs, and what shape trap (array vs string) do the integration tests guard against?

## outputSchema-declared tools return BOTH `structuredContent` AND a backward-compatible text block
**Path/Symbol:** `src/everything/tools/get-structured-content.ts` (whole file, 92L: output schema :16–20; config carrying `outputSchema` :22–36; dual return :82–90). Enforcement twin: filesystem server's real tools — `src/filesystem/index.ts` `directory_tree`, `list_directory_with_sizes`, `move_file` declare `{ content: z.string() }`-style outputSchemas. The everything-server demo returns the SAME object both ways; the filesystem server serializes its payload to a JSON STRING for the text block.

**Signature:** `config = { ..., inputSchema, outputSchema }` — declaring `outputSchema` makes the SDK validate every `structuredContent` against it on BOTH sides of the wire. Handler returns `{ content: [ContentBlock...], structuredContent?: object }`.

**Data Shape:** demo: `content: [{ type: "text", text: JSON.stringify(weather) }]` + `structuredContent: weather`. Filesystem tools: `structuredContent.content` MUST be a string matching the declared schema.

### Decisive source
```ts
// get-structured-content.ts:82-90 — never emit only one arm
const backwardCompatibleContentBlock: ContentBlock = {
  type: "text",
  text: JSON.stringify(weather),
};
return {
  content: [backwardCompatibleContentBlock],
  structuredContent: weather,
};
```
```ts
// src/filesystem/__tests__/structured-content.test.ts:10-17 — the regression this pins
// These tests address issues #3110, #3106, #3093 where tools were returning
// structuredContent: { content: [contentBlock] } (array) instead of
// structuredContent: { content: string } as declared in outputSchema.
```

**Flow:** declare `outputSchema` at registration → handler produces the typed payload → emit text block (JSON-stringified) AND `structuredContent` together → SDK validates the structured arm against the declared schema → strict clients validate again client-side → legacy clients read only `content`.

**Invariants:**
1. **The two arms must AGREE in shape**: `structuredContent` is validated independently against `outputSchema`; schema validation alone cannot catch the two drifting apart (the #4029 test comment states exactly this) — keep them derived from ONE source value.
2. **Never wrap the structured arm in an array** when the schema says scalar/string — the historical bug class (#3110/#3106/#3093).
3. **Invalid `type` values are rejected by the SDK union** — e.g. emitting `type: "blob"` fails CallToolResult parsing client-side before any assertion (#4029); only the five canonical ContentBlock types exist.
4. For binary/media results, mirror bytes EXACTLY into both arms and use `pathToFileURL` semantics for resource URIs (percent-encode spaces/non-ASCII), not raw `file://` concatenation.

**Probe:** `src/filesystem/__tests__/structured-content.test.ts` (281L, whole suite) — spawns the REAL built server over stdio (`StdioClientTransport`) and asserts per-tool that `typeof structuredContent.content === 'string'` and NOT an array (:55–158); the #4029 block (:164–280) round-trips PNG/MP3/bin bytes through base64 equality, asserts `result.structuredContent` DEEP-EQUALS `{ content }`, pins percent-encoding via `/%C3%A9|%CC%81/`, and verifies the advertised `tools/list` outputSchema still serializes both union branches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "structured content weather output schema", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt dual emission with one source-of-truth payload, string-typed structured payloads where the schema declares strings, and byte-exact mirroring for media; adapt schemas to your domain; omit the demo weather data. Extends `thinking-tool.md`'s dual-emission seam with the schema-validation and regression-test discipline.
