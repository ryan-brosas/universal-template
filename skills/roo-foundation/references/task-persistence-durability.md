<!-- capsule-v2 -->
# Crash-proof dual-history persistence — how do you write two correlated JSON logs so a crash can't strand them?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What do read/save of clineMessages vs apiConversationHistory guarantee when files are corrupt, empty, renamed, or half-written?

## read/save pairs: tolerate-and-empty reads, snapshot-before-write saves
**Path/Symbol:** `src/core/task-persistence/apiMessages.ts:40-121` (+ legacy rename at :72-99); `src/core/task-persistence/taskMessages.ts:17-56`; save wrappers tested in `src/core/task/__tests__/Task.persistence.spec.ts:258-449`; atomic writer `src/utils/safeWriteJson.ts`.
**Signature:** `readApiMessages({taskId, globalStoragePath}): Promise<ApiMessage[]>`; `saveApiMessages(messages, ...)`, `readTaskMessages`/`saveTaskMessages` twins for UI log.
**Data Shape:** ApiMessage extends Anthropic.MessageParam with roo bookkeeping: `ts?`, `isSummary?/condenseId?/condenseParent?`, `isTruncationMarker?/truncationId?/truncationParent?`, plus vendor reasoning fields (`reasoning_content` for DeepSeek/Z.ai tool-call sequences, `reasoning_details[]` OpenRouter/Gemini-3, `type:"reasoning"`+`encrypted_content`).

### Decisive source
```ts
try {
  const parsedData = JSON.parse(fileContent)
  if (!Array.isArray(parsedData)) { warn(...); return [] }   // corrupt shape ⇒ empty, not throw
  ...
} catch (error) {
  // DO NOT unlink oldPath if parsing failed.
  return []
}
// legacy migration: claude_messages.json unlinked ONLY after successful parse
```
Task.persistence.spec pins the save side: on failure returns false AND RETRIES (success on 2nd attempt), and **snapshots the array before passing to save** — the caller's live array keeps mutating during async writes without corrupting the persisted copy.

**Flow:** new filename first → fall back to legacy `claude_messages.json` (migrate-or-preserve: unlink only after clean parse) → missing/corrupt always degrades to `[]` with a diagnostic log, letting task bootstrap proceed; writes go through safeWriteJson (temp-file replace semantics).
**Invariant:** Reads NEVER throw on corrupt content and NEVER destroy data they failed to parse; saves operate on snapshots so concurrent mutation cannot tear the file. Both logs share one directory layout keyed by taskId (`getTaskDirectoryPath`).
**Probe:** `src/core/task/__tests__/Task.persistence.spec.ts` ("returns false on failure"/"succeeds on 2nd retry attempt" :278/:304, "snapshots the array" :326/:385); corrupt-read behavior exercised via message-manager suite fixtures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "readApiMessages saveApiMessages claude_messages legacy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt degrade-to-empty reads + parse-gated legacy deletion + snapshot-before-save. Adapt filenames/storage paths to your host. Nothing portable worth omitting — this capsule IS the durability contract.
