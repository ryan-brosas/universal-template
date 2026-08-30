<!-- capsule-v2 -->
# Inbound attachment resolution — file_uuid fetch, untrusted filenames, and last-text-block targeting

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you turn cloud-uploaded attachments on inbound messages into local @path references the agent's Read tool can consume — safely?

## Path/Symbol
**Path/Symbol:** `src/bridge/inboundAttachments.ts` — whole file: schema (:31-37), `extractInboundAttachments` (:42-48, safeParse rejects malformed), `sanitizeFileName` (:55-58), `resolveOne` (:68-117), `resolveInboundAttachments` (:123-134), `prependPathRefs` (:142-161), `resolveAndPrepend` (:167-175); sibling image-block repair in `src/bridge/inboundMessages.ts` (`normalizeImageBlocks` :52-73, fast-path scan :55).
**Signature:** `extractInboundAttachments(msg: unknown): InboundAttachment[]`; `resolveAndPrepend(msg, content) → string | ContentBlockParam[]`.
**Data Shape:** `{file_uuid, file_name}`; downloads land at `~/.claude/uploads/{sessionId}/{uuid8}-{safeName}`; refs are QUOTED: `@"<abs path>"` joined by spaces + trailing space.

### Decisive source
```ts
// Strip path components and keep only filename-safe chars. file_name comes
// from the network (web composer), so treat it as untrusted even though the
// composer controls it.
function sanitizeFileName(name: string): string {
  const base = basename(name).replace(/[^a-zA-Z0-9._-]/g, '_')
  return base || 'attachment'
}
...
// Quoted form — extractAtMentionedFiles truncates unquoted @refs at the
// first space, which breaks any home dir with spaces (/Users/John Smith/).
return ok.map(p => `@"${p}"`).join(' ') + ' '
// Targets the LAST text block — processUserInputBase reads inputString
// from processedBlocks[processedBlocks.length - 1], so putting refs in
// block[0] means they're silently ignored for [text, image] content.
const i = content.findLastIndex(b => b.type === 'text')
```

**Flow:** message carries `file_attachments` → zod safeParse (malformed ⇒ empty, never throw) → parallel fetch via OAuth-authed content endpoint (30s timeout, validateStatus true, uuid encodeURIComponent'd into path) → write under session-scoped dir with uuid-prefix collision guard → prepend quoted @refs. Every failure (no token, network, non-2xx, disk, bad custom-oauth URL thrown INSIDE the try so FedStart misconfig degrades to "no @path") skips that attachment only — the prompt still reaches the model. Image twin: clients sending camelCase `mediaType` would poison every subsequent API call ("media_type: Field required"); a fast-path `some()` scan returns the ORIGINAL array reference when nothing needs fixing (zero allocation happy path).

**Invariant:** (1) Network-supplied filenames are path-traversal vectors — basename + charset allowlist before joining. (2) Refs must target the LAST text block, not block[0], or multi-block messages silently drop them. (3) Quoted @refs only — spaces in paths otherwise truncate the reference. (4) Attachment failure degrades to message-without-attachments, never to message loss.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "treat it as untrusted" src/bridge/inboundAttachments.ts` (:52-53); `grep -n "breaks any home dir with spaces" src/bridge/inboundAttachments.ts` (:131); `grep -n "silently ignored for \[text, image\]" src/bridge/inboundAttachments.ts` (:140); graph resolves `locoagent.src.bridge.inboundMessages.normalizeImageBlocks` :52-73 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "resolveInboundAttachments prependPathRefs sanitizeFileName normalizeImageBlocks", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt whole for any bridge/composer attachment pipeline. Adapt storage root and ref syntax to your tooling; keep the untrusted-filename and last-text-block rules verbatim.
