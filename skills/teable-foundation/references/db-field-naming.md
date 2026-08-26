<!-- capsule-v2 -->
# DB identifier minting — how does teable turn user-facing table/field names into safe Postgres identifiers without collisions?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** A porter must reproduce how arbitrary Unicode names become collision-free db column/table names while reserving the system columns.

## slugify + letter-prefix repair + suffix-disambiguation over a growing reserved set
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/naming.ts` — `convertNameToValidCharacter` (14–26), `ensureUniqueDbFieldName` (32–43), `joinDbTableName` (28–30), `baseRecordColumnNames` (4–12); direct test `naming.spec.ts` :10–34.
**Signature:** `convertNameToValidCharacter(name: string, maxLength = 40): string`; `ensureUniqueDbFieldName(baseName: string, reservedNames: Set<string>): string`.
**Data Shape:** `baseRecordColumnNames = ['__id','__auto_number','__created_time','__last_modified_time','__created_by','__last_modified_by','__version']`.

### Decisive source
```ts
let cleanedName = slugify(name, { allowedChars: 'a-zA-Z0-9_', separator: '_', lowercase: false });
if (cleanedName === '' || /^_+$/.test(cleanedName)) return 'unnamed';
if (!/^[a-z]/i.test(cleanedName)) cleanedName = `t${cleanedName}`;
return cleanedName.substring(0, maxLength);
// uniqueness: if reserved has base → try `${base}_2`, `_3`, ... until free; caller adds result to set
```

**Flow:** slugify keeps case (`lowercase:false`) and maps disallowed chars to `_` → empty/all-underscore collapses to `'unnamed'` → non-letter-leading names get a `t` prefix (Postgres identifiers can't start with a digit/underscore-only) → truncate to 40 → caller seeds a reserved Set with the seven `__*` system columns plus every already-minted name, then `ensureUniqueDbFieldName` walks `_2`, `_3`, … for the first free candidate.
**Invariant:** minting is ORDER-SENSITIVE: the same two fields named "数据" mint different names depending on insertion order (`数据` vs `数据_2`) because each mint is added to the shared reserved set — porters who dedupe against a snapshot instead of a running set will collide on duplicate names. Truncation happens AFTER prefixing so `t` survives; max 40 applies to the final candidate.
**Probe:** `naming.spec.ts` — 'returns unnamed when the converted name is empty or underscores only' (:11), 'prefixes names that do not start with a letter and truncates long names' (:16), 'finds the next available field name suffix' (:25).
**Coverage:** fully indexed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "convertNameToValidCharacter ensureUniqueDbFieldName baseRecordColumnNames naming", limit: 8 });
```

## Verdict
Adopt the slugify→unnamed/t-prefix/suffix-walk ladder verbatim including the 40-char cap and the seven reserved system columns; adapt the column-name vocabulary to host conventions; omit nothing — every branch handles a real Postgres failure mode.
