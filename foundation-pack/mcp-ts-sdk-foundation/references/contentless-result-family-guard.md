<!-- capsule-v2 -->
# Contentless tool-result normalization — which result shapes must NOT be defaulted into `{content: []}` successes, and why is the helper a leaf module?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When normalizing a plain-object tool result for v1 wire parity, which keys veto the default and what cycle does the module placement prevent?

## Family-key guard
**Path/Symbol:** `packages/core-internal/src/wire/resultFamilies.ts`: `TOOL_RESULT_FOREIGN_FAMILY_KEYS` (:7), `normalizeContentlessToolResult` (:13-24).
**Signature:** `normalizeContentlessToolResult(value: unknown): unknown`.
**Data Shape:** foreign-family keys = `['task', 'inputRequests', 'requestState']`; default adds `content: []` by SPREAD (`{...value, content: []}` — input never mutated).

### Decisive source
```ts
// :14-23 the five-way veto
if (
    value === null ||
    typeof value !== 'object' ||
    Array.isArray(value) ||
    (value as { content?: unknown }).content !== undefined ||
    TOOL_RESULT_FOREIGN_FAMILY_KEYS.some(key => key in value)
) {
    return value;
}
return { ...value, content: [] };
```

**Flow:** shared by the 2025 wire-seam schema AND server-side handler normalization (one owner, two consumers). A bare object like `{status:'ok'}` gains `content: []` so v1 clients always see a renderable result. A result carrying `task`/`inputRequests`/`requestState` belongs to a DIFFERENT result family (task lifecycle / multi-round-trip) — defaulting it into a tools/call success would fabricate a completion the driver layer owns.

**Invariant:** presence checks are `!== undefined` / `key in value` — falsy-but-present values (`content: null`, empty-string requestState) must veto; porters who truthiness-test them double-default real data or strip driver payloads. Leaf-module placement is load-bearing: importing from `./codec.js` (which value-imports both rev codecs at top level) closes a runtime cycle and TDZ-crashes whichever era codec evaluates first.

**Probe (direct tests):** pinned via `packages/core-internal/test/wire/*` (codec + neutralKeyParity suites exercise both consumers); source-anchored behavior verified against this file's five-way branch.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "normalizeContentlessToolResult content empty tool result family keys", limit: 2 });
// → wire.resultFamilies.normalizeContentlessToolResult Function 13-24 rank #1
```

## Verdict
Adopt the veto list and spread-default; adapt family keys if your protocol grows new result families; omit nothing.
