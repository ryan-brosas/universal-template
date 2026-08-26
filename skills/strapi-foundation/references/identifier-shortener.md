<!-- capsule-v2 -->
# Identifier shortener — how do you generate deterministic DB table/column names that always fit dialect identifier limits?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** When `collectionName_attribute_links` exceeds e.g. Postgres's 63-char limit, how are names shortened *stably across processes* without collisions?

## Identifier naming seam
**Path/Symbol:** `packages/core/database/src/utils/identifiers/index.ts:Identifiers.getNameFromTokens` (273–422) and `Identifiers.getShortenedName` (239–263); hash primitive in `src/utils/identifiers/hash.ts:createHash` (34–41).
**Signature:** `getNameFromTokens(nameTokens: NameToken[]): string`; `getShortenedName(name: string, len: number): string`; `createHash(data: string, len: number): string`.
**Data Shape:** `NameToken = { name, compressible, shortName?, allocatedLength? }` — suffix/prefix tokens (e.g. `"links"`) are incompressible and may map to short names; content tokens are compressible. `maxLength = 0` means "legacy v4 unlimited name".

### Decisive source
```ts
const available = maxLength - totalIncompressibleLength - totalSeparatorsLength;
const availablePerToken = Math.floor(available / compressible.length);
...
// Redistribute surplus length to longer strings, one character at a time
while (surplus > 0 && deficits.length > 0) {
  deficits = deficits.filter((token) => filterAndIncreaseLength(token));
  if (surplus === previousSurplus) break; // infinite loop protection
  previousSurplus = surplus;
}
```
```ts
return `${name.substring(0, availableLength)}${this.HASH_SEPARATOR}${createHash(name, this.HASH_LENGTH)}`;
```
```ts
// hash.ts — shake256 gives an arbitrary-length hex stream, so any HASH_LENGTH works
const hash = crypto.createHash('shake256', { outputLength: Math.ceil(len / 2) }).update(data);
return hash.digest('hex').substring(0, len);
```

**Flow:** join tokens with separator → if full name fits, use it → else partition compressible/incompressible → budget `availablePerToken`, give unused budget of short tokens back to over-long ones char-by-char → tokens still too long become `head + separator + shake256(fullToken)[:HASH_LENGTH]` → final length re-check throws if the allocator mis-bounded.
**Invariant:** Shortening is a pure function of `(tokens, maxLength)` — same inputs always produce the same DB identifier, which is what makes schema diffing idempotent; `getShortenedName` refuses lengths below `MIN_TOKEN_LENGTH + HASH_LENGTH`; unshortened→shortened mapping is recorded (`setUnshortenedName`) so the schema layer can translate both ways.
**Probe:** `packages/core/database/src/metadata/__tests__/identifiers.test.ts` — runs `createMetadata` twice: `maxLength: 0` must match `expectedMetadataResults` verbatim; `maxLength: 25` must match precomputed `expectedMetadataHashedResults` (pins determinism of hashed names).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "tokens compress truncate maxLength", file_pattern: "packages/core/database/src/utils/identifiers/*", limit: 15 });
```
Executed during pass 1: returned exactly `getNameFromTokens` (273–422). Companion call `query: "shortened name hash prefix suffix separator"` returned `getShortenedName` (239–263) and `hash.createHash`.

## Verdict
Adopt even-budget-with-surplus-redistribution token compression plus shake256 suffixing for overflow tokens — it solves DB-name-limit portability deterministically without a lookup table. Adapt `maxLength` per dialect and your separator/short-name maps. Omit Strapi's v4 legacy `maxLength=0` mode unless you must coexist with old schemas. Coverage: `no_recorded_issue` + `metadata_match` on both cited files.
