<!-- capsule-v2 -->
# API message normalization pipeline — what ordered passes convert an internal transcript into a provider-safe message array?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** In what order must virtual-message stripping, merging, error-block stripping, thinking filters, and boundary injections run — and why does order matter?

## normalizeMessagesForAPI
**Path/Symbol:** `src/utils/messages.ts:normalizeMessagesForAPI` (:1989-2370); helpers `reorderAttachmentsForAPI` (:1481), `stripToolReferenceBlocksFromUserMessage` (:1677), `appendMessageTagToUserMessage` (:1620), `mergeUserMessages` (:2411-2449), `filterOrphanedThinkingOnlyMessages`, `sanitizeErrorToolResultContent` (:1884-1907).
**Signature:** `(messages: Message[], tools: Tools = []) => (UserMessage | AssistantMessage)[]`.
**Data Shape:** internal transcript carries typed envelopes (progress/system/attachment/virtual/user/assistant); output is strictly user/assistant pairs with API-legal block contents.

### Decisive source
```ts
const reorderedMessages = reorderAttachmentsForAPI(messages).filter(m => !m.isVirtual)
// targeted strip map: syntheticApiErrorMessage text → block types to strip
// from the NEAREST PRECEDING isMeta user message (walk-back bounded)
const result = []
// switch(message.type):
//  system(local_command) → userMessage, merge-if-last-is-user
//  user    → strip tool_reference (or unavailable-tool refs when search ON)
//         → strip document/image blocks named by a following too-large error
//         → inject TOOL_REFERENCE_TURN_BOUNDARY sibling (unless defer gate)
//         → merge consecutive users ("Bedrock doesn't support multiple user
//            messages in a row")
//  assistant→ normalizeToolInputForAPI + drop 'caller' field when search OFF;
//         → merge SAME message.id walking back over tool_results ("concurrent
//            agents (teammates) can interleave streaming content blocks")
//  attachment → normalizeAttachmentForAPI (+ensureSystemReminderWrap under
//         chair_sermon gate) → mergeUserMessagesAndToolResults or push
// post-passes IN ORDER:
// relocateToolReferenceSiblings (defer gate) → filterOrphanedThinkingOnly
// → filterTrailingThinkingFromLastAssistant THEN filterWhitespaceOnlyAssistant
// → ensureNonEmptyAssistantContent → [gate] mergeAdjacentUserMessages +
//   smooshSystemReminderSiblings → sanitizeErrorToolResultContent (unconditional)
// → [HISTORY_SNIP && !test] append [id:xxx] tags to non-meta users → validateImagesForAPI
```

**Flow:** the pipeline exists because the API rejects many legal-internally shapes: consecutive user turns (Bedrock), non-text content inside `is_error` tool_results ("all content must be type text"), orphaned thinking-only assistants after compaction slicing (signature-mismatch 400s), oversized images/documents re-sent after their error, and tool_reference expansions at prompt tail teaching capybara models to sample the stop sequence (~10% A/B, fixed by inserting a `\n\nHuman:` boundary sibling — "Must be a sibling, NOT inside tool_result.content — mixing text with tool_reference inside the block is a server ValueError").
**Invariant:** (1) ORDER IS LOAD-BEARING and documented in-source: strip trailing thinking BEFORE filtering whitespace-only messages — reversed, `[text("\n\n"), thinking(...)]` survives the whitespace filter then loses its thinking block leaving `[text("\n\n")]` which 400s (:2312-2316); each pass can create conditions a prior pass handled ("These multi-pass normalizations are inherently fragile … Consider unifying" comment is a warning, not license to reorder); (2) `[id:]` snip tags append ONLY to non-meta users and skip test mode ("tags change message content hashes, breaking VCR fixture lookup"); (3) merges preserve the FIRST message's uuid/envelope (`...a` spread) so strip maps keyed by uuid stay valid; (4) error-driven stripping targets the nearest preceding `isMeta` user message — synthetic errors themselves never reach the API.
**Probe:** coverage caveat (no upstream tests for messages.ts). Deterministic probes: `sed -n '2312,2316p' src/utils/messages.ts` pins the ordering bug comment verbatim; `grep -n "is_error" src/utils/messages.ts | head -5` anchors sanitizeErrorToolResultContent; graph resolves normalizeMessagesForAPI :1989-2370 line-exact.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "normalizeMessagesForAPI merge consecutive user messages", limit: 5, fields: ["signature","name","file"] });
// → normalizeMessagesForAPI 1989-2370, mergeUserMessages 2411-2449, ...
```

## Verdict
Adopt the pass ORDER as the portable contract (it encodes five distinct API failure modes); adapt individual strips to your provider's quirks; omit teammate-ID merging if single-agent. Porting trap: running whitespace-filter before thinking-strip reproduces the exact 400 the source documents; another is letting attachments render as separate user turns instead of merging into the adjacent one.
