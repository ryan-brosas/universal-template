<!-- capsule-v2 -->
# Imagegen tool boundary — gate first, attach always, publish best effort

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how should a tool compose argument/reference/policy/model gates with attachment persistence and write-intent publication so a generated image remains usable when workspace output is denied?

## imagegenTool
**Path/Symbol:** src/imagegen.ts:268-399 parseArgs and imagegenTool.
**Signature:** imagegenTool(ctx: Context, credentials: OpenAICodexCredentialStore, policy: ImageToolPolicy): ToolDefinition.
**Data Shape:** Input is a trimmed prompt plus at most five workspace refs or one recent-image count and optional output_path. Output is ImagegenValue: prompt, PNG ImageAttachmentRef metadata, and either file {path, operation} or a bounded writeError. Concurrency is safe only when output_path is omitted.

### Decisive source
~~~ts
const args = parseArgs(rawArgs)
policy.assertAllowed(exec, 'imagegen')
await assertImageCapable(ctx, exec, 'generate an image')
const images = args.referenced_image_paths !== undefined
  ? await workspaceImages(ctx, exec, args.referenced_image_paths)
  : args.num_last_images_to_include !== undefined
    ? await conversationImages(ctx, exec, args.num_last_images_to_include)
    : []
const data = await client.generate(args.prompt, images, exec.signal)
const mediaType = imageMediaType(data)
if (mediaType !== 'image/png') throw new Error('OpenAI Codex image response was not a PNG')
const ref = await ctx.attachments.saveImage({ data, mediaType, name: 'generated.png' })
const value: ImagegenValue = {
  prompt: args.prompt,
  image: {
    attachmentId: ref.attachmentId,
    mediaType,
    bytes: ref.bytes,
    width: ref.width,
    height: ref.height,
    ...ref.name === undefined ? {} : { name: ref.name },
  },
}
const outputPath = args.output_path ?? defaultOutputPath()
try {
  const cwd = exec.agent?.session.header.cwd
  const target = await ctx.fs.resolve(outputPath, { ...cwd === undefined ? {} : { cwd }, signal: exec.signal })
  const intent = await ctx.waterfall('fs/write-intent', target, exec, () => undefined)
  const outcome = await writeWorkspaceBytes(ctx, exec, target, data, intent)
  value.file = { path: target.displayPath, operation: outcome.operation }
} catch (error: unknown) {
  throwIfAborted(exec.signal)
  const detail = (error instanceof Error ? error.message : String(error)).slice(0, 1000)
  value.writeError = `generated image was not written to ${JSON.stringify(outputPath)}: ${detail}`
}
~~~

**Flow:** parse exclusive reference modes and bounded counts → enforce cross-provider policy and model image capability → resolve references → generate/validate/save the PNG attachment → attempt write-intent-gated workspace publication → defer rendered context for child executions and return the attachment even when writing fails.
**Invariant:** policy/capability failures happen before provider work; a write denial cannot discard the generated attachment; output paths go through the host waterfall/filesystem; write errors are bounded and cancellation still aborts; child context uses the same rendered image/file metadata.
**Probe:** tests/imagegen.spec.ts:117-163 verifies attachment + output file + presentResult; 204-242 verifies ambiguous refs, text-only capability, and cross-provider policy reject before fetch; 244-254 verifies read-only output retains the image and reports write failure. tests/tool-policy.spec.ts:90-100 also verifies the owning-provider gate. All were executed in the 22-file/154-test passing run.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.imagegen\\.imagegenTool', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt gate-before-side-effect, attachment-before-publication, and best-effort output reporting. Adapt tool schema, capability service, write-intent waterfall, and context-defer APIs; retain the separation between durable attachment success and optional workspace publication. Omit silently dropping the image when a requested path is denied. Coverage is no_recorded_issue + metadata_match for source and direct tests.
