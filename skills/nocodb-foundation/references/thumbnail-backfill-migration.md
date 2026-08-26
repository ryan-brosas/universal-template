<!-- capsule-v2 -->
# Thumbnail backfill migration — how do you generate thumbnails for a legacy storage fleet by reusing the live job as a library call?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the backfill reuse `ThumbnailGeneratorProcessor` directly, and how does it avoid regenerating what already exists?

## Existence-check short-circuit + injected processor call
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_002_thumbnail.ts:job` (:24-346) — sharp-absent skip (:26-33), fallback rescan reusing `_001`'s ledger schema (:39-149), pre-generation existence check (:276-320), direct processor invocation (:204-215).
**Signature:** `await this.thumbnailGeneratorProcessor.job({ data: { context: { base_id: RootScopes.ROOT, workspace_id: RootScopes.ROOT }, attachments: [attachment] } } as any)` — concurrency 1.
**Data Shape:** ledger rows from `nc_temp_file_references`; attachment built per row: local → `{path: 'download/' + file_path minus 'nc/uploads/', mimetype}`, URL → `{url, mimetype}`.

### Decisive source
```ts
// check if thumbnails exist
const isUrl = /^https?:\/\//i.test(fileReference.file_path);
const thumbnailRoot = relativePath.replace(/nc\/uploads/, 'nc/thumbnails');
try {
  const thumbnails = await storageAdapter.getDirectoryList(thumbnailRoot);
  if (['card_cover.jpg', 'small.jpg', 'tiny.jpg'].every((t) => thumbnails.includes(t))) {
    await ncMeta.knexConnection(temp).where('file_path', …).update({ thumbnail_generated: true });
    continue;                                   // skip regeneration entirely
  }
} catch { /* ignore */ }

// manually call thumbnail generator job to control the concurrency
const generated = await this.thumbnailGeneratorProcessor.job({ data: { context: ROOT_CONTEXT, attachments: [attachment] } } as any);
if (generated.length > 0) markDone(); else skipImages.push(id);
```

**Flow:** bail with success (not error) when sharp is unavailable → if `_001` never ran, recreate its scan ledger inline (identical DDL + pause/resume ingest) → page unreferenced→referenced image rows 10 at a time, excluding in-flight and previously-skipped ids → for each, derive the `nc/thumbnails/...` twin directory and short-circuit when all three size files exist → otherwise invoke the LIVE thumbnail processor synchronously at root scope so its guards/batch logic stay in one place → mark done or push to skipImages (which also feeds the WHERE NOT IN of later pages) → onIdle.
**Invariant:** reuse-not-reimplement is deliberate — calling `.job()` directly keeps bomb-guards and sizing in the production path (the migration would silently drift otherwise); the cost is that failures inside the processor are swallowed into empty arrays, hence the explicit `length > 0` check feeding skipImages rather than try/catch alone. Missing thumbnails directory must count as "needs generation", not an error.
**Probe:** no unit test upstream. Source-grounded probe: three-name existence test :300-304; skip-list doubles as query filter :262-265; sharp guard returns `true` :29-33.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "ThumbnailMigration getDirectoryList card_cover small tiny thumbnailGenerated", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the existence-short-circuit + direct-library-call pattern for any media backfill; adapt the sentinel filename list; omit the inline rescan branch if your scan phase always runs first.
