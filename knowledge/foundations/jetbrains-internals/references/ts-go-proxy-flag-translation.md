<!-- capsule-v2 -->
# TS flag translation proxy - how do you talk to tsserver types across engine versions without breaking on enum drift?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** How do you serialize TypeScript's internal bit-flags to a stable consumer when the runtime's own enum values may not match your compile-time table?

## ts-go-proxy FlagsConverter
**Path/Symbol:** `plugins/javascript-plugin/ts-go-proxy/index.js:buildFlagsMapping` (:8-19) + `convertFlags` (:119-126) + `FlagsConverter` (:127-152); canonical tables TYPE/OBJECT/SYMBOL/ELEMENT_FLAG_ENTRIES (:20-116). Bundle header: "src/index.mts" — Node side of a JVM↔Go↔TS type pipeline.
**Signature:** `buildFlagsMapping(entries, runtimeEnum): [from,to][] | null`; `convertFlags(flags, mapping | null)`; converters memoize per-enum mappings (`??=`).
**Data Shape:** each table entry is `[name, canonicalBit]`; the mapping is built against the LIVE runtime enum object (`environment.flagEnums.TypeFlags`), not against the table.

### Decisive source
```js
function buildFlagsMapping(entries, runtimeEnum) {
  let needsMapping = false;
  for (const [name, targetValue] of entries) {
    const sourceValue = runtimeEnum[name];
    if (sourceValue === void 0) continue;              // unknown member: skip silently
    if (sourceValue !== targetValue) needsMapping = true;
    mapping.push([sourceValue, targetValue]);
  }
  return needsMapping ? mapping : null;                // identical values -> null = PASSTHROUGH
}
function convertFlags(flags, mapping) { if (mapping === null) return flags; /* OR-fold */ }
```

**Flow:** first conversion per flag family builds the map by diffing the live enum against the canonical bit table → if every known member agrees, the converter stores null and later calls return flags UNTOUCHED (zero-cost path); any drift produces a from→to table applied by AND/OR folding; members absent from the runtime never block passthrough.
**Invariant:** a translation layer should be ABLE to prove it is unnecessary — the null-mapping fast path is the contract that keeps the common case (matching TS version) allocation-free. Partial enums are safe precisely because unknown names are skipped, not defaulted.
**Probe:** executed against the SHIPPED kernel (extracted via new Function from index.js head): 29-entry table; identical runtime → null passthrough TRUE; String moved to bit 30 → map built, convertFlags(drifted.String|drifted.Number) round-trips to canonical bits TRUE; partial enum {Any:1} → null (skip-and-passthrough), confirming the nuance.
**Coverage caveat:** coverage no_recorded_issue; graph retrieval line-exact (`ts-go-proxy.convertFlags :119-126`, `dispatch :1175-1179`).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "convertFlags buildFlagsMapping ts-go-proxy", limit: 5 });
```

## Verdict
Adopt drift-only lazy translation for ANY wire protocol over third-party internal state (TS flags today, AST kinds tomorrow). Adapt tables to the consumer's stable vocabulary. Omit nothing — the null fast-path IS the pattern.
