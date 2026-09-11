<!-- capsule-v2 -->
# Post-compact state restoration — after a summary replaces the conversation, exactly which state must be re-injected, re-announced, or deliberately NOT reset?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the full restoration checklist a compaction implementation must perform between "summary produced" and "conversation resumes"?

## post-compact-restoration
**Path/Symbol:** `src/services/compact/compact.ts` (`compactConversation` :387-763 — restoration block :517-717; budgets :122-130).
**Signature:** `compactConversation(messages, context, cacheSafeParams, suppressFollowUpQuestions, customInstructions?, isAutoCompact?, recompactionInfo?): Promise<CompactionResult>`; `buildPostCompactMessages(result)` fixes order: boundaryMarker → summaryMessages → messagesToKeep → attachments → hookResults.
**Data Shape:** budget constants: 5 files / 50K-token file budget / 5K per file; skills 25K total / 5K per skill (rationale in-source: verify=18.7KB, claude-api=20.1KB skills previously re-injected unbounded = 5-10K tok/compact).

### Decisive source
```ts
// Store the current file state before clearing
const preCompactReadFileState = cacheToObject(context.readFileState)

// Clear the cache
context.readFileState.clear()
context.loadedNestedMemoryPaths?.clear()

// Intentionally NOT resetting sentSkillNames: re-injecting the full
// skill_listing (~4K tokens) post-compact is pure cache_creation with
// marginal benefit. The model still has SkillTool in its schema and
// invoked_skills attachment (below) preserves used-skill content.
```
and the delta re-announcement:
```ts
// Compaction ate prior delta attachments. Re-announce from the current
// state so the model has tool/instruction context on the first
// post-compact turn. Empty message history → diff against nothing →
// announces the full set.
for (const att of getDeferredToolsDeltaAttachment(
  context.options.tools,
  context.options.mainLoopModel,
  [],            // empty history in full compact
  { callSite: 'compact_full' },
))
```

**Flow:** snapshot readFileState → clear it + nested-memory paths → parallel: restore recent files (re-READ via FileReadTool for fresh validated content, recency-sorted, count+token double-capped, skipping plan/memory files AND anything already visible in preserved tail) + async-agent status attachments (running/finished-unretrieved tasks so the model neither respawns nor loses results) + plan-file attachment + plan-MODE instructions attachment (else the model exits plan mode across the boundary) + invoked-skills attachment (most-recent-first, per-skill head truncation with a marker telling the model to Read the path) → re-announce deferred-tools/agent-listing/MCP-instructions DELTAS against empty history (full) or scanned kept messages (partial) → SessionStart hooks with source 'compact' → boundary marker carries sorted `preCompactDiscoveredTools` because summaries don't preserve tool_reference blocks → notifyCompaction resets cache-break baseline → reAppendSessionMetadata keeps custom title inside readLiteMetadata's 16KB tail window.
**Invariant:** restoration is asymmetric BY DESIGN: file/memory caches reset (cheap to re-read), but skill-name dedup sets do NOT (resetting would re-inject a ~4K listing as pure cache_creation); every delta re-announcement diffs against what survives (kept messages), not against nothing; token counting distinguishes three numbers — preCompact count, compaction-call usage, and truePostCompactTokenCount (message-payload estimate that will still gain ~20-40K of system prompt/tools next turn, so `willRetriggerNextTurn` is computed against it).
**Probe:** no upstream test. Deterministic pins: `grep -n "Intentionally NOT resetting sentSkillNames" src/services/compact/compact.ts` → :524/:922; `grep -n "truePostCompactTokenCount" src/services/compact/compact.ts` → :308/:637/:654/:746; `grep -n "16KB tail window" src/services/compact/compact.ts` → :707/:1056.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createPostCompactFileAttachments createSkillAttachmentIfNeeded", limit: 10 });
```

## Verdict
Adopt the restoration checklist and its asymmetry rules. Adapt budget numbers and attachment types. Omit KAIROS transcript-segment writes. Coverage caveat: no unit tests upstream.
