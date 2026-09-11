<!-- capsule-v2 -->
# Archive as a boolean flag — why is soft-delete just `archived` and where is it enforced?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** How does dub implement archive/unarchive and how does listing respect it?

## archiveLink + list-side enforcement
**Path/Symbol:** `apps/web/lib/api/links/archive-link.ts:archiveLink` (1-18); enforcement in `get-links-for-workspace.ts:136` (`archived: showArchived ? undefined : false`).
**Signature:** `archiveLink({ linkId: string, archived: boolean }): Promise<Link>` — a bare prisma update.
**Data Shape:** single nullable-ish boolean column `archived` (default false); no timestamped tombstone table.

### Decisive source
```ts
export async function archiveLink({ linkId, archived }) {
  return await prisma.link.update({ where: { id: linkId }, data: { archived } });
}
// PATCH route drives it through the body flag (update-link.test.ts):
test("archive link", ...)    // PATCH { archived: true }  -> archived === true
test("unarchive link", ...)  // PATCH { archived: false } -> archived === false

// EVERY list/count query defaults to hiding archived rows:
archived: showArchived ? undefined : false,
```

**Flow:** archiving is an ordinary authenticated PATCH whose only semantic payload is the boolean; unarchive is the same call with false. The redirect edge needs NO archived check because lists hide them and the cache tier refreshes from those lists; hard deletion remains deleteLink's job.
**Invariant:** Soft-delete state lives ON THE ROW (not a side table) and is enforced at READ composition — exactly one expression (`showArchived ? undefined : false`) decides visibility across every consumer, so forgetting it is impossible where the shared builder runs. Archived ≠ deleted: analytics rows, click attribution, and the Redis cache entry survive; only default listings filter the flag. The deliberate minimalism (18-line helper, no events) marks archive as UI-state, not lifecycle — webhooks fire only for the surrounding link.updated mutation, not for the flag itself.
**Probe:** direct integration tests `tests/links/update-link.test.ts:87 "archive link"` and `:119 "unarchive link"`. Deterministic probe: create two links, archive one ⇒ GET /links returns one; GET /links?showArchived=true returns both.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getLinksForWorkspace validateLinksQueryFilters folderIds", limit: 5 }); // list-side twin
// archive-link.ts cited directly (check_index_coverage: no_recorded_issue)
```

## Verdict
Adopt on-row boolean soft-delete with a single read-side switch when you need reversible hiding without analytics loss; reach for tombstones (hard-delete-choreography) only when history must be queryable per-row. Adapt the flag name/default visibility. Omit if your product treats removal as irreversible.
