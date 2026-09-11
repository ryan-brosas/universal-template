<!-- capsule-v2 -->
# Suffixed filter params & operator wire format — how do multiple same-name filters and typed operators survive a GET query string?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are repeated filters (`browser1`, `os2`), operator prefixes (`eq.a|b`), and indexed property filters (`epf0`, `spf0`) encoded, parsed, and re-serialized?

## suffixed-filter-wire-format
**Path/Symbol:** `src/lib/params.ts:parseFilterValue :23-46, filtersObjectToArray :57-88, filtersArrayToObject :90-103, parseUniversalEventPropertyFilters :146-180`; request-side restore `src/lib/request.ts:36-44`; tests `src/lib/params.test.ts`.
**Signature:** filter value string grammar `^(operator)\.(value)$` with operator ∈ {eq,neq,s,ns,c,dnc,re,nre,t,f,gt,lt,gte,lte,bf,af}; equality splits on commas → arrays.
**Data Shape:** repeated names get numeric suffixes (`browser`, `browser1`, `browser2`); suffix stripped via `key.replace(/\d+$/,'')` for column lookup while the FULL key becomes the unique param name (dedupe in SQL placeholders).

### Decisive source
```ts
const { operator, value } = parseFilterValue(filter);
// 'eq.chrome,firefox' → { operator:'eq', value:['chrome','firefox'] }   (IN clause)
// unknown/missing operator ⇒ equals; bare string ⇒ single-value equals
...
// round-trip: object→array rebuilds unique keys by counting occurrences
const key = count === 0 ? name : `${name}${count}`;
obj[key] = `${operator}.${Array.isArray(value) ? value.join(',') : value}`;
```

**Flow:** GET query → zod strips unknowns → parseRequest RE-ADDS dynamic suffixed keys (`/\d+$/`, `^pf_`, `^epf\d+$`, `^spf\d+$`) that zod dropped (:38-43) → getRequestFilters whitelist-maps base names to columns → compiler uses paramName to keep bind params distinct.
**Invariant:** the suffix is IDENTITY, not semantics — `browser1` means exactly what `browser` means; losing it would merge two OR'd filters into one. Property-filter grammar is positional `dataType.operator.property.value` with dots forbidden in property names unless percent-encoded (`%2E`), enforced by encodePropertyName.
**Probe:** `grep -c "ignores malformed" src/lib/params.test.ts` → 2 (:11-75 round-trip + malformed rejection); structural: `grep -n "replace(/\\\\d+\$/" src/lib/params.ts | head -2` → :66,:95 region.
**Probe:** `grep -c "paramName" src/lib/params.ts` → ≥5 lines.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "parseFilterValue filtersObjectToArray paramName suffix", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt suffix-indexed repeated params + operator-prefixed values for expressive GET APIs without arrays; adapt operator vocabulary; document the dot-encoding rule wherever property names are user-defined.
