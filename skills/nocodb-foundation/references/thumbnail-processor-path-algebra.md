<!-- capsule-v2 -->
|# Thumbnail processor — sharp-gated batch loop with dual-shape path algebra

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** Between queue payload and sharp, how does the processor turn an attachment reference into (bytes, canonical path) — the part of thumbnailing that actually breaks when ported?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/thumbnail-generator/thumbnail-generator.processor.ts:job` (16–44), `generateThumbnail` (46–91), `getFileData` (93–127); producer gate `services/attachments.service.ts:211-225` (`supportsThumbnails` filter + ROOT-scope context).

**Signature:** `job(job: Job<{attachments, scope?}>): Promise<{path, card_cover?, small?, tiny?}[]>` — SEQUENTIAL loop, one result entry per attachment keyed by `attachment.path ?? attachment.url`.

**Data Shape:** attachment refs carry `path | url` + `mimetype` + `title`. `Noco.sharp` absence ⇒ warn + return [] at the job level and null per item. Only `image/*` mimes reach the generator; everything else is a logged skip.

### Decisive source
```ts
if (!sharp) { this.logger.warn('Sharp not available...'); return results; }   // []
// getFileData — the path algebra:
if (attachment.path) {
  // For scoped uploads, `attachment.path` already starts with the scope
  // (after `download/`) — see attachments.service. Don't re-prefix.
  relativePath = path.join('nc', scope ? '' : 'uploads',
    attachment.path.replace(/^download[/\\]/i, ''));
} else if (attachment.url) {
  relativePath = getPathFromUrl(attachment.url).replace(/^\/+/, '');
}
const file = await storageAdapter.fileRead(relativePath);
relativePath = relativePath.replace(new RegExp(`^.*?nc[/\\\\]${scopePath}[/\\\\]`), '');
if (scope) relativePath = `${scopePath}/${relativePath}`;   // read key ≠ write key
```

**Flow:** refs → sharp gate → per item: adapter read → mime gate → ImageThumbnailGenerator produces the card_cover/small/tiny trio → collect keyed results; per-item errors log-and-null, job still succeeds.

**Invariant:** (1) TWO input shapes need TWO derivations: `path` refs get `download/` stripped and NO uploads re-prefix when scoped; `url` refs go through URL→path extraction — mixing them double-prefixes or escapes the bucket. (2) After reading, relativePath is normalized by cutting through `nc/<scope>/` then re-prefixed for scoped writes: read path and write key are deliberately separate derivations. (3) Producer-side `supportsThumbnails` filter + empty-list suppression means non-image batches never enqueue; the processor mime switch is defense-in-depth. (4) Enqueue context is ROOT scope (base-agnostic infra work). (5) Sequential processing keeps decoded-image memory bounded.

**Probe:** no unit test upstream. Source-grounded probe: whole file cited above (128 L), especially :101-102 scope comment verbatim, :116-124 normalization regex; attachments.service.ts:211-225 (filter+ROOT); pairing capsules thumbnail-bomb-guard.md / thumbnail-batch.md / thumbnail-producer-gating.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "ThumbnailGeneratorProcessor getFileData getPathFromUrl supportsThumbnails", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt dual-shape path derivation, read/write key separation, warn-skip isolation, and ROOT-context infra enqueues; adapt size names/scope tokens; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
