<!-- capsule-v2 -->
# Enhanced read_image — local delegation plus bounded HTTP image loading

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how should a plugin add HTTP(S) image input to an existing local read_image tool without duplicating local filesystem policy or weakening model, byte, and media gates?

## enhancedReadImageTool
**Path/Symbol:** src/read-image-enhancement.ts:69-164 enhancedReadImageTool.
**Signature:** enhancedReadImageTool(ctx: Context, original: ToolDefinition, publicHttpRuntime?: PublicHttpRuntime): ToolDefinition.
**Data Shape:** Input is exactly one non-empty file_path or url. Local input returns the original tool's ReadImageValue; URL input returns path/display plus a saved ImageAttachmentRef with one of the supported media types.

### Decisive source
~~~ts
const filePath = args.file_path?.trim()
const sourceUrl = args.url?.trim()
if ((filePath === undefined || filePath.length === 0) === (sourceUrl === undefined || sourceUrl.length === 0)) {
  throw new Error('read_image requires exactly one non-empty file_path or url')
}
if (filePath !== undefined && filePath.length > 0) {
  return await original.execute({ file_path: filePath }, exec)
}
const url = sourceUrl as string
await assertImageCapable(ctx, exec, `read ${JSON.stringify(url)}`)
const attachments = ctx.attachments
const maxBytes = Math.min(attachments.imageLimits.maxImageBytes, attachments.imageLimits.maxMessageImageBytes)
const loaded = await fetchPublicHttpResource(url, maxBytes, exec.signal, publicHttpRuntime)
const mediaType = imageMediaType(loaded.data)
if (mediaType === undefined) throw new Error('read_image supports PNG, JPEG, WebP, and GIF image bytes')
if (!attachments.imageLimits.mediaTypes.includes(mediaType)) {
  throw new Error(`${mediaType} images are disabled by this deployment`)
}
const ref = await attachments.saveImage({
  data: loaded.data,
  mediaType,
  ...loaded.name === undefined ? {} : { name: loaded.name },
})
~~~

**Flow:** normalize both inputs, reject none/both/empty, delegate local paths unchanged, then for URLs enforce model image capability, call the public HTTP runtime with the shared byte cap and signal, classify/check deployment media policy, save an attachment, and defer context only for child executions.
**Invariant:** local filesystem behavior remains owned by Harness; remote input cannot bypass SSRF/public-fetch controls, byte limits, model capability, or deployment media policy; only validated bytes become an image attachment.
**Probe:** tests/read-image-enhancement.spec.ts:128-150 verifies schema and local delegation; 152-165 verifies HTTP fetch and image result; 167-185 verifies exactly-one input and model image-capability rejection. The direct 22-file/154-test run passed.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.read-image-enhancement\\.enhancedReadImageTool', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt the wrapper pattern: preserve the original local tool and add a bounded remote branch. Adapt public-fetch and attachment APIs plus the supported media policy; retain exact-one-source and capability-before-network ordering. Omit direct URL fetches that bypass the host public-http/SSRF runtime. Coverage is no_recorded_issue + metadata_match for source and direct tests.
