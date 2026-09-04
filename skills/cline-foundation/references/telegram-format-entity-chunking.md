<!-- capsule-v2 -->
# Telegram entity formatting — how do I send rich markdown to a chat API that 400s on malformed markup, and split long replies without losing formatting?

**Source:** cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How do I convert markdown to platform entities, chunk at the message limit while re-basing entity offsets, and fall back to raw text mid-send without resending delivered chunks?

## Markdown→entities, no parse_mode, overlap-rebased chunking
**Path/Symbol:** `apps/cli/src/connectors/adapters/telegram-format.ts:buildTelegramFormattedPayloads` (:180-192) + `chunkFormattedMessage` (:86-132).
**Signature:** `buildTelegramFormattedPayloads(threadId: string, text: string): TelegramSendMessagePayload[]`; `chunkFormattedMessage(text: string, entities: TelegramMessageEntity[]): Array<{text, entities}>`.
**Data Shape:** TelegramMessageEntity = `{type, offset, length, url?, language?, custom_emoji_id?}`; TELEGRAM_MESSAGE_LIMIT = 4096; payload always carries `link_preview_options:{is_disabled:true}` and NEVER `parse_mode`.

### Decisive source
```ts
const chunkEntities = entities
	.map((entity) => {
		const entityStart = entity.offset;
		const entityEnd = entity.offset + entity.length;
		const overlapStart = Math.max(entityStart, startOffset);
		const overlapEnd = Math.min(entityEnd, endOffset);
		if (overlapStart >= overlapEnd) {
			return undefined;
		}
		return {
			...entity,
			offset: overlapStart - startOffset,
			length: overlapEnd - overlapStart,
		};
	})
	.filter((entity): entity is TelegramMessageEntity =>
		Boolean(entity && validEntityForText(entity, chunkText.length)),
	);
```

**Flow:** markdownToFormattable (from @gramio/format/markdown) over normalizeTelegramText(text) (empty ⇒ " " — Telegram rejects empty sends) → plain text + entity array → chunkFormattedMessage slices at 4096 and re-bases overlapping entities per chunk (offset = overlapStart − startOffset, length = overlapEnd − overlapStart; non-overlapping dropped; validEntityForText re-validates finite offset/length, offset≥0, length>0, offset+length≤chunkLen) → one sendMessage POST per chunk. postTelegramFormattedReply tracks sentPayloadCount across the sequential loop; on ANY failure it logs warn and falls back to RAW thread.post chunks of ONLY the unsent remainder — payloads.slice(sentPayloadCount).map(text).join("") when some chunks landed, else the ORIGINAL input text — via chunkTelegramRawText (4096 slices, empty ⇒ [" "]). API failure detail = parsed.description || body.slice(0,240); a JSON SyntaxError rethrows as a described failure.
**Invariant:** No parse_mode ever — malformed markdown degrades to raw text instead of a Telegram 400; chunk texts joined equal the original text (nothing dropped); entity offsets are always valid within their own chunk; the fallback resends only undelivered content.
**Probe:** `apps/cli/src/connectors/adapters/telegram-format.test.ts` (10 cases: no-parse_mode pin; malformed-markdown degradation; bold entity split byte-pinned as bold[0,4096]+bold[0,10]; partial-send fallback resends only the tail; raw-fallback chunking).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "chunkFormattedMessage telegram entity offset overlap message limit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the entities-not-parse_mode strategy, the overlap-rebase chunking arithmetic, and the sent-count-tracked raw fallback. Adapt the markdown converter (@gramio/format) and the entity vocabulary to the host platform. Omit Telegram-specific payload fields (link_preview_options, message_thread_id). Coverage caveat: MCP check_index_coverage not runnable this session (transport failure).
