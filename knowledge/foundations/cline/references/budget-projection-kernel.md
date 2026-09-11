<!-- capsule-v2 -->
# Budget projection kernel — shrink any message list under protections with an audit trail

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** What is the reusable algorithm for forcing a transcript under a token target without breaking tool pairs or mutating provider-unsafe blocks?

## Policy-driven projection: drop unsafe → truncate oldest → closure-drop, never touching pinned/protected messages
**Path/Symbol:** `sdk/packages/core/src/extensions/context/budget-projection/project.ts:487-676` (`buildBudgetProjection`) + `types.ts` (`BudgetPolicyIntent`).
**Signature:** `buildBudgetProjection({messages, targetTokens, policyIntent: "agentic_summary"|"basic_compaction_projection"|"normal_provider_request", estimateMessageTokens}) → {status:"ok"|"failed", messages, actions[], warnings[], liveTailHandling:"included_verbatim"|"included_degraded"|"preserved_out_of_band", estimatedTokens}`.
**Data Shape:** Policy matrix — compaction intents get `{protectLatestTypedUser:true, protectLiveTailFromDrop:true, dropUnsafeOutsideLiveTail:true, dropThinkingBlocks:true}`; normal requests keep unsafe/thinking blocks. Every mutation appends a `BudgetAction{kind:"dropped_message"|"dropped_block"|"truncated_text"|"preserved", path:{messageIndex(, blockIndex)}, reason:"over_budget"|"unsafe_to_truncate"|"tool_pair_boundary"|"protected_live_tail", originalSize, finalSize}` with indexes tracked against the ORIGINAL array across removals.

### Decisive source
```ts
function findProtectedTailStartIndex(messages) {
    // ... collect every resolved (has tool_result) tool_use id, then:
    for (let index = messages.length - 1; index >= 0; index -= 1) {
        if (message.content.some((block) =>
            block.type === "tool_use" && !resolvedToolUseIds.has(block.id))) {
            return index;   // live tail starts at the first UNRESOLVED call
        }
    }
    return messages.length;
}
...
const targetChars = Math.max(
    16,
    Math.floor((options.targetTokens * charsPerToken) / Math.max(1, messages.length)),
);
```

**Flow:** clone → (compaction intents) drop ALL thinking blocks + prune empties → drop unsafe blocks (image/media/redacted_thinking, nested images inside tool_results) OUTSIDE latest-typed-user ∪ protected-live-tail → if still over: backward pass truncating text-bearing messages to a per-message char share (`target×charsPerToken÷count`, floor 16 chars; marker `\n...[truncated N chars]` budgeted INSIDE the limit) skipping pinned/protected → if still over: forward pass dropping whole messages but only after computing each candidate's tool-pair CLOSURE (BFS over shared tool_use/tool_result ids via `collectMessageClosure`) and refusing when the closure touches first/latest typed user or the protected tail → over target at the end ⇒ status "failed" + warning `budget_unachievable_with_protections`, returning best-effort result (callers log and proceed).
**Invariant:** Protected content is NEVER mutated by truncation — truncation targets text/file/tool_result payloads of unpinned messages only; drops are pair-closure-safe; "preserved" actions record WHY a message was skipped, making the projection auditable. The protected tail = everything from the first unresolved tool_use onward (in-flight work survives even mid-loop).
**Probe:** `grep -cF 'budget_unachievable_with_protections' .../project.ts` → 1; `grep -cF 'const closure = collectMessageClosure(messages, index);' ...` → 1; upstream suite project.test.ts pins all four behaviors ("drops unsafe image and redacted thinking blocks instead of truncating them", "keeps tool-use and tool-result pairs coherent when dropping history", "records budget action paths against original message indexes", "drops completed tool pairs after the latest typed prompt").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "buildBudgetProjection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-phase pipeline + policy matrix + action ledger wholesale — this is the most directly portable file in the plane; adapt char floors/marker copy; omit the normal_provider_request intent only if the host never projects non-compaction requests. Upstream tests exist per behavior; runner blocked here, battery greps green.
