<!-- capsule-v2 -->
# Context-management trigger ladder — when exactly do condense vs truncate fire, and with which threshold?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How does roo decide "summarize now" vs "slide the window" — and how do per-profile thresholds enter without corrupting the global one?

## manageContext + willManageContext: shared budget math, profile-scoped thresholds
**Path/Symbol:** `src/core/context-management/index.ts:243-372` (`manageContext`); UI pre-check `willManageContext` :157-193; constants `TOKEN_BUFFER_PERCENTAGE = 0.1` :24; fallback call `truncateConversation(messages, 0.5, taskId)` :331.
**Signature:** `manageContext(options): Promise<ContextManagementResult>` (`SummarizeResponse & { prevContextTokens, truncationId?, messagesRemoved?, newContextTokensAfterTruncation? }`).
**Data Shape:** Budget: `prevContextTokens = totalTokens + lastMessageTokens` (totalTokens NEVER includes the last user message) and `allowedTokens = contextWindow * (1 - 0.1) - reservedTokens` where `reservedTokens = maxTokens || ANTHROPIC_DEFAULT_MAX_TOKENS`.

### Decisive source
```ts
let effectiveThreshold = autoCondenseContextPercent          // global default
const profileThreshold = profileThresholds[currentProfileId]
if (profileThreshold !== undefined) {
  if (profileThreshold === -1)            effectiveThreshold = autoCondenseContextPercent // -1 = inherit
  else if (profileThreshold >= MIN_CONDENSE_THRESHOLD &&
           profileThreshold <= MAX_CONDENSE_THRESHOLD) effectiveThreshold = profileThreshold
  // invalid ⇒ keep global default (+ console.warn in manageContext)
}
if (autoCondenseContext && (contextPercent >= effectiveThreshold || prevContextTokens > allowedTokens)) {
  const result = await summarizeConversation({ ..., isAutomaticTrigger: true })
  if (!result.error) return { ...result, prevContextTokens }
}
if (prevContextTokens > allowedTokens) return await truncateConversation(messages, 0.5, taskId) // sliding-window fallback
```

**Flow:** count last message → compute budget → condense attempt when auto-condense on AND (percent ≥ threshold OR over hard budget) → on condense ERROR fall through to truncation at fixed fracToRemove 0.5 → post-truncate, recount `newContextTokensAfterTruncation` by re-counting system prompt + every non-hidden message. `willManageContext` duplicates ONLY the threshold math so the UI can show a spinner before the real run.
**Invariant:** Condense failure must degrade to truncation, never abort the turn; the two trigger predicates (percent-threshold, hard-budget) are OR-ed, and the identical formula lives in both functions — porters who change one must change both or the UI indicator lies.
**Probe:** `src/core/context-management/__tests__/context-management.spec.ts`; `truncation.spec.ts` ("should round messagesToRemove to an even number" :75).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "manageContext willManageContext TOKEN_BUFFER_PERCENTAGE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-trigger ladder (threshold OR hard-budget → summarize → truncate-on-failure). Adapt threshold bounds and buffer percentage to your models. Omit the VS Code spinner messaging.
