<!-- capsule-v2 -->
# SQLite mirror — idempotent Markdown→SQLite reconciliation with exact identity and orphan pruning

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does a searchable SQLite mirror stay exactly aligned with authoritative Markdown memory files — upserting new entries, pruning orphans, and recovering from prior duplicate rows — without ever inventing rows the Markdown does not contain?

## Markdown→SQLite reconciliation
**Path/Symbol:** `src/store/sqlite-memory-store.ts`; `syncMemoryEntry` (341–422), `reconcileMarkdownMemoryScope` (429–484), `reconcileMarkdownFailureScopes` (490–527), `replaceSyncedMemories` (533–607), `removeSyncedMemories` (613–644), `removeExactSyncedMemories` (651–680), `parseMarkdownMemoryEntry` (280–335), `parseMetadataComment` (194–216).
**Signature:** `syncMemoryEntry(dbManager, input: SqliteMemorySyncInput) → { action: 'inserted'|'existing', entry }`; `reconcileMarkdownMemoryScope(dbManager, rawEntries: string[], target, project?) → { inserted, existing, removed }`.
**Data Shape:** `SqliteMemorySyncInput = { content, target, project?, category?, failureReason?, toolState?, correctedTo?, created?, lastReferenced? }`. Identity is exact: `project + target + category + content` (normalized). Failure entries carry `[category] content — Failed: … — Tool state: … — Corrected to: …` text plus a `project64=` metadata comment.

### Decisive source
```ts
// syncMemoryEntry (341-422): exact-identity upsert
const conditions = buildScopeConditions(params, input.target, project, category);
conditions.push('content = ?'); params.push(content);
const existing = db.prepare(`SELECT ... FROM memories WHERE ${conditions.join(' AND ')} ORDER BY id ASC LIMIT 1`).get(...params);
if (!existing) return { action: 'inserted', entry: addMemory(...) };
// merge: min(created), max(last_referenced), category/failure fields coalesce to existing ?? new
const updatedCreated = minDate(existing.created, created);
const updatedLastReferenced = maxDate(existing.last_referenced, lastReferenced);
db.prepare(`UPDATE memories SET category=?, failure_reason=?, tool_state=?, corrected_to=?, created=?, last_referenced=? WHERE id=?`).run(...);

// reconcileMarkdownMemoryScope (429-484): upsert desired + prune orphans, in a transaction
const desiredIdentities = new Set<string>();
for (const rawEntry of rawEntries) {
  const parsed = parseMarkdownMemoryEntry(rawEntry, target, normalizedProject);
  desiredIdentities.add(JSON.stringify([normalizeCategory(parsed.category), parsed.content.trim()]));
  const result = syncMemoryEntry(dbManager, parsed); // inserted++ or existing++
}
// scopedRows = all rows in scope; orphan = identity not desired OR duplicate identity
const orphanIds = scopedRows.filter(r => !desiredIdentities.has(identity(r)) || retained.has(identity(r))).map(r => r.id);
if (orphanIds.length) removed = db.prepare(`DELETE FROM memories WHERE id IN (${placeholders})`).run(...orphanIds).changes;
const transactional = db.transaction?.(reconcile); return transactional ? transactional() : reconcile();

// replaceSyncedMemories (533-607): substring replace with LIKE escaping, updates ALL matches
conditions.push(`content LIKE ? ESCAPE '\\'`); params.push(`%${escapeLikePattern(normalizedOldText)}%`);
// removeSyncedMemories (613-644): substring remove, deletes all matches
// removeExactSyncedMemories (651-680): exact content= match (for FIFO eviction, avoids substring over-removal)
```

**Flow:** (1) `parseMarkdownMemoryEntry` parses each `§`-delimited Markdown entry, reading the metadata comment for created/last/project and the `[category] … — Failed: …` segments for failure fields. (2) `syncMemoryEntry` upserts by exact identity, merging dates (min created, max last_referenced) and coalescing failure fields. (3) `reconcileMarkdownMemoryScope` computes the desired identity set, then deletes any scoped row whose identity is absent or duplicated — making the Markdown scope authoritative. (4) `reconcileMarkdownFailureScopes` groups failure entries by project (from metadata) and reconciles each project scope plus the global scope, also pruning mirrored projects that no longer exist. (5) `replaceSyncedMemories`/`removeSyncedMemories` recover from prior duplicate rows by matching all rows whose content LIKE-contains the normalized old text.

**Invariant:** the SQLite mirror never contains a row whose exact identity is not present in the authoritative Markdown scope; reconcile is idempotent (re-running de-duplicates); substring replace/remove escapes `%` and `_` so they match literally; exact remove is used for eviction so unrelated rows containing the evicted text are untouched.

**Probe:** `tests/store/sqlite-memory-store.test.ts` — `deduplicates exact logical entries` (:65), `reconcileMarkdownMemoryScope` `keeps explicit global MEMORY and USER scope despite embedded project metadata` (:156), `prunes only absent rows in the exact target and project scope` (:182), `removes duplicate and stale-category rows by full Markdown identity` (:209), `escapes % and _ during replace matching` (:258), `escapes % and _ during remove matching` (:274). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "syncMemoryEntry reconcileMarkdownMemoryScope replaceSyncedMemories parseMarkdownMemoryEntry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exact-identity upsert, the scope-authoritative reconcile with orphan pruning, the failure-scope grouping by project metadata, and the LIKE-escaped substring replace/remove with exact-remove for eviction. Adapt the identity tuple, the metadata-comment format, and the failure text format to the host. Omit the Pi `/memory-sync-markdown` command wiring and the extension-root migration unless a target needs them.
