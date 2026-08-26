<!-- capsule-v2 -->
# Workspace image references — bounded filesystem-to-data-URL conversion

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how should an image tool turn workspace paths into ordered provider inputs without trusting extensions, exceeding image limits, or bypassing filesystem observation?

## workspaceImages
**Path/Symbol:** src/imagegen.ts:248-266 workspaceImages.
**Signature:** workspaceImages(ctx: Context, exec: ToolExecution, paths: readonly string[]): Promise<string[]>.
**Data Shape:** Each input path is resolved relative to the active session cwd. Output is an array of data URLs in input order. The byte budget is the minimum of maxImageBytes and maxMessageImageBytes; filesystem metadata and attachment validation remain host-owned.

### Decisive source
~~~ts
const cwd = exec.agent?.session.header.cwd
const maxBytes = Math.min(ctx.attachments.imageLimits.maxImageBytes, ctx.attachments.imageLimits.maxMessageImageBytes)
const images: string[] = []
for (const path of paths) {
  if (path.trim().length === 0) throw new Error('referenced_image_paths must not contain an empty path')
  const target = await ctx.fs.resolve(path, { ...cwd === undefined ? {} : { cwd }, signal: exec.signal })
  const info = await ctx.fs.stat(target, exec.signal)
  if (info === undefined) throw new Error(`referenced image does not exist: ${path}`)
  if (info.type !== 'file') throw new Error(`referenced image is not a regular file: ${path}`)
  const data = await ctx.fs.readBytes(target, exec.signal, maxBytes)
  const mediaType = imageMediaType(data)
  if (mediaType === undefined) throw new Error(`referenced image is not PNG, JPEG, WebP, or GIF: ${path}`)
  await ctx.attachments.validateImage({ data, mediaType, name: basename(target.displayPath) })
  ctx.emit('fs/observed', target, { kind: 'present', version: info.version }, exec)
  images.push(`data:${mediaType};base64,${Buffer.from(data).toString('base64')}`)
}
~~~

**Flow:** reject empty names, resolve/stat/read through the active filesystem with the execution signal, classify bytes, validate against attachment limits, emit a present observation, and encode only validated bytes while preserving path-array order.
**Invariant:** a directory, missing path, unsupported signature, oversized read, or cancellation never becomes a provider input; the provider sees data URLs, not raw workspace paths, and the host retains path/attachment policy ownership.
**Probe:** tests/imagegen.spec.ts:165-180 writes reference.png, invokes imagegen, and asserts the edit body contains the exact PNG data URL; the direct image/read-image/policy command passed all 154 tests.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.imagegen\\.workspaceImages', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt the resolve → stat → bounded read → magic-byte classify → attachment validate → observe → encode ladder. Adapt filesystem/attachment APIs and byte limits; retain active-cwd resolution and ordered inputs. Omit any extension-only MIME inference or direct path forwarding. Coverage is no_recorded_issue + metadata_match; the direct test exercises a valid PNG path, while missing/non-file/unsupported branches are source-confirmed.
