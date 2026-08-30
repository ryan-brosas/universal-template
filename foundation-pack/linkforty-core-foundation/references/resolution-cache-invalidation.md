<!-- capsule-v2 -->
# Resolution cache invalidation on link mutation — old AND new template keys, delete-time too

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** Which cache keys must be invalidated when a link changes — including when its template association changes?

## invalidateLinkResolutionCache + update/delete call pattern
**Path/Symbol:** `src/lib/link-resolution-cache.ts:invalidateLinkResolutionCache` (:9-22); called at `src/routes/links.ts:291-298` (update) and :431-433 (delete).
**Signature:** `async function invalidateLinkResolutionCache(redis: { del(...keys: string[]): Promise<number> } | null | undefined, shortCode: string, templateSlug?: string | null): Promise<void>`.
**Data Shape:** Key grammar set in redirect.ts/sdk.ts: `link:${shortCode}` (legacy) and `link:${templateSlug}:${shortCode}` (templated); redis param accepts null/undefined so callers need no presence check.

### Decisive source
```ts
// links.ts:289-298 (update path)
const oldRow = oldLinkResult.rows[0];
const oldTemplateSlug = await getTemplateSlug(oldRow?.template_id);
const newTemplateSlug = await getTemplateSlug(link.template_id);
await invalidateLinkResolutionCache(fastify.redis, link.short_code, oldTemplateSlug);
if (newTemplateSlug !== oldTemplateSlug) {
  await invalidateLinkResolutionCache(fastify.redis, link.short_code, newTemplateSlug);
}

// link-resolution-cache.ts:19-21
} catch {
  // Swallow — a cache miss on the next read is self-healing.
}
```

**Flow:** update captures pre-update identifiers BEFORE the UPDATE → after it, invalidates legacy key + OLD template key always, NEW template key only when the association changed (re-fetching slug from template id) → delete path returns `short_code, template_id` from the DELETE ... RETURNING and invalidates both its key shapes. This closes the stale-cache window the safety gate cannot: redirect.ts :259-269 records that a cached row carries stale `is_active=true`, and staleness is handled HERE, not by re-checking SQL.
**Invariant:** Invalidate BOTH key namespaces on every mutation path (update/duplicate-code-change/delete); errors are swallowed because a missed del degrades to TTL-bounded staleness while a thrown one breaks the write API; safety gate stays post-cache-read to cover whatever survived.
**Probe:** per-file line counts: `bash -c "grep -cF 'invalidateLinkResolutionCache' src/routes/links.ts"` → 4 (:5 import + :295 update-old + :297 update-new + :433 delete); `bash -c "grep -cF 'invalidateLinkResolutionCache' src/lib/link-resolution-cache.ts"` → 1 (definition); direct tests `src/lib/link-resolution-cache.test.ts`: "deletes both legacy and template keys when templateSlug is provided", "skips template key when templateSlug is empty string", "swallows errors from redis.del without throwing".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "invalidateLinkResolutionCache redis del short_code", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt explicit dual-key invalidation wired into EVERY mutation path plus swallow-don't-throw semantics; adapt key grammar; omit the template dimension entirely if you have no templated links — but then keep exactly one key shape everywhere.
