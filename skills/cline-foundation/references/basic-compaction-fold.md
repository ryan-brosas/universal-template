<!-- capsule-v2 -->
# Basic compaction fold — no-LLM transcript collapse with frozen survivors

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** How do you shrink a transcript deterministically (no summarizer) while keeping every typed user prompt and never re-processing prior compaction output?

## Selection funnel: typed prompts mandatory → frozen skip → latest-turn suffix → older finals → merge with dropped-work summaries
**Path/Symbol:** `sdk/packages/core/src/extensions/context/basic-compaction.ts:452-711` (`runBasicCompaction`).
**Signature:** `runBasicCompaction({context, estimateMessageTokens, logger?}) → CoreCompactionResult | undefined` — synchronous, returns `undefined` when nothing changed.
**Data Shape:** Refuses transcripts `< 2` messages or with zero sanitizable typed prompts. Target = `min(budget.messages.targetTokens, triggerTokens)`. Frozen marker: `metadata.compaction === "preserved"`.

### Decisive source
```ts
// Output of an earlier compaction is frozen: those messages are kept
// as-is and never re-folded, so this pass only processes new messages.
if (isPreservedByCompaction(originalMessages[index])) {
    frozenIndices.add(index);
    totalTokens += estimate(originalMessages[index]);
}
...
while (start < originalMessages.length &&
       originalMessages[start].role !== "assistant") { start += 1; }
```
```ts
const projectionTargetTokens = Math.min(
    Math.max(totalTargetTokens, totalTokens),   // floor = deliberate keeps
    Math.max(1, options.context.budget.messages.triggerTokens), // ceiling
);
```

**Flow:** (1) sanitize+keep ALL typed user prompts, budgeting them at post-merge shape — attachments (`file`/`image` blocks) survive ONLY on the latest typed prompt; (2) add frozen output of earlier compactions verbatim; (3) latest turn: keep newest-fitting suffix walking backward from the end (stop at first over-budget message or frozen index), then snap the kept start FORWARD to an assistant message so tool pairs stay whole; (4) older turns newest-first: keep each turn's concluding assistant answer when it fits — skipping tool_use-bearing assistants (their results are gone), stripping thinking blocks, dropping the answer if nothing text-bearing remains; (5) run budget projection → `mergeAdjacentUserTurns` bridges gaps between adjacent typed prompts with dropped-work summaries resolved by original message-id (`<SYSTEM_NOTICE>` blocks listing files read/edited + commands + up to 3 preserved recent assistant responses verbatim); trailing gaps after the last surviving message of a turn get appended to that prompt; (6) if nothing changed JSON-wise ⇒ undefined; (7) first kept message gets accumulating compaction metadata (kind:"compaction", reason by mode, running messagesRemoved + aggregated usageBefore since per-message metrics are stripped); non-typed survivors get the frozen marker.
**Invariant:** The safety-valve floor `max(targetTokens, totalTokens)` means repeated compaction NEVER trims below what selection deliberately kept (a manual /compact halving its target each run cannot erase prompts); trigger stays a hard best-effort ceiling. Repeated passes only ever process messages added since — without the frozen marker each pass would re-drop preserved answers and stack duplicate SYSTEM_NOTICEs.
**Probe:** `grep -cF 'COMPACTION_PRESERVED_MARKER = \"preserved\"' .../basic-compaction.ts` → 1; `grep -cF 'PRESERVED_ASSISTANT_TEXT_COUNT = 3' ...` → 1; `grep -cF 'Math.max(totalTargetTokens, totalTokens)' ...` → 1; upstream tests "does not re-fold the output of an earlier compaction", "bridges merged user turns with dropped-work summaries and drops stale metrics".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "runBasicCompaction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole selection funnel incl. frozen-marker idempotence and assistant-suffix snapping; adapt PRESERVED_ASSISTANT_TEXT_COUNT=3 and the SYSTEM_NOTICE copy; omit Cline's metrics-aggregation metadata if the host has no per-message usage ledger. Runner blocked honestly (no node_modules in clone); battery greps executed green.
