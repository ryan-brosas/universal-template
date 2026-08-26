<!-- capsule-v2 -->
# Compaction input stripping — which message content must be dropped BEFORE the summarizer call so the fix doesn't hit prompt-too-long itself?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What preprocessing does the compact request apply, and why do images and re-injected attachments get stripped but markers kept?

## compaction-input-stripping
**Path/Symbol:** `src/services/compact/compact.ts` (`stripImagesFromMessages` :145-200, `stripReinjectedAttachments` :211-223; applied :1293-1301).
**Signature:** `stripImagesFromMessages(messages: Message[]): Message[]`; `stripReinjectedAttachments(messages): Message[]` (no-op when EXPERIMENTAL_SKILL_SEARCH off).
**Data Shape:** image/document blocks → text markers `[image]` / `[document]`, both at user-message top level AND nested inside `tool_result.content` arrays; skill_discovery/skill_listing attachment messages removed entirely.

### Decisive source
```ts
// Images are not needed for generating a conversation summary and can
// cause the compaction API call itself to hit the prompt-too-long limit,
// especially in CCD sessions where users frequently attach images.
// Replaces image blocks with a text marker so the summary still notes
// that an image was shared.
```
```ts
// Strip attachment types that are re-injected post-compaction anyway.
// skill_discovery/skill_listing are re-surfaced by resetSentSkillNames()
// + the next turn's discovery signal, so feeding them to the summarizer
// wastes tokens and pollutes the summary with stale skill suggestions.
```

**Flow:** the streaming fallback assembles: `getMessagesAfterCompactBoundary(messages)` + summaryRequest → stripReinjectedAttachments → stripImagesFromMessages → normalizeMessagesForAPI. Only USER messages carry images (in-source note), so assistant messages pass untouched; nested tool_result media is replaced with a marker while keeping the tool_result block itself (pairing intact).
**Invariant:** replace-with-marker, never delete: the summary must still record that an image existed, and removing blocks outright breaks tool_result/tool_use pairing. Attachment stripping targets exactly the types whose POST-compact lifecycle re-injects them — stripping is deduplication against future state, not information loss. The whole chain runs BEFORE normalizeMessagesForAPI because normalization assumes clean pairing.
**Probe:** no upstream test. Deterministic pins: `grep -n "'\[image\]'" src/services/compact/compact.ts` → :160/:172; `grep -n "Only user messages contain images" src/services/compact/compact.ts` → :141-142; applied-order anchor `grep -n "stripImagesFromMessages(" src/services/compact/compact.ts` → :145/:1294.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "stripImagesFromMessages stripReinjectedAttachments", limit: 10 });
```

## Verdict
Adopt marker-replacement media stripping and lifecycle-aware attachment stripping. Adapt marker strings/types. Omit nothing else — small seam. Coverage caveat: no unit tests upstream.
