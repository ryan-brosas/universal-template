<!-- capsule-v2 -->
# R2 cache key + TTL — how do you cache paid API responses in object storage so keys are stable, TTL is soft, and stale shapes can't leak through?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** How is the cache key derived and how is expiry enforced on read?

## Sorted-param SHA-256 keys with metadata-based soft TTL
**Path/Symbol:** `src/server/lib/r2-cache.ts:buildCacheKey` (:25-34), `getCached` (:41-53), `setCached` (:58-71).
**Signature:** `async function buildCacheKey(prefix: string, params: Record<string, unknown>): Promise<string>` → `` `${prefix}:${sha256Hex(sortedJson)}` ``; `setCached<T>(key, data, ttlSeconds, metadata?)`.
**Data Shape:** Objects stored under `dataforseo-cache/<key>` as JSON with `contentType: application/json` and `customMetadata.expiresAt` (ISO timestamp); TTLs live per-feature (e.g. brand lookup 24h, keyword research 86400s).

### Decisive source
```ts
const raw = JSON.stringify(
  Object.fromEntries(sortBy(Object.entries(params), ([key]) => key)),
);
return `${prefix}:${await sha256Hex(raw)}`;
// getCached:
const expiresAt = obj.customMetadata?.expiresAt;
if (expiresAt && Date.parse(expiresAt) < Date.now()) return null;
```

**Flow:** caller builds a key from endpoint slug + ALL params that influence the paid call (including scope and casing-normalized values — see brandLookup's key param set) → hit ⇒ zod-validate the parsed value BEFORE trusting it (`brandLookupResultSchema.safeParse(await getCached(key))`; schema drift between writes and reads is otherwise silent) → miss ⇒ run metered fan-out ⇒ write via waitUntil with feature TTL. Changing a key's param set orphans pre-deploy entries — accepted (at most one re-charged lookup per target within TTL) rather than maintaining legacy-shape parsing.
**Invariant:** Params must be sorted before serialization or equivalent inputs get different keys. Expiry is enforced at READ time from customMetadata (soft TTL — objects may outlive it; no background reaper needed). Cached values are untrusted until schema-validated. Never cache partial/failure results (see brand-lookup capsule for the complete-only gate).
**Probe:** `src/server/features/ai-search/services/brandLookup.test.ts` (cache-hit path requires schema-valid payload).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "buildCacheKey getCached setCached expiresAt customMetadata", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sorted-param hashing + read-time expiry + validate-on-read for any KV/object-store response cache. Adapt storage backend and metadata field names. Omit the namespace-prefix listing helper if you never enumerate cached entries.
