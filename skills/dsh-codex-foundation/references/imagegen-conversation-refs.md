<!-- capsule-v2 -->
# Conversation image references — recursive attachment selection with exact cardinality

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how should image generation reuse recent conversation images while preserving chronological order, refusing short histories, and never accepting model-supplied bytes?

## collectImageRefs, recentImageRefs, and conversationImages
**Path/Symbol:** src/imagegen.ts:222-246 collectImageRefs/recentImageRefs/conversationImages.
**Signature:** conversationImages(ctx: Context, exec: ToolExecution, count: number): Promise<string[]>; recentImageRefs(messages: readonly Message[], count: number): ImageAttachmentRef[].
**Data Shape:** Message content may contain image blocks directly or nested tool-result content. The latest count refs are selected from the flattened chronological traversal, loaded through ctx.attachments.readImage, and converted to data URLs; no agent session means the source is unavailable.

### Decisive source
~~~ts
function collectImageRefs(content: readonly ContentBlock[], output: ImageAttachmentRef[]): void {
  for (const block of content) {
    if (block.type === 'image') output.push(block.attachment)
    else if (block.type === 'tool-result') collectImageRefs(block.content, output)
  }
}
function recentImageRefs(messages: readonly Message[], count: number): ImageAttachmentRef[] {
  const refs: ImageAttachmentRef[] = []
  for (const message of messages) collectImageRefs(message.content, refs)
  return refs.slice(-count)
}
const session = exec.agent?.session
if (session === undefined) throw new Error('conversation image references are unavailable outside an agent session')
const refs = recentImageRefs(session.deriveMessages(), count)
if (refs.length !== count) {
  throw new Error(`requested the last ${count} conversation images, but only ${refs.length} were available`)
}
return Promise.all(refs.map(async ref => {
  const stored = await ctx.attachments.readImage(ref, exec.signal)
  return `data:${stored.ref.mediaType};base64,${Buffer.from(stored.data).toString('base64')}`
}))
~~~

**Flow:** require an active session, recursively flatten image-bearing message content, retain the suffix of the ordered ref list, fail before attachment reads when cardinality is short, then load and encode refs concurrently under the execution signal.
**Invariant:** count is exact, newest refs win without reversing order, nested tool-result images are not lost, and the provider receives attachment-store bytes rather than message-embedded or model-supplied raw data.
**Probe:** tests/imagegen.spec.ts:183-202 saves one prior attachment, derives it from a user message, requests num_last_images_to_include: 1, and asserts the request data URL; the direct suite passed. Nested tool-result recursion and short-history failure are source-confirmed caveats.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.imagegen\\.conversationImages', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt recursive ref collection plus suffix selection and exact-cardinality checks. Adapt the conversation/message and attachment interfaces; preserve store-mediated reads and execution cancellation. Omit silently truncating a short history or accepting caller-provided binary content. Coverage is no_recorded_issue + metadata_match for the source/test path; one direct attachment case passed, with recursion and short-history branches source-confirmed.
