<!-- capsule-v2 -->
# Guard-kernel composition — How do I build a typed data model in plain JS without schema validators?

**Source:** Linked Helper v2.130.5 ingest (proprietary — citations-only), pin `?@?`; Codebase Memory `lh-basis` @ 2026-08-23T00:11:49Z. **Question:** what is the minimal primitive set from which every entity guard composes?

## Primitive guards + bottom-up composition
**Path/Symbol:** `core/public-methods/models/helpers/guards/objects.js` (isObject/objectHasStringProperties/objectHasNotEmptyStringProperties/objectHasProperties/objectHasNoProperties/objectHasMethods/isNullish, lines 12–52); `.../guards/strings.js` (isNotEmptyString, isStringInBase64UrlEncoding); `.../guards/dates.js` (isISentAtToPASDates et al., lines 9–28); root entity guard `core/public-methods/models/dbItem/guards.js:isDBId/isIDBItem` (fan-in 19 per graph).
**Signature:** `isObject(d): d is object`; `objectHasStringProperties(d, props[])`; `objectHasNotEmptyStringProperties(d, props[])`; `isIDBItem(d)`; `isISentAtToPASDates(d)`.
**Data Shape:** entities are plain objects; DB identity is a positive number (`isNumber(id) && id > 0` — SQLite rowid); timestamps are `Date` instances; optional `sentAtToPAS` may be `undefined`.

### Decisive source
```js
function isObject(data) { return data !== null && typeof data === 'object'; }   // arrays pass!
function objectHasNotEmptyStringProperties(data, props) {
    if (!objectHasStringProperties(data, props)) return false;
    for (const prop of props) if (data[prop].trim().length === 0) return false;
    return true;
}
// dbItem/guards.js — the root of every entity guard
function isDBId(id) { return isNumber(id) && id > 0; }
function isIDBItem(data) { return isObject(data) && isDBId(data.id); }
// dates/guards.js
function isISentAtToPASDate(data) { return isObject(data) && (data.sentAtToPAS === undefined || data.sentAtToPAS instanceof Date); }
function isISentAtToPASDates(data) { return isICreatedAtDate(data) && isIUpdatedAtDate(data) && isISentAtToPASDate(data) && isIActualAtDate(data); }
// composition example — people/PersonExternalIdentifier/guards.js:9-13
function isIPersonExternalIdentifier(arg) {
    return isIDBItem(arg) && IPersonExternalIdentifier.ExternalIdWithType.isValidExternalIdentifierData(arg) && isISentAtToPASDates(arg);
}
```

**Flow:** primitives (typeof/null checks) -> property-shape guards -> domain-value guards (dates, numbers, base64url) -> entity-data validators -> composite entity guard = dbItem ∧ payload-validity ∧ timestamp-shape. The graph shows this as fan-in: `isIDBItem` 19 callers, `isObject` 4+ hotspots.
**Invariant:** composition is pure conjunction — no guard mutates or defaults; every layer is independently callable and falsifies rather than coerces.
**Probe:** `node -e "const g=require('<root>/core/public-methods/models/dbItem/guards.js'); console.log(g.isIDBItem({id:3}), g.isIDBItem({id:0}), g.isIDBItem({}))" → expect true false false`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "guard objects properties", format: "json", file_pattern: "core/public-methods/models/helpers/.*" });
```

## Verdict
Adopt the ~10-primitive kernel plus strict-conjunction composition for runtime boundaries where pulling a schema library is too heavy. Adapt: add Array.isArray exclusions where arrays must fail (`isObject` accepts them!). Caveat learned from source: `instanceof Date` rejects ISO strings — these guards validate in-process objects only, not JSON-revived wire payloads; porters must convert wire data first. Keep citations-only (proprietary).
