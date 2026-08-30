<!-- capsule-v2 -->
# Attachment message rendering — how do typed attachments become API-visible user messages wrapped in system-reminder tags?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the boundary where in-memory attachment objects cross into transcript messages (and thus prompt-cache history).

## createAttachmentMessage / getAttachmentMessages
**Path/Symbol:** `src/utils/attachments.ts:createAttachmentMessage` (:3201-3210), `getAttachmentMessages` generator (:2937-2970).
**Signature:** `createAttachmentMessage(attachment) → { attachment, type: 'attachment', uuid: randomUUID(), timestamp: ISO }`; generator yields one AttachmentMessage per collected attachment.
**Data Shape:** every message gets a fresh UUID + timestamp at CREATION — identity belongs to the message, not the content.

### Decisive source
```ts
export async function* getAttachmentMessages(...): AsyncGenerator<AttachmentMessage, void> {
  const attachments = await getAttachments(input, toolUseContext, ideSelection,
                                            queuedCommands, messages, querySource, options)
  if (attachments.length === 0) return
  logEvent('tengu_attachments', { attachment_types: attachments.map(_ => _.type) })
  for (const attachment of attachments) {
    yield createAttachmentMessage(attachment)
  }
}
```

**Flow:** single collection call → per-attachment message wrap → yielded INTO the caller's tool-result stream (`query.ts:1580-1589`: each yielded message is also pushed onto `toolResults`, so attachments participate in the loop's bookkeeping like any tool result). The renderer (messages layer) wraps non-meta attachment content in `<system-reminder>` framing — that framing plus the memory-budget comments (:271-273 "injects ... via <system-reminder>, bypassing the per-message tool-result budget") is why surfacing budgets must be self-imposed.
**Invariant:** attachments are FIRST-CLASS transcript citizens with their own message type — they occupy prompt-cache history exactly like human turns, so everything upstream (byte-stability, tail-append-only, throttles) exists to protect that history; uuid-per-message enables dedup downstream (session-tail monitor dedups by uuid); empty collections yield nothing rather than an empty message.
**Probe:** no upstream test (coverage caveat). Deterministic probe: consume-site push pattern pinned at `src/query.ts:1585-1588`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createAttachmentMessage getAttachmentMessages yield", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt typed attachment messages with creation-time identity; adapt the envelope shape to your transport; omit telemetry. Porting trap: treating attachments as ephemeral render-side decorations loses their cache-history role — anything you show the model is context you pay for and must therefore budget and stabilize.
