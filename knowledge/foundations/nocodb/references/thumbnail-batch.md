<!-- capsule-v2 -->
# Thumbnail job fan-out — how does one thumbnail job handle a batch of attachments and report per-file results without failing the batch?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What does the processor return, and how do scope-scoped paths avoid double-prefixing?

## per-attachment results + path de-scope
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/thumbnail-generator/thumbnail-generator.processor.ts:ThumbnailGeneratorProcessor.job/getFileData` (16-127).
**Signature:** `job(job: Job<ThumbnailGeneratorJobData>): Promise<Array<{path, card_cover?, small?, tiny?}>>`; private `getFileData(attachment, storageAdapter, scope?): {file: Buffer, relativePath}`.
**Data Shape:** input `{attachments: AttachmentResType[], scope?: PublicAttachmentScope}`; output entries keyed by the ORIGINAL `path ?? url` so callers can map thumbnails back to cells.

### Decisive source
```ts
const sharp = Noco.sharp;
if (!sharp) { this.logger.warn('Sharp not available, skipping...'); return results; }  // degrade, don't fail
for (const attachment of attachments) {
  const thumbnail = await this.generateThumbnail(attachment, scope);
  if (!thumbnail) continue;                       // failed file → skipped entry
  results.push({ path: attachment.path ?? attachment.url, ...thumbnail });
}
...
if (attachment.path) {
  // For scoped uploads, `attachment.path` already starts with the scope
  // (after `download/`) — see attachments.service. Don't re-prefix.
  relativePath = path.join('nc', scope ? '' : 'uploads',
    attachment.path.replace(/^download[/\\]/i, ''));
} else if (attachment.url) {
  relativePath = getPathFromUrl(attachment.url).replace(/^\/+/, '');
}
```

**Flow:** each attachment is read from storage, dispatched by mimetype (image/* only today), and resized via the shared generator (see thumbnail-bomb-guard). Results are returned as the JOB RESULT — the caller updates cell metadata after completion. Scoped (public-share) uploads keep their scope prefix; normal uploads normalize under `nc/uploads`.
**Invariant:** missing sharp binary ⇒ empty results + warn, never an exception — thumbnails are enhancement, not correctness. Path derivation has TWO sources (path vs URL) and must strip the `download/` prefix exactly once. Per-attachment failures log + skip so one corrupt image doesn't void the batch.
**Probe:** no unit test upstream. Source-grounded probe: `thumbnail-generator.processor.ts:21-26` — sharp-absent early return; `:100-110` — the two-branch relativePath derivation with the no-re-prefix comment.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "ThumbnailGeneratorProcessor getFileData attachments scope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt result-mapped batch processing keyed to original references with graceful degradation; adapt scope/path conventions and image library; omit the public-scope branch if you have no share-scoped uploads. Coverage caveat: no in-repo tests; source-grounded.
