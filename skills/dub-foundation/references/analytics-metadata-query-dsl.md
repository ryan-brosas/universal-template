<!-- capsule-v2 -->
# Metadata query DSL — user-typed field:value filters that survive ClickHouse safely

**Source:** dub AGPL-3.0-or-later `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** How can end users filter events by arbitrary metadata keys without opening an injection hole?

## metadataQueryParser: regex grammar + fail-closed sanitization
**Path/Symbol:** `apps/web/lib/analytics/metadata-query-parser.ts:metadataQueryParser` (:16-44) + `parseCondition` (:47-98) + `mapOperator` (:101-120).
**Signature:** `metadataQueryParser(query?: string): InternalFilter[] | undefined` where InternalFilter = `{ operand, operator: equals|notEquals|greaterThan|lessThan|greaterThanOrEqual|lessThanOrEqual, value }`.
**Data Shape:** grammar `field:value`, `field>=value`, `metadata['key']['nested']:value` joined by AND/OR tokens; output feeds get-analytics's `filters` JSON channel (:125-133).

### Decisive source
```ts
const unifiedPattern =
  /^([a-zA-Z_][a-zA-Z0-9_]*|metadata\[['"][^'"]*['"]\](?:\[['"][^'"]*['"]\])*)\s*([:><=!]+)\s*(.+)$/;
...
// Security: Validate metadata key contains only safe characters
if (!/^[a-zA-Z0-9_.]+$/.test(extractedKey)) return null;
...
const sanitizedValue = value
  .trim()
  .replace(/^['"`]|['"`]$/g, "")
  .replace(/[;\\]|--|\*\/|\/\*/g, "");

if (!sanitizedValue) return null;
```
(metadata-query-parser.ts :52-53, :77, :86-91)

**Flow:** split on `/\s+(?:AND|and|OR|or)\s+/` (structure ready for boolean trees; today each condition stands alone) → regex captures field/op/value → `metadata['a']['b']` chains flatten to operand `metadata.a.b` gated by the `[a-zA-Z0-9_.]` charset (anything else ⇒ condition dropped) → strip wrapping quotes, then delete `;` `\` `--` `*/` `/*` tokens from the value → `mapOperator` defaults UNSUPPORTED operator strings to equals.
**Invariant:** the parser NEVER throws — unparseable input yields undefined/null entries that are skipped upstream; sanitization is defense-in-depth BEHIND parameterization (values travel inside the JSON filters arg, never raw SQL text).

**Probe:** executed: `grep -n 'a-zA-Z0-9_.' apps/web/lib/analytics/metadata-query-parser.ts` → :53 (pattern line); `grep -n 'replace(/\\[;' ...` → :89. Direct test `tests/analytics/metadata-query-parser.test.ts` (:1-79, PURE unit, runs without cloud): nested paths :5-44, notEquals :53-58, falsy inputs :60-78 — runner offline-blocked in checkout, anchors line-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", name_pattern: "^metadataQueryParser$", limit: 5, fields: ["signature"] });
```
(observed: metadataQueryParser Function 16-44.)

## Verdict
Adopt the fail-closed charset gate + token-stripping + never-throw posture. Adapt the operator set and operand prefix. Omit the bracket-quote syntax only if you expose a structured filter builder instead.
