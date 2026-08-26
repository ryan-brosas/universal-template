<!-- capsule-v2 -->
# FileList ingestion — how do browser file picks become FileUIParts, and what does stop() owe pending conversions?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the boundary contract converting FileList/File[] into message parts (and why does sendMessage track it in an AbortController set)?

## convertFileListToFileUIParts
**Path/Symbol:** `packages/ai/src/ui/convert-file-list-to-file-ui-parts.ts:convertFileListToFileUIParts`; consumer gate `packages/ai/src/ui/chat.ts:sendMessage` (:374-389).
**Signature:** `convertFileListToFileUIParts(files?: FileList | File[]): Promise<FileUIPart[]>` — async because File.arrayBuffer() is; empty/null ⇒ `[]`.
**Data Shape:** output parts `{type:'file', mediaType, filename?, url: data-URL}`; mediaType falls back from `file.type` when the browser omits it.

### Decisive source
```ts
// sendMessage wraps the AWAIT conversion in a tracked AbortController so
// stop() can cancel the PRE-request phase too:
const abortController = new AbortController();
this.pendingMessagePreparations.add(abortController);
let fileParts;
try { fileParts = Array.isArray(message.files) ? message.files : await convertFileListToFileUIParts(message.files); }
finally { this.pendingMessagePreparations.delete(abortController); }
if (abortController.signal.aborted) return;   // stopped mid-conversion ⇒ silently drop
```

**Flow:** user submits `{text?, files}` → conversion runs under a tracked controller → aborted ⇒ return without pushing anything → otherwise parts order is files FIRST then text part → pushMessage → makeRequest. stop() iterates `pendingMessagePreparations` BEFORE aborting activeResponse/resume (:605-611).
**Invariant:** a porter that awaits file conversion WITHOUT registering an AbortController leaves an uncancellable window where stop() during a large multi-file pick still sends. The aborted-check must sit AFTER the await, not before it.
**Probe:** exercised via `packages/ai/src/ui/chat.test.ts` send-with-files paths (no dedicated direct suite for the converter itself — coverage caveat: behavior pinned through chat.test.ts integration paths).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "convertFileListToFileUIParts pendingMessagePreparations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tracked-conversion + post-await abort-check pattern for any pre-request async work. Adapt data-URL encoding limits to your transport.
