<!-- capsule-v2 -->
# MCP attachment path allowlisting — how does an LLM-facing file reader avoid becoming an arbitrary-file exfiltration channel?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** The model supplies attachment URLs/paths as tool arguments — what stops it reading any storage path in the base?

## FILE_REFERENCES membership gate before stream read
**Path/Symbol:** `packages/nocodb/src/mcp/mcp.service.ts:readAttachment` handler (:332–522); helpers: `resolveAttachmentFilePath` (helpers/attachmentHelpers), `serialize` (helpers/serialize).
**Signature:** input `files: Array<{title?, mimeType?, size?} & ({url,signedUrl} | {path,signedPath})>`; per-file result `{title, mimeType?, size?, content?, images?, error?}` — never throws outward.
**Data Shape:** candidates = [path, url, path minus leading download/] filtered truthy; gate table MetaTable.FILE_REFERENCES keyed base_id + deleted:false + file_url IN candidates.

### Decisive source
```ts
// Only allow paths recorded as an attachment in the
// caller's current base.
const fileUrlCandidates = [
  file.path,
  file.url,
  file.path ? file.path.replace(/^download[/\\]/i, '') : null,
].filter(Boolean) as string[];

const fileRef = await Noco.ncMeta
  .knex(MetaTable.FILE_REFERENCES)
  .where({ base_id: context.base_id, deleted: false })
  .whereIn('file_url', fileUrlCandidates)
  .first();

if (!fileRef) {
  return {
    title: file.title || 'Unknown file',
    error: 'Attachment is not accessible from this MCP context',
  };
}
```
(:420–:439)

**Flow:** for each requested file → resolve relative path from url/path fields → ALLOWLIST CHECK: the exact URL or path must exist in FILE_REFERENCES for THIS base and not be deleted → only then read via storage adapter stream → serialize to text/images with '@file_not_supported' treated as no-content → per-file failures become `{error}` entries; the final response groups successes ('## Successfully Processed Files') and failures ('## Files With Processing Issues') into one markdown text block.
**Invariant:** trust boundary is the RECORDED ATTACHMENT TABLE, not the caller-supplied string — anything not previously uploaded through normal flows has no reference row and is refused even if the path exists. The zod schema enforces url-XOR-path shape at the tool boundary. Errors are data, never rejections, so one bad file cannot abort the batch.
**Probe:** `cd packages/nocodb && grep -c "FILE_REFERENCES" src/mcp/mcp.service.ts` (=1) and `grep -c "isError: true" src/mcp/mcp.service.ts` (=13 across all tools' catches).
**Direct test:** none upstream for mcp/ — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "readAttachment FILE_REFERENCES resolveAttachmentFilePath serialize", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reference-table allowlisting + per-item error-as-data + grouped markdown response for LLM file access; adapt the reference schema to your upload pipeline; omit if your MCP surface never touches files. Coverage caveat: grep-pinned only.
